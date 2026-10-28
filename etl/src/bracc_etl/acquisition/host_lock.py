"""Host serialization across cooperating processes on a single machine."""

from __future__ import annotations

import fcntl
import hashlib
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def host_lock(host: str) -> Iterator[None]:
    """Serialize a host per user; all cooperating clients must share the same temp directory."""
    root = Path(tempfile.gettempdir()) / f"bracc-acquisition-{os.getuid()}"
    root.mkdir(mode=0o700, exist_ok=True)
    st = root.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise PermissionError("unsafe acquisition lock directory")
    name = hashlib.sha256(host.lower().encode()).hexdigest()
    fd = os.open(root / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)
