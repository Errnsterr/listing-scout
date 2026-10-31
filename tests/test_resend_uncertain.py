"""v1.2.13 fix 8: a timed-out send is retried with one honest line (30 chars max), never a silent double."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
sys.argv = ["notify.py"]
if not os.path.exists("CRITERIA.yaml"): os.environ.setdefault("SCOUT_CRITERIA", os.path.join(HERE, "CRITERIA.example.yaml"))
import notify as n

def test_resend_line():
    assert len(n.RESEND_LINE) <= n.style.MAX
    p = n.resend_parts(["New place that fits\n\n2 bed\nCosta Mesa, 92627\n$3,000/mo\n\n1 A St\nhttps://example.com/a\n\nNo rush.\n\nI'll keep watching.", "part 2"])
    assert p[0].startswith(n.RESEND_LINE + "\n\n") and p[1] == "part 2" and not n.style.check(p[0])
    assert n.resend_parts("x")[0] == n.RESEND_LINE + "\n\nx"

if __name__ == "__main__":
    test_resend_line(); print("ok resend test")
