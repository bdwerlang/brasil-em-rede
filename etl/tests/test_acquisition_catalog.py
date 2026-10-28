import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID

import pytest

from bracc_etl.acquisition import Acquisition, AcquisitionError, Manifest
from bracc_etl.acquisition.catalog import (
    RawArtifactRef,
    register_raw_artifact,
    resolve_manifest_source,
)


class Connection:
    def __init__(self) -> None:
        self.row = None
        self.rows = {}
        self.inserted = []

    def execute(self, query: str, params: tuple) -> "Connection":
        if query.startswith("SELECT id"):
            self.result = [
                row for key, row in self.rows.items() if key == params[0] or row[2] == params[1]
            ]
        else:
            self.inserted.append(params)
            self.rows[params[0]] = params
        return self

    def fetchall(self):
        return self.result


class FakeCatalog:
    def __init__(self) -> None:
        self.connection = Connection()

    def artifact(self, *params) -> None:
        self.connection.execute("INSERT", params)


def fixture(tmp_path: Path) -> tuple[Manifest, Path]:
    path = tmp_path / "manifest.json"
    manifest = Manifest(path, "cnpj", "2026-01")
    artifact = tmp_path / "part.csv"
    raw = b"cnpj\n123\n"
    artifact.write_bytes(raw)
    manifest.pages[artifact.name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    manifest.save()
    return manifest, artifact


def test_resolve_alias_to_canonical_source_and_register_consistent_reuse(tmp_path: Path) -> None:
    manifest, artifact = fixture(tmp_path)
    identity = resolve_manifest_source(manifest)
    assert identity.source_id == "cnpj"
    catalog = FakeCatalog()
    args = dict(
        artifact_id=UUID(int=1),
        partition_id="2026-01",
        dataset_id="cnpj",
        access_class="public",
        storage_root=tmp_path / "objects",
    )
    reference = register_raw_artifact(catalog, manifest, artifact.name, artifact, **args)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert reference == RawArtifactRef(
        source_id="cnpj",
        provider_source_id="receita_federal",
        dataset_id="cnpj",
        artifact_id=UUID(int=1),
        artifact_sha256=digest,
        partition_id="2026-01",
        object_key=f"raw/cnpj/cnpj/2026-01/{digest}",
    )
    assert reference.object_key.endswith("/" + digest)
    assert (args["storage_root"] / reference.object_key).read_bytes() == artifact.read_bytes()
    assert len(catalog.connection.inserted) == 1
    assert register_raw_artifact(catalog, manifest, artifact.name, artifact, **args) == reference
    assert len(catalog.connection.inserted) == 1
    with pytest.raises(ValueError, match="different identity"):
        register_raw_artifact(
            catalog,
            manifest,
            artifact.name,
            artifact,
            **{**args, "artifact_id": UUID(int=9)},
        )


def test_manifest_and_bytes_must_match_before_catalog_write(tmp_path: Path) -> None:
    manifest, artifact = fixture(tmp_path)
    catalog = FakeCatalog()
    artifact.write_bytes(b"altered")
    with pytest.raises(ValueError, match="disagree"):
        register_raw_artifact(
            catalog,
            manifest,
            artifact.name,
            artifact,
            storage_root=tmp_path / "objects",
            artifact_id=UUID(int=2),
            partition_id="2026-01",
            dataset_id="cnpj",
            access_class="public",
        )
    assert not catalog.connection.inserted
    assert not (tmp_path / "objects").exists()


def test_divergent_existing_raw_object_is_not_overwritten(tmp_path: Path) -> None:
    manifest, artifact = fixture(tmp_path)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    storage_root = tmp_path / "objects"
    target = storage_root / "raw" / "cnpj" / "cnpj" / "2026-01" / digest
    target.parent.mkdir(parents=True)
    target.write_bytes(b"preexisting divergent bytes")
    catalog = FakeCatalog()
    with pytest.raises(ValueError, match="existing storage object differs"):
        register_raw_artifact(
            catalog,
            manifest,
            artifact.name,
            artifact,
            storage_root=storage_root,
            artifact_id=UUID(int=3),
            partition_id="2026-01",
            dataset_id="cnpj",
            access_class="public",
        )
    assert target.read_bytes() == b"preexisting divergent bytes"
    assert not catalog.connection.inserted


def test_unknown_source_id_rejected(tmp_path: Path) -> None:
    manifest, _ = fixture(tmp_path)
    manifest.source_id = "free_form_unknown"
    with pytest.raises(ValueError, match="Unknown source"):
        resolve_manifest_source(manifest)


def test_known_catalog_source_without_runner_is_accepted(tmp_path: Path) -> None:
    manifest, artifact = fixture(tmp_path)
    manifest.source_id = "bolsa_familia_bpc"
    manifest.save()
    identity = resolve_manifest_source(manifest)
    assert identity.source_id == "bolsa_familia_bpc"
    assert identity.runner_name is None
    reference = register_raw_artifact(
        FakeCatalog(),
        manifest,
        artifact.name,
        artifact,
        storage_root=tmp_path / "objects",
        artifact_id=UUID(int=4),
        partition_id="2026-01",
        dataset_id="bpc",
        access_class="public",
    )
    assert reference.provider_source_id is None


def test_three_page_interruption_resume_then_catalog_registration(tmp_path: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        calls: list[str] = []
        interrupted = False

        def log_message(self, *args) -> None:
            pass

        def do_GET(self) -> None:
            self.calls.append(self.path)
            body = json_pages[self.path]
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.path == "/two" and not Handler.interrupted:
                Handler.interrupted = True
                self.wfile.write(body[:5])
                self.wfile.flush()
                self.connection.shutdown(2)
                return
            self.wfile.write(body)

    json_pages = {
        "/one": b'{"page":1}',
        "/two": b'{"page":2}',
        "/three": b'{"page":3}',
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        pages = [(f"{name}.json", f"{base}/{name}") for name in ("one", "two", "three")]
        out = tmp_path / "partition"
        manifest_path = out / "manifest.json"
        manifest = Manifest.open(manifest_path, "cnpj", "2026-01")
        with pytest.raises(AcquisitionError):
            Acquisition(retries=0).acquire_pages(manifest, pages, out, "json")

        resumed = Manifest.open(manifest_path, "cnpj", "2026-01")
        assert list(resumed.pages) == ["one.json"]
        catalog = FakeCatalog()
        with pytest.raises(ValueError, match="missing"):
            register_raw_artifact(
                catalog,
                resumed,
                "two.json",
                out / "two.json",
                storage_root=tmp_path / "objects",
                artifact_id=UUID(int=11),
                partition_id="2026-01",
                dataset_id="cnpj",
                access_class="public",
            )
        assert not catalog.connection.inserted
        assert not (tmp_path / "objects").exists()

        Acquisition(retries=0).acquire_pages(resumed, pages, out, "json")
        assert Handler.calls == ["/one", "/two", "/two", "/three"]
        complete = Manifest.open(manifest_path, "cnpj", "2026-01")
        assert set(complete.pages) == {"one.json", "two.json", "three.json"}
        for index, (name, _) in enumerate(pages, start=1):
            raw = (out / name).read_bytes()
            assert raw == json_pages[f"/{name.removesuffix('.json')}"]
            assert hashlib.sha256(raw).hexdigest() == complete.pages[name]["sha256"]
            register_raw_artifact(
                catalog,
                complete,
                name,
                out / name,
                storage_root=tmp_path / "objects",
                artifact_id=UUID(int=20 + index),
                partition_id="2026-01",
                dataset_id="cnpj",
                access_class="public",
            )
        assert len(catalog.connection.inserted) == 3

        corrupted = out / "two.json"
        corrupted.write_bytes(b'{"page":999}')
        with pytest.raises(ValueError, match="disagree"):
            register_raw_artifact(
                catalog,
                complete,
                "two.json",
                corrupted,
                storage_root=tmp_path / "objects",
                artifact_id=UUID(int=99),
                partition_id="2026-01",
                dataset_id="cnpj",
                access_class="public",
            )
        assert len(catalog.connection.inserted) == 3
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
