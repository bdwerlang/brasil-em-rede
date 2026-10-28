"""Direct F05-to-U03 contract check against the shell's disposable PostgreSQL."""

from __future__ import annotations

import hashlib
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import psycopg

from bracc_etl.acquisition import Acquisition, AcquisitionError, Manifest
from bracc_etl.acquisition.catalog import RawArtifactRef, register_raw_artifact
from bracc_etl.control.catalog import Catalog


def main(socket: str) -> None:
    bodies = {
        "/one": b'{"page":1,"rows":[1]}',
        "/two": b'{"page":2,"rows":[2]}',
        "/three": b'{"page":3,"rows":[3]}',
    }

    class Handler(BaseHTTPRequestHandler):
        calls: list[str] = []
        interrupt_once = True

        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            self.calls.append(self.path)
            body = bodies[self.path]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.path == "/two" and Handler.interrupt_once:
                Handler.interrupt_once = False
                self.wfile.write(body[:5])
                self.wfile.flush()
                self.connection.shutdown(2)
                return
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        pages = [(f"{n}.json", f"{base}/{n}") for n in ("one", "two", "three")]
        checksums = {
            name: hashlib.sha256(bodies[f"/{name.removesuffix('.json')}"]).hexdigest()
            for name, _ in pages
        }
        with TemporaryDirectory() as folder:
            output = Path(folder)
            storage_root = output / "object-store"
            manifest_path = output / "manifest.json"
            manifest = Manifest.open(manifest_path, "cnpj", "2026-01")
            try:
                Acquisition(retries=0).acquire_pages(manifest, pages, output, "json", checksums)
            except AcquisitionError:
                pass
            else:
                raise AssertionError("interrupted page acquisition unexpectedly succeeded")

            manifest = Manifest.open(manifest_path, "cnpj", "2026-01")
            assert set(manifest.pages) == {"one.json"}
            with psycopg.connect(host=socket, user="postgres", dbname="postgres") as conn:
                catalog = Catalog(conn)
                try:
                    with catalog.transaction():
                        register_raw_artifact(
                            catalog,
                            manifest,
                            "two.json",
                            output / "two.json",
                            storage_root=storage_root,
                            artifact_id=UUID(int=101),
                            partition_id="2026-01",
                            dataset_id="cnpj",
                            access_class="public",
                        )
                except ValueError as exc:
                    assert "missing" in str(exc)
                else:
                    raise AssertionError("incomplete page was registered")

                Acquisition(retries=0).acquire_pages(manifest, pages, output, "json", checksums)
                assert Handler.calls == ["/one", "/two", "/two", "/three"]
                manifest = Manifest.open(manifest_path, "cnpj", "2026-01")
                assert set(manifest.pages) == {name for name, _ in pages}
                for index, (name, _) in enumerate(pages, start=1):
                    raw = (output / name).read_bytes()
                    assert raw == bodies[f"/{name.removesuffix('.json')}"]
                    assert hashlib.sha256(raw).hexdigest() == checksums[name]
                    with catalog.transaction():
                        reference = register_raw_artifact(
                            catalog,
                            manifest,
                            name,
                            output / name,
                            storage_root=storage_root,
                            artifact_id=UUID(int=100 + index),
                            partition_id="2026-01",
                            dataset_id="cnpj",
                            access_class="public",
                        )
                    assert reference == RawArtifactRef(
                        source_id="cnpj",
                        provider_source_id="receita_federal",
                        dataset_id="cnpj",
                        artifact_id=UUID(int=100 + index),
                        artifact_sha256=checksums[name],
                        partition_id="2026-01",
                        object_key=f"raw/cnpj/cnpj/2026-01/{checksums[name]}",
                    )

                rows = conn.execute(
                    "SELECT s.id, d.id, p.id, a.object_key, a.sha256, a.access_class "
                    "FROM control.artifact a JOIN control.partition p ON p.id=a.partition_id "
                    "JOIN control.dataset d ON d.id=p.dataset_id "
                    "JOIN control.source s ON s.id=d.source_id ORDER BY a.object_key"
                ).fetchall()
                assert len(rows) == 3
                assert all(row[:3] == ("cnpj", "cnpj", "2026-01") for row in rows)
                assert all(row[5] == "public" for row in rows)
                assert {row[4] for row in rows} == set(checksums.values())
                for name, _ in pages:
                    object_path = storage_root / next(
                        row[3] for row in rows if row[4] == checksums[name]
                    )
                    assert object_path.read_bytes() == (output / name).read_bytes()

                restricted_bytes = b'{"page":"restricted"}'
                restricted_path = output / "restricted.json"
                restricted_path.write_bytes(restricted_bytes)
                restricted_digest = hashlib.sha256(restricted_bytes).hexdigest()
                manifest.pages["restricted.json"] = {
                    "sha256": restricted_digest,
                    "bytes": len(restricted_bytes),
                }
                manifest.save()
                restricted_key = f"raw/cnpj/cnpj/2026-01/{restricted_digest}"
                existing_object = storage_root / restricted_key
                existing_object.parent.mkdir(parents=True, exist_ok=True)
                existing_object.write_bytes(restricted_bytes)
                try:
                    with catalog.transaction():
                        register_raw_artifact(
                            catalog,
                            manifest,
                            "restricted.json",
                            restricted_path,
                            storage_root=storage_root,
                            artifact_id=UUID(int=201),
                            partition_id="2026-01",
                            dataset_id="cnpj",
                            access_class="restricted",
                        )
                except psycopg.Error:
                    pass
                else:
                    raise AssertionError("catalog accepted access mismatch")
                assert existing_object.read_bytes() == restricted_bytes

                existing_pages = {row[3]: (storage_root / row[3]).read_bytes() for row in rows}
                try:
                    with catalog.transaction():
                        register_raw_artifact(
                            catalog,
                            manifest,
                            "three.json",
                            output / "three.json",
                            storage_root=storage_root,
                            artifact_id=UUID(int=202),
                            partition_id="2026-01",
                            dataset_id="other",
                            access_class="public",
                        )
                except psycopg.Error:
                    pass
                else:
                    raise AssertionError("catalog accepted dataset mismatch")
                assert all(
                    (storage_root / key).read_bytes() == data
                    for key, data in existing_pages.items()
                )

                divergent_bytes = b'{"page":"divergent"}'
                divergent_source = output / "divergent.json"
                divergent_source.write_bytes(divergent_bytes)
                divergent_digest = hashlib.sha256(divergent_bytes).hexdigest()
                manifest.pages["divergent.json"] = {
                    "sha256": divergent_digest,
                    "bytes": len(divergent_bytes),
                }
                manifest.save()
                divergent_key = f"raw/cnpj/cnpj/2026-01/{divergent_digest}"
                divergent_target = storage_root / divergent_key
                divergent_target.parent.mkdir(parents=True, exist_ok=True)
                divergent_target.write_bytes(b"existing wrong content")
                try:
                    with catalog.transaction():
                        register_raw_artifact(
                            catalog,
                            manifest,
                            "divergent.json",
                            divergent_source,
                            storage_root=storage_root,
                            artifact_id=UUID(int=204),
                            partition_id="2026-01",
                            dataset_id="cnpj",
                            access_class="public",
                        )
                except ValueError as exc:
                    assert "existing storage object differs" in str(exc)
                else:
                    raise AssertionError("divergent existing object was overwritten")
                assert divergent_target.read_bytes() == b"existing wrong content"
                assert (
                    conn.execute(
                        "SELECT count(*) FROM control.artifact WHERE id=%s OR object_key=%s",
                        (UUID(int=204), divergent_key),
                    ).fetchone()[0]
                    == 0
                )

                corrupted = output / "one.json"
                original = corrupted.read_bytes()
                corrupted.write_bytes(b'{"page":999}')
                try:
                    with catalog.transaction():
                        register_raw_artifact(
                            catalog,
                            manifest,
                            "one.json",
                            corrupted,
                            storage_root=storage_root,
                            artifact_id=UUID(int=203),
                            partition_id="2026-01",
                            dataset_id="cnpj",
                            access_class="public",
                        )
                except ValueError as exc:
                    assert "disagree" in str(exc)
                else:
                    raise AssertionError("corrupt bytes were registered")
                finally:
                    corrupted.write_bytes(original)
                object_key = next(row[3] for row in rows if row[4] == checksums["one.json"])
                assert (storage_root / object_key).read_bytes() == original
                assert conn.execute("SELECT count(*) FROM control.artifact").fetchone()[0] == 3
        print("F05 acquisition resume and U03 catalog bridge: passed")
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


if __name__ == "__main__":
    main(sys.argv[1])
