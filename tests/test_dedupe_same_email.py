"""Same alert email twice in one run must still alert once (skipped-alert fix 2026-10-26)."""
import os, sys, json, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src"))
import scout

def L(i, addr="100 Example Ln, Los Angeles, CA 90001"):
    return {"id": i, "address": addr, "source": "Zillow", "garage": scout.U, "layout": scout.U, "pets": scout.U,
            "price": 3000, "beds": 2, "baths": 2, "eligible": True, "match": True}

def test_merge_never_self():
    C = {"baths": {"ideal": 2, "ok": 1}, "match": {}, "mode": "lease"}
    scout.is_match = lambda b, C: True
    m = scout.merge_dupes([L("email:Zillow:1"), L("email:Zillow:1"), L("email:Redfin:9"), L("email:Redfin:9")], C)
    assert len(m) == 1 and m[0]["also_ids"] == ["email:Redfin:9"], m

if __name__ == "__main__":
    test_merge_never_self(); print("ok")
