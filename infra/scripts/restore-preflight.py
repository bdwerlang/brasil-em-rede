#!/usr/bin/env python3
"""Inspect a candidate backup and empty destination; never restore or modify data."""
import argparse
import hashlib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("backup", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
if not args.backup.is_file() or args.backup.is_symlink():
    parser.error("backup must be a regular, non-symlink file")
if not args.destination.is_dir() or args.destination.is_symlink() or any(args.destination.iterdir()):
    parser.error("destination must be an existing, empty, non-symlink directory")
hash_value = hashlib.sha256()
with args.backup.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        hash_value.update(chunk)
print(f"backup_size_bytes: {args.backup.stat().st_size}")
print(f"backup_sha256: {hash_value.hexdigest()}")
print("destination_empty: true")
print("restore: not performed; compatibility and recovery are not verified")
