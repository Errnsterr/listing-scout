"""v1.2.15/v1.2.19: with inbox_pull: routine, fetch_inbox.py never reads alert_inbox (the routine's inbox);
since v1.2.19 it runs the listener's catch-up instead, fail-safe: an unreachable API -> exit 0, no heartbeat, no files."""
import os, subprocess, tempfile, shutil
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(H, "src") if os.path.exists(os.path.join(H, "src", "fetch_inbox.py")) else H
d = tempfile.mkdtemp()
for f in ("fetch_inbox.py", "mail_listener.py", "fetched_ids.py"): shutil.copy(os.path.join(S, f), d)
open(os.path.join(d, "CRITERIA.yaml"), "w").write("inbox_pull: routine\nalert_inbox: x@example.com\n")
r = subprocess.run(["python3", "fetch_inbox.py"], cwd=d, capture_output=True, text=True, timeout=90,
                   env=dict(os.environ, AGENTMAIL_API_KEY="fake", LS_ROOT=d, LS_AGENTMAIL_API="http://127.0.0.1:9/v0"))
assert r.returncode == 0 and "catch-up: error" in r.stdout, r.stdout
assert not os.path.exists(os.path.join(d, "out", "routine_heartbeat.txt"))
assert not os.listdir(os.path.join(d, "inbox")) and "fake" not in r.stdout + r.stderr
print("ok fetch gate")
