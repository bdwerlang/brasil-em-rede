"""Resumable, validated partition downloads with durable page checkpoints."""

from __future__ import annotations

import csv
import hashlib
import http.client
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


class AcquisitionError(Exception):
    """Acquisition failed without publishing an invalid artifact."""


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, data: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _validate(path: Path, kind: str) -> None:
    if kind not in {"json", "csv", "binary"}:
        raise ValueError("kind must be json, csv or binary")
    if kind == "binary":
        return
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        prefix = stream.read(1024).lstrip().lower()
        if prefix.startswith(("<!doctype html", "<html", "<head", "<body")):
            raise AcquisitionError("HTML response is not a data export")
        stream.seek(0)
        try:
            if kind == "json":
                json.load(stream)
            else:
                rows = csv.reader(stream, strict=True)
                if not next(rows, None):
                    raise AcquisitionError("empty CSV")
                for _ in rows:
                    pass
        except (ValueError, csv.Error, UnicodeError) as exc:
            raise AcquisitionError(f"invalid {kind} export") from exc


@dataclass
class Manifest:
    """Persist only local artifact metadata, never URLs or credentials."""

    path: Path
    source_id: str
    partition: str
    pages: dict[str, dict[str, str | int]] = field(default_factory=dict)

    @classmethod
    def open(cls, path: Path, source_id: str, partition: str) -> Manifest:
        if not path.exists():
            return cls(path, source_id, partition)
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["source_id"] != source_id or data["partition"] != partition:
            raise AcquisitionError("manifest belongs to another partition")
        return cls(path, source_id, partition, data["pages"])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(self.path, {"source_id": self.source_id, "partition": self.partition,
                                 "pages": self.pages})


class Acquisition:
    """One instance shares per-host concurrency limits across its callers."""

    def __init__(self, retries: int = 3, backoff: float = 0.2, per_host: int = 2,
                 timeout: float = 30, sleep: Callable[[float], None] = time.sleep):
        if retries < 0 or backoff < 0 or per_host < 1 or timeout <= 0:
            raise ValueError("invalid acquisition limits")
        self.retries = retries
        self.backoff = backoff
        self.per_host = per_host
        self.timeout = timeout
        self.sleep = sleep
        self._lock = threading.Lock()
        self._hosts: dict[str, threading.BoundedSemaphore] = {}

    def _host(self, url: str) -> threading.BoundedSemaphore:
        host = urlsplit(url).hostname
        if not host:
            raise ValueError("URL requires a host")
        with self._lock:
            return self._hosts.setdefault(host.lower(), threading.BoundedSemaphore(self.per_host))

    def acquire_pages(self, manifest: Manifest, pages: Iterable[tuple[str, str]], directory: Path,
                      kind: str, checksums: dict[str, str] | None = None) -> None:
        """Consume pages in order. A page is checkpointed only after validation and rename."""
        directory.mkdir(parents=True, exist_ok=True)
        for page, url in pages:
            if not page or Path(page).name != page or page in {".", ".."}:
                raise ValueError("page must be a safe filename")
            target = directory / page
            expected = (checksums or {}).get(page)
            record = manifest.pages.get(page)
            source_hash = hashlib.sha256(url.encode()).hexdigest()
            if (record and record.get("source_sha256") == source_hash and target.is_file()
                    and _digest(target) == record["sha256"]
                    and (expected is None or record["sha256"] == expected.lower())):
                continue
            with self._host(url):
                self._download(url, target, kind, expected)
            manifest.pages[page] = {"sha256": _digest(target), "bytes": target.stat().st_size,
                                    "source_sha256": source_hash}
            manifest.save()

    def export(self, manifest: Manifest, page: str, directory: Path, kind: str,
               producer: Callable[[Path], None], checksum: str | None = None) -> None:
        """Validate an export generated by a caller into a temporary path."""
        if not page or Path(page).name != page or page in {".", ".."}:
            raise ValueError("page must be a safe filename")
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / page
        record = manifest.pages.get(page)
        if (record and target.is_file() and _digest(target) == record["sha256"]
                and (checksum is None or record["sha256"] == checksum.lower())):
            return
        partial = target.with_name(target.name + ".part")
        producer(partial)
        self._publish(partial, target, kind, checksum)
        manifest.pages[page] = {"sha256": _digest(target), "bytes": target.stat().st_size}
        manifest.save()

    def _publish(self, partial: Path, target: Path, kind: str, checksum: str | None) -> None:
        _validate(partial, kind)
        if checksum and _digest(partial) != checksum.lower():
            raise AcquisitionError("checksum mismatch")
        os.replace(partial, target)

    def _download(self, url: str, target: Path, kind: str, checksum: str | None) -> None:
        scheme = urlsplit(url).scheme.lower()
        if scheme not in {"http", "https", "ftp"}:
            raise ValueError("unsupported protocol")
        partial = target.with_name(target.name + ".part")
        metadata = target.with_name(target.name + ".part.json")
        for attempt in range(self.retries + 1):
            try:
                if scheme == "ftp":
                    # FTP transfers restart: no reliable identity check for partial content.
                    with urlopen(url, timeout=self.timeout) as response, partial.open("wb") as out:
                        self._copy(response, out)
                else:
                    self._http(url, partial, metadata)
                self._publish(partial, target, kind, checksum)
                metadata.unlink(missing_ok=True)
                return
            except (OSError, URLError, http.client.HTTPException) as exc:
                if isinstance(exc, HTTPError) and exc.code < 500 and exc.code not in {408, 429}:
                    raise AcquisitionError(f"HTTP {exc.code}") from exc
                if attempt == self.retries:
                    raise AcquisitionError("transfer failed after retries") from exc
                self.sleep(self.backoff * (2 ** attempt))

    @staticmethod
    def _copy(response: object, out: object) -> None:
        while block := response.read(65536):  # type: ignore[attr-defined]
            out.write(block)  # type: ignore[attr-defined]

    def _http(self, url: str, partial: Path, metadata: Path) -> None:
        info = json.loads(metadata.read_text()) if metadata.exists() else {}
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        offset = (partial.stat().st_size if partial.exists() and info.get("etag")
                  and info.get("url_hash") == url_hash else 0)
        headers = {"Accept-Encoding": "identity"}
        if offset:
            headers.update({"Range": f"bytes={offset}-", "If-Range": info["etag"]})
        with urlopen(Request(url, headers=headers), timeout=self.timeout) as response:
            etag = response.headers.get("ETag", "")
            resumed = (offset > 0 and response.status == 206 and etag == info.get("etag")
                       and response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"))
            if response.status == 206:
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)",
                                     response.headers.get("Content-Range", ""))
                if (not resumed or not match or int(match[1]) != offset
                        or int(match[2]) + 1 != int(match[3])):
                    raise AcquisitionError("invalid partial response")
            if not resumed:
                offset = 0
            # Only strong ETags bind a subsequent range to the same representation.
            _atomic_json(metadata, {"etag": etag if etag and not etag.startswith("W/") else "",
                                    "url_hash": url_hash})
            with partial.open("ab" if resumed else "wb") as out:
                self._copy(response, out)
            length = response.headers.get("Content-Length")
            if length is not None and partial.stat().st_size - offset != int(length):
                raise OSError("incomplete response")
