#!/usr/bin/env python3
"""Shared id check for the email routine and the listener. 'am:<id>' and '<id>' are the same message.
  python3 fetched_ids.py seen '<id>'   -> exit 0 if already handled, 1 if new
  python3 fetched_ids.py add '<id>'    -> records the bare id (under the same lock as the listener)"""
import sys, os, fcntl
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "out", "fetched_ids.txt")
def norm(m):
    """Bare form: strips whitespace, an 'am:' prefix and surrounding <...>."""
    m = str(m).strip()
    if m.startswith("am:"): m = m[3:].strip()
    if m.startswith("<") and m.endswith(">"): m = m[1:-1].strip()
    return m
def main(a):
    if len(a) != 2 or a[0] not in ("seen", "add"): print(__doc__); return 2
    with open(os.path.join(HERE, "out", ".fetched_ids.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        seen = {norm(l) for l in open(F)} if os.path.exists(F) else set()
        if a[0] == "seen": return 0 if norm(a[1]) in seen else 1
        if norm(a[1]) not in seen:
            with open(F, "a") as f: f.write(norm(a[1]) + "\n")
        return 0
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
