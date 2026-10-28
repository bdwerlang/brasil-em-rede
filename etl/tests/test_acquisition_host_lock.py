import multiprocessing
import os
import time

import pytest

from bracc_etl.acquisition.host_lock import host_lock


def _hold(host, entered, release):
    with host_lock(host):
        entered.set()
        release.wait(5)


def test_host_lock_serializes_processes():
    context = multiprocessing.get_context("spawn")
    first_entered, second_entered, release = (context.Event() for _ in range(3))
    host = f"test-{os.getpid()}"
    first = context.Process(target=_hold, args=(host, first_entered, release))
    second = context.Process(target=_hold, args=(host, second_entered, release))
    try:
        first.start()
        assert first_entered.wait(5)
        second.start()
        time.sleep(0.25)
        assert not second_entered.is_set()
        release.set()
        assert second_entered.wait(5)
        first.join(5)
        second.join(5)
        assert first.exitcode == second.exitcode == 0
    finally:
        release.set()
        for process in (first, second):
            if process.is_alive():
                process.terminate()
            process.join()


def test_insecure_lock_directory_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    root = tmp_path / f"bracc-acquisition-{os.getuid()}"
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    with pytest.raises(PermissionError), host_lock("example.test"):
        pytest.fail("unsafe lock accepted")
