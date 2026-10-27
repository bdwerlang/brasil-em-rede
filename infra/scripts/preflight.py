#!/usr/bin/env python3
"""Read-only local capacity check; does not connect to a database or print secrets."""
import argparse
import os
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("destination", type=Path, help="Existing directory for planned data")
args = parser.parse_args()
if not args.destination.is_dir():
    parser.error("destination must be an existing directory")
usage = shutil.disk_usage(args.destination)
print(f"destination: {args.destination.resolve()}")
print(f"disk_free_bytes: {usage.free}")
print(f"writable: {os.access(args.destination, os.W_OK)}")
try:
    pages = os.sysconf("SC_PHYS_PAGES")
    page_size = os.sysconf("SC_PAGE_SIZE")
    print(f"memory_total_bytes: {pages * page_size}")
except (ValueError, OSError):
    print("memory_total_bytes: unavailable")
print("database_access: not checked")
print("partition_measurement: not performed")
