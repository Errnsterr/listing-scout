#!/usr/bin/env python3
"""v1.2.16 loop guard. If a rental-loop pass runs longer than, or no pass is logged within, LS_STALL_MIN minutes (default 7, at least
loop_minutes + 2), stop the stuck pass and restart the loop via ensure_running.sh. Never sends anything.
Waits instead if a notify.py send is running (so a text is never cut off mid-send).
  python3 loop_watchdog.py           check, restart if stalled
  python3 loop_watchdog.py --check   print the decision only"""
import os, sys, time, signal, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
S = "src/" if ROOT != HERE else ""

def limit_min():
    n = 5
    try:
        import yaml; n = int(yaml.safe_load(open(os.path.join(ROOT, "CRITERIA.yaml"))).get("loop_minutes") or 5)
    except Exception: pass
    return max(float(os.environ.get("LS_STALL_MIN", "7")), n + 2)

def children(pid):
    try: return [int(x) for x in open(f"/proc/{pid}/task/{pid}/children").read().split()]
    except Exception: return []

def cmd(pid):
    try: return open(f"/proc/{pid}/cmdline").read().replace("\0", " ")
    except Exception: return ""

def decide(now=None, log_mtime=None, limit=None, sending=False, loop_alive=True, start_mtime=None, resumed_at=None):
    """Pure decision: 'ok', 'wait_send', or 'restart'. A pass is running when its start mark is newer than the last
    loop.log line; then the clock is the pass start. Otherwise (sleeping between passes) it is the last line."""
    now = now or time.time(); limit = limit or limit_min()
    if not loop_alive: return "restart"
    ref = start_mtime if (start_mtime and (log_mtime is None or start_mtime > log_mtime)) else log_mtime
    if ref is not None and resumed_at: ref = max(ref, resumed_at)   # time the box was paused doesn't count
    if ref is None or now - ref <= limit * 60: return "ok"
    return "wait_send" if sending else "restart"

def main(argv):
    os.chdir(ROOT)
    if os.path.exists("out/search_ended.json"): return 0
    ll = "logs/loop.log"; mt = os.path.getmtime(ll) if os.path.exists(ll) else None
    try: pid = int(open("logs/loop.pid").read().strip())
    except Exception: pid = None
    alive = bool(pid) and "run_loop.sh" in cmd(pid)
    kids = children(pid) if alive else []
    sending = any("notify.py" in cmd(k) or "photon_send" in cmd(k) for k in kids)
    sm = "out/loop_pass_start"; st = os.path.getmtime(sm) if os.path.exists(sm) else None
    ra = "out/resumed_at"   # v1.2.17: the box was paused; a pass that "took" the pause isn't stuck. Count from the wake-up.
    rz = os.path.getmtime(ra) if os.path.exists(ra) else None
    d = decide(time.time(), mt, None, sending, alive, st, rz)
    if "--check" in argv: print(d); return 0
    if d == "ok": return 0
    stamp = time.strftime("%F %T %Z")
    with open(ll, "a") as f:
        if d == "wait_send": f.write(f"{stamp} watchdog: pass stalled but a send is running; waiting\n"); return 0
        f.write(f"{stamp} watchdog: no pass logged in {limit_min():g} min; restarting loop\n")
    if alive:
        for k in kids:
            if "gonecheck" in cmd(k): continue   # own background job
            try: os.kill(k, signal.SIGTERM)
            except Exception: pass
        try: os.kill(pid, signal.SIGTERM)
        except Exception: pass
        time.sleep(2)
    subprocess.run([f"./{S}ensure_running.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    return 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
