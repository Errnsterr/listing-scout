"""'Email sync stalled' waits the routine's real interval + 3h. inbox_routine_minutes overrides the plan's hours."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, "src")); sys.path.insert(0, HERE)
import features as F

def test_stall_limit():
    assert F.email_stale_limit({"plan_mode": "lean"}) == 15 * 3600
    assert F.email_stale_limit({"plan_mode": "lean", "inbox_routine_minutes": 10}) == 10 * 60 + 3 * 3600
    assert F.email_stale_limit({"inbox_pull": "api", "inbox_routine_minutes": 10}) == 3 * 3600

if __name__ == "__main__":
    test_stall_limit(); print("ok test_stall_limit")
