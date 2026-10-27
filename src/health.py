#!/usr/bin/env python3
"""Weekly health check for Listing Scout (no AI, sends nothing). Prints a short plain report.
  python3 src/health.py            # report; exit 1 if something needs attention
  python3 src/health.py --restart  # also restart the loop if it is down (keeps exactly one)
The weekly bot routine runs this with --restart and tells the owner only if something is wrong."""
import os, sys, re, json, time, subprocess, yaml
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
os.chdir(HERE)
C = yaml.safe_load(open("CRITERIA.yaml")); issues = []
pid = open("logs/loop.pid").read().strip() if os.path.exists("logs/loop.pid") else ""
alive = bool(pid) and os.path.exists(f"/proc/{pid}/cmdline") and b"run_loop.sh" in open(f"/proc/{pid}/cmdline", "rb").read()
n = len(subprocess.run(["pgrep", "-f", "bash ./src/run_loop.sh"], capture_output=True, text=True).stdout.split())
if not alive:
    issues.append("watcher loop is not running")
    if "--restart" in sys.argv: subprocess.run(["./src/ensure_running.sh"]); issues[-1] += " (restart attempted)"
if n > 1: issues.append(f"{n} loops running; should be 1")
log = open("logs/loop.log").read().splitlines() if os.path.exists("logs/loop.log") else []
runs = [l for l in log if " ok mode=" in l or "scout failed" in l]
interval = 15 if C.get("plan_mode") == "lean" else 5
if runs:
    last = time.mktime(time.strptime(runs[-1][:19], "%Y-%m-%d %H:%M:%S"))
    age = (time.time() - last) / 60
    if age > interval * 3: issues.append(f"last check was {age:.0f} min ago (expected every {interval})")
    fails = sum("scout failed" in l for l in runs[-20:])
    if fails: issues.append(f"{fails} of the last {min(20, len(runs))} checks failed")
else: issues.append("no checks logged yet")
err = open("logs/scout.err").read() if os.path.exists("logs/scout.err") else ""
lastrun = err.split("== SOURCES ==")[-1]
bad = [l.split(" | ")[0] for l in lastrun.splitlines() if " | ERROR | " in l]
if bad: issues.append("sources with errors on the last check: " + ", ".join(bad))
nl = open("logs/notify.log").read() if os.path.exists("logs/notify.log") else ""
if "Not sent:" in nl[-5000:]: issues.append("a recent text was not accepted by Photon (see logs/notify.log)")
inbox = [f for f in os.listdir("inbox") if not f.startswith(".")] if os.path.isdir("inbox") else []
st = json.load(open("state.json"))["listings"] if os.path.exists("state.json") else {}
# Secrets, listener, email path (flags written by ensure_running.sh / fetch_inbox.py; nothing printed but names)
fl = json.load(open("out/health_flags.json")) if os.path.exists("out/health_flags.json") else {}
if "photon_key_missing" in fl: issues.append("Photon key missing: add it to ~/.config/listing-scout/env via the secure flow (texts are off)")
if "listener_restarted" in fl: issues.append(f"reply listener was down and restarted (since {fl['listener_restarted']['since']}); owner told once")
if "email_pull_missing" in fl and (C.get("inbox_pull") or "") != "routine": issues.append("email alerts aren't being pulled: set AGENTMAIL_API_KEY or a 10-minute inbox routine (inbox_pull: routine)")
if any(s.get("type") == "email" for s in C.get("sources", [])) and not os.path.exists("out/email_proven.json"):
    issues.append("email path unproven: no real Zillow/Redfin/HotPads alert has been parsed yet (check each site's email is verified)")
if C.get("replies"):
    lp = open("logs/listen.pid").read().strip() if os.path.exists("logs/listen.pid") else ""
    if not (lp and os.path.exists(f"/proc/{lp}/cmdline") and b"listen.mjs" in open(f"/proc/{lp}/cmdline", "rb").read()):
        issues.append("reply listener is not running" + (" (restart attempted)" if "--restart" in sys.argv else ""))
        if "--restart" in sys.argv: subprocess.run(["./src/ensure_running.sh"])
print(f"Listing Scout health {time.strftime('%F %H:%M %Z')}")
print(f"loop: {'running' if alive else 'DOWN'} (pid {pid or '-'}), {len(runs)} checks logged, plan {C.get('plan_mode')}")
print(f"tracking {len(st)} listings; {len(inbox)} alert emails in inbox/")
print("OK" if not issues else "NEEDS ATTENTION:\n- " + "\n- ".join(issues))
sys.exit(1 if issues else 0)
