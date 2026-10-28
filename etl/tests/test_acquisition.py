import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from bracc_etl.acquisition import Acquisition, AcquisitionError, Manifest


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        calls = []
        failed = False

        def log_message(self, *args):
            pass

        def do_GET(self):
            self.calls.append((self.path, self.headers.get("Range")))
            if self.path == "/login":
                body = b"<!DOCTYPE html><html>login</html>"
            else:
                body = b'{"page":"' + self.path.encode() + b'","value":"' + b'x' * 100000 + b'"}'
            offset = 0
            if self.headers.get("Range"):
                offset = int(self.headers["Range"].split("=")[1].split("-")[0])
            self.send_response(206 if offset else 200)
            self.send_header("ETag", '"v1"')
            self.send_header("Content-Length", str(len(body) - offset))
            if offset:
                self.send_header("Content-Range", f"bytes {offset}-{len(body)-1}/{len(body)}")
            self.end_headers()
            if self.path == "/one" and not Handler.failed:
                Handler.failed = True
                self.wfile.write(body[:70000])
                self.wfile.flush()
                self.connection.shutdown(2)
            else:
                self.wfile.write(body[offset:])

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", Handler
    httpd.shutdown()
    thread.join()
    httpd.server_close()


def test_resume_checkpoint_and_idempotence(server, tmp_path):
    base, handler = server
    manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
    client = Acquisition(retries=1, backoff=0)
    pages = [("one.json", base + "/one"), ("two.json", base + "/two")]
    client.acquire_pages(manifest, pages, tmp_path, "json")
    assert handler.calls[1][1] is not None
    assert [call[0] for call in handler.calls] == ["/one", "/one", "/two"]
    assert (tmp_path / "one.json").read_bytes().endswith(b'"}')
    assert set(Manifest.open(manifest.path, "source", "partition").pages) == {
        "one.json", "two.json",
    }
    client.acquire_pages(manifest, pages, tmp_path, "json")
    assert len(handler.calls) == 3


@pytest.mark.parametrize("kind", ["csv", "json"])
def test_reject_login(server, tmp_path, kind):
    base, _ = server
    manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
    with pytest.raises(AcquisitionError):
        Acquisition().acquire_pages(manifest, [("page", base + "/login")], tmp_path, kind)
    assert not (tmp_path / "page").exists()
    assert not manifest.pages


def test_export_checksum(tmp_path):
    manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
    data = b'a,b\n1,2\n'
    client = Acquisition()
    client.export(manifest, "page.csv", tmp_path, "csv", lambda p: p.write_bytes(data),
                  hashlib.sha256(data).hexdigest())
    client.export(manifest, "page.csv", tmp_path, "csv", lambda p: pytest.fail("re-export"))
    with pytest.raises(AcquisitionError):
        client.export(
            manifest, "other.csv", tmp_path, "csv", lambda p: p.write_bytes(data), "0" * 64,
        )
    assert not (tmp_path / "other.csv").exists()


def test_host_limit():
    client = Acquisition(per_host=1)
    first = client._host("https://example.test/a")
    second = client._host("https://example.test/b")
    assert first is second
    assert first.acquire(blocking=False)
    assert not second.acquire(blocking=False)
    first.release()
    assert client._host("https://other.test/a").acquire(blocking=False)


def test_legacy_downloader_rejects_partial_status_and_html(monkeypatch, tmp_path):
    import importlib.util
    from contextlib import nullcontext

    import httpx

    path = Path(__file__).parents[1] / "scripts" / "_download_utils.py"
    spec = importlib.util.spec_from_file_location("download_utils", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path / "data.csv"
    partial = tmp_path / "data.csv.partial"
    partial.write_bytes(b"unverified")
    request = httpx.Request("GET", "https://example.test")
    for status, body in [(416, b""), (206, b"wrong"), (200, b"<html>login</html>")]:
        response = httpx.Response(status, content=body, request=request)
        monkeypatch.setattr(
            module.httpx, "stream", lambda *a, response=response, **kw: nullcontext(response),
        )
        assert not module.download_file(str(request.url), target)
        assert not target.exists()


def test_failed_page_does_not_skip_next(server, tmp_path):
    base, handler = server
    manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
    pages = [("one", base + "/one"), ("two", base + "/two")]
    with pytest.raises(AcquisitionError):
        Acquisition(retries=0).acquire_pages(manifest, pages, tmp_path, "json")
    assert not manifest.pages
    assert [call[0] for call in handler.calls] == ["/one"]
    Acquisition(retries=0).acquire_pages(manifest, pages, tmp_path, "json")
    assert set(manifest.pages) == {"one", "two"}
    assert handler.calls[1][1] is not None


def test_invalid_range_cannot_publish(monkeypatch, tmp_path):
    import io
    import json

    import bracc_etl.acquisition.client as module

    class Response(io.BytesIO):
        status = 206
        headers = {"ETag": '"v1"', "Content-Range": "bytes 1-2/3", "Content-Length": "2"}

    url = "http://example.test/page"
    (tmp_path / "page.part").write_bytes(b"12345")
    (tmp_path / "page.part.json").write_text(json.dumps({
        "etag": '"v1"', "url_hash": hashlib.sha256(url.encode()).hexdigest(),
    }))
    class Opener:
        def open(self, *args, **kwargs):
            return Response(b"xx")

    monkeypatch.setattr(module, "build_opener", lambda *args: Opener())
    manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
    with pytest.raises(AcquisitionError, match="invalid partial"):
        Acquisition().acquire_pages(manifest, [("page", url)], tmp_path, "binary")
    assert not (tmp_path / "page").exists()


def test_changed_source_reacquires_page(server, tmp_path):
    base, handler = server
    handler.failed = True
    manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
    client = Acquisition()
    client.acquire_pages(manifest, [("page", base + "/one")], tmp_path, "json")
    original = (tmp_path / "page").read_bytes()
    client.acquire_pages(manifest, [("page", base + "/two")], tmp_path, "json")
    assert (tmp_path / "page").read_bytes() != original
    assert [call[0] for call in handler.calls] == ["/one", "/two"]
    assert base not in manifest.path.read_text()




def test_ftp_resume_and_checksum(tmp_path):
    import json
    from threading import Thread
    from typing import override

    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer

    source = tmp_path / "remote"
    source.mkdir()
    data = b"name,value\n" + b"a,b\n" * 50000
    (source / "data.csv").write_bytes(data)
    authorizer = DummyAuthorizer()
    authorizer.add_anonymous(str(source), perm="elr")
    offsets = []

    class Handler(FTPHandler):
        @override
        def ftp_REST(self, line):
            offsets.append(int(line))
            return super().ftp_REST(line)

    Handler.authorizer = authorizer
    server = FTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, kwargs={"timeout": 0.1}, daemon=True)
    thread.start()
    try:
        url = f"ftp://127.0.0.1:{server.socket.getsockname()[1]}/data.csv"
        out = tmp_path / "out"
        out.mkdir()
        checksum = hashlib.sha256(data).hexdigest()
        (out / "page.part").write_bytes(data[:12345])
        (out / "page.part.json").write_text(json.dumps({
            "url_hash": hashlib.sha256(url.encode()).hexdigest(), "checksum": checksum,
        }))
        manifest = Manifest.open(out / "manifest.json", "source", "partition")
        Acquisition().acquire_pages(manifest, [("page", url)], out, "csv", {"page": checksum})
        assert (out / "page").read_bytes() == data
        assert offsets == [12345]
        (out / "other.part").write_bytes(b"stale")
        Acquisition().acquire_pages(manifest, [("other", url)], out, "csv")
        assert (out / "other").read_bytes() == data
        assert offsets == [12345]
        (out / "bad.part").write_bytes(b"wrong prefix")
        bad_checksum = hashlib.sha256(data).hexdigest()
        (out / "bad.part.json").write_text(json.dumps({
            "url_hash": hashlib.sha256(url.encode()).hexdigest(), "checksum": bad_checksum,
        }))
        with pytest.raises(AcquisitionError, match="checksum"):
            Acquisition().acquire_pages(manifest, [("bad", url)], out, "csv",
                                        {"bad": bad_checksum})
        assert not (out / "bad").exists()
    finally:
        server.close_all()
        thread.join(5)


def test_http_redirect_rejected(tmp_path):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    class Redirect(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "file:///etc/passwd")
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
        with pytest.raises(AcquisitionError):
            Acquisition(retries=0).acquire_pages(
                manifest, [("page", f"http://127.0.0.1:{httpd.server_port}/")],
                tmp_path, "binary",
            )
        assert not manifest.pages
    finally:
        httpd.shutdown()
        thread.join()
        httpd.server_close()


def test_ftp_interruption_resumes(monkeypatch, tmp_path):
    from contextlib import asynccontextmanager

    import bracc_etl.acquisition.client as module

    data = b"name,value\na,b\n"
    offsets = []

    class Stream:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def iter_by_block(self, size):
            if len(offsets) == 1:
                yield data[:5]
                raise OSError("connection interrupted")
            yield data[offsets[-1]:]

    class Client:
        async def stat(self, path):
            return {"size": str(len(data))}

        def download_stream(self, path, *, offset):
            offsets.append(offset)
            return Stream()

    @asynccontextmanager
    async def fake_context(*args, **kwargs):
        yield Client()

    monkeypatch.setattr(module.aioftp.Client, "context", fake_context)
    manifest = Manifest.open(tmp_path / "manifest.json", "source", "partition")
    checksum = hashlib.sha256(data).hexdigest()
    Acquisition(retries=1, backoff=0).acquire_pages(
        manifest, [("page", "ftp://example.test/file")], tmp_path, "csv", {"page": checksum},
    )
    assert offsets == [0, 5]
    assert (tmp_path / "page").read_bytes() == data
