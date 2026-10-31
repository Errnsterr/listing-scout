"""v1.2.15: with inbox_pull: routine, fetch_inbox.py does nothing (no API call, no heartbeat) even if the key is set."""
import os, subprocess, tempfile, shutil
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = tempfile.mkdtemp(); shutil.copy(os.path.join(H, "src", "fetch_inbox.py") if os.path.exists(os.path.join(H, "src", "fetch_inbox.py")) else os.path.join(H, "fetch_inbox.py"), d)
open(os.path.join(d, "CRITERIA.yaml"), "w").write("inbox_pull: routine\nalert_inbox: x@example.com\n")
r = subprocess.run(["python3", "fetch_inbox.py"], cwd=d, env=dict(os.environ, AGENTMAIL_API_KEY="fake"), capture_output=True, text=True)
assert r.returncode == 0 and "error" not in r.stdout, r.stdout
assert not os.path.exists(os.path.join(d, "out", "routine_heartbeat.txt"))
print("ok fetch gate")
