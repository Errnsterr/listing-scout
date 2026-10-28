#!/usr/bin/env python3
"""Weekly health check for Listing Scout (no AI, sends nothing). Prints a short plain report.
  python3 src/health.py            # report; exit 1 if something needs attention
  python3 src/health.py --restart  # also restart the loop if it is down (keeps exactly one)
  python3 src/health.py --restart --quiet   # safe every 10 minutes: prints nothing and exits 0 when all is well
The weekly bot routine runs this with --restart and tells the owner only if something is wrong."""
import os, sys, re, json, time, subprocess, yaml
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
os.chdir(HERE)
if "--restart" in sys.argv:   # v1.2.11: heal first (npm ci, restore missing files only, block on re-text risk)
    subprocess.run(["python3", os.path.join(_SRC, "selfheal.py")], capture_output=True)
C = yaml.safe_load(open("CRITERIA.yaml")); issues = []
SHADOW = os.path.exists("SHADOW_ONLY")   # shadow-only proof install: the loop is run_shadow.sh (never sends)
LOOP = "run_shadow.sh" if SHADOW else "run_loop.sh"
pidf = "logs/run_shadow.pid" if SHADOW else "logs/loop.pid"
pid = open(pidf).read().strip() if os.path.exists(pidf) else ""
alive = bool(pid) and os.path.exists(f"/proc/{pid}/cmdline") and LOOP.encode() in open(f"/proc/{pid}/cmdline", "rb").read()
S = "src/" if os.path.basename(_SRC) == "src" else ""   # src/ (repo) or a flat install
n = len(subprocess.run(["pgrep", "-f", f"bash ./{LOOP}" if SHADOW else f"bash ./{S}run_loop.sh"], capture_output=True, text=True).stdout.split())
if not alive:
    issues.append(("shadow " if SHADOW else "") + "watcher loop is not running")
    if "--restart" in sys.argv and n == 0:
        if SHADOW:   # no keys in its environment, ever
            env = {k: v for k, v in os.environ.items() if not re.match(r"(PHOTON|AGENTMAIL)_", k)}
            subprocess.Popen(["bash", "./run_shadow.sh"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        else: subprocess.run([f"./{S}ensure_running.sh"])
        issues[-1] += " (restart attempted)"
if n > 1: issues.append(f"{n} loops running; should be 1")
log = open("logs/loop.log").read().splitlines() if os.path.exists("logs/loop.log") else []
runs = [l for l in log if " ok mode=" in l or " ok files=" in l or "scout failed" in l]
interval = 15 if SHADOW else max(1, int(C.get("loop_minutes") or 5))   # same rule as the loop script
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
# Texts failing for 30+ minutes: every send since the last success failed, and the first of them is 30+ min old
sends = [json.loads(x) for x in open("logs/sends.jsonl")] if os.path.exists("logs/sends.jsonl") else []
sends = [x for x in sends if not x.get("dry_run")]
tail_fail = []
for x in reversed(sends):
    if x.get("ok"): break
    tail_fail.append(x)
ff = json.load(open("out/health_flags.json")) if os.path.exists("out/health_flags.json") else {}
if tail_fail:
    first = time.mktime(time.strptime(tail_fail[-1]["ts"][:19], "%Y-%m-%d %H:%M:%S"))
    mins = (time.time() - first) / 60
    if mins >= 30:
        issues.append(f"texts have failed for {mins:.0f} min ({len(tail_fail)} sends, Photon): nobody is getting alerts")
        ff.setdefault("send_failing", {"since": tail_fail[-1]["ts"]})
elif "send_failing" in ff: ff.pop("send_failing")
os.makedirs("out", exist_ok=True); json.dump(ff, open("out/health_flags.json", "w"))
# Alert emails that may have lost places (cut off by the mail reader, or a subject price never parsed)
cut = json.load(open("out/email_cutoff.json")) if os.path.exists("out/email_cutoff.json") else {}
notes = []
if cut and SHADOW: notes.append(f"{len(cut)} alert email(s) may be cut off; left as they are in this proof run")
elif cut: issues.append(f"{len(cut)} alert email(s) may be cut off ({', '.join(sorted(cut)[:3])}{'...' if len(cut) > 3 else ''}): re-read in full (50,000 characters)")
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
        if "--restart" in sys.argv: subprocess.run([f"./{S}ensure_running.sh"])
# v1.2.11: backups and self-heal
try: HS = json.loads(subprocess.run(["python3", os.path.join(_SRC, "selfheal.py"), "--status"], capture_output=True, text=True).stdout or "[]")
except Exception: HS = []
for h in HS:
    nm = os.path.basename(h["install"])
    if h.get("heal_blocked"): issues.append(f"{nm}: sends blocked by self-heal (see logs/heal.log)")
    if not h.get("last_backup_ts"): issues.append(f"{nm}: no automatic backup yet")
    elif time.time() - h["last_backup_ts"] > 3 * 3600: issues.append(f"{nm}: last backup {h['last_backup']} is over 3 hours old")
    notes.append(f"{nm}: last backup {h.get('last_backup') or 'none'}{' (+ off-box copy)' if h.get('mirrored') else ''}; last heal: {h.get('last_heal') or 'none'}")
if "--quiet" in sys.argv and not issues: sys.exit(0)   # every-10-minutes use: say nothing when all is well
print(f"Listing Scout health {time.strftime('%F %H:%M %Z')}")
print(f"{'shadow loop (sends nothing)' if SHADOW else 'loop'}: {'running' if alive else 'DOWN'} (pid {pid or '-'}), {len(runs)} checks logged, plan {C.get('plan_mode')}")
for x in notes: print("note: " + x)
print(f"tracking {len(st)} listings; {len(inbox)} alert emails in inbox/")
print("OK" if not issues else "NEEDS ATTENTION:\n- " + "\n- ".join(issues))
sys.exit(1 if issues else 0)
