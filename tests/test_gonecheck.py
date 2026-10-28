"""v1.2.9 'Still listed?' check: gone only on a clear signal; blocks are unknown; never texts; never edits state."""
import os, sys, json, tempfile, shutil, importlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import gonecheck as g

Z = "https://www.zillow.com/homedetails/1_zpid/"; R = "https://www.redfin.com/CA/Town/1-Main-St-90001/home/1"; H = "https://hotpads.com/x-ca-90001-abc/pad"

def test_clear_signals_only():
    assert g.classify_response(404, None, "", Z)[0] == "gone"
    assert g.classify_response(410, None, "", R)[0] == "gone"
    assert g.classify_response(301, "/homes/for_rent/Town-CA/", "", Z)[0] == "gone"            # sent to a search page
    assert g.classify_response(302, "https://www.redfin.com/city/1/CA/Town", "", R)[0] == "gone"
    assert g.classify_response(302, "/x-ca-90001/apartments-for-rent", "", H)[0] == "gone"
    assert g.classify_response(200, None, "<h1>This home is off market</h1>", Z)[0] == "gone"
    assert g.classify_response(200, None, "Sorry, this listing is no longer available.", H)[0] == "gone"
    assert g.classify_response(200, None, "This unit has been rented.", H)[0] == "gone"
    assert g.classify_response(200, None, "<h1>3 bed apartment</h1> Recently rented nearby homes", Z)[0] == "live"   # 'rented nearby' is not this home
    assert g.classify_response(302, "/homedetails/1-Main/1_zpid/", "", Z)[0] == "follow"
    tmpl = '<script>{"removedListingHeading":"Sorry, {address} is no longer available."}</script><h1>2 bed</h1>'
    assert g.classify_response(200, None, tmpl, H)[0] == "live"                                   # site code, not the page          # canonical URL: follow it

def test_blocks_are_unknown():
    for st in (403, 429, 500, 503):
        assert g.classify_response(st, None, "", Z)[0] == "unknown"
    assert g.classify_response(200, None, "Press & Hold to confirm you are a human", Z)[0] == "unknown"
    assert g.classify_response(200, None, "<div id=px-captcha>", R)[0] == "unknown"
    assert g.check(Z, get=lambda u: (None, None, "TimeoutError"))[0] == "unknown"
    assert g.classify_response(302, "https://captcha.example.com/", "", Z)[0] == "unknown"        # off-site: never followed

def _box():
    d = tempfile.mkdtemp(); os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs")
    S = {"email:Zillow:1": {"eligible": True}, "email:Redfin:2": {"eligible": True}, "email:addr:3": {"eligible": True},
         "email:addr:4": {"eligible": False}, "appfolio:5": {"eligible": True}}
    json.dump({"listings": S}, open(f"{d}/state.json", "w"))
    json.dump({"email:Zillow:1": {"where": "Main", "likes": ["A"]}, "appfolio:5": {"where": "Elm"}}, open(f"{d}/out/shortlist.json", "w"))
    json.dump([{"id": "email:Zillow:1", "where": "Main"}, {"id": "email:Redfin:2", "where": "Oak"}], open(f"{d}/out/last_numbered.json", "w"))
    return d

def test_apply_marks_and_lists_never_state():
    d = _box(); old = g.HERE, g.GONE_FILE, g.inbox_links
    g.HERE, g.GONE_FILE = d, f"{d}/out/link_gone.json"
    g.inbox_links = lambda: {"email:Zillow:1": Z, "email:Redfin:2": R, "email:addr:3": H, "email:addr:4": H}
    resp = {Z: (404, None, ""), R: (403, None, ""), H: (200, None, "<h1>2 bed</h1>")}
    seen = []
    try:
        before = open(f"{d}/state.json").read()
        g.main(["--apply", "--daily"], get=lambda u: seen.append(u) or resp[u], sleep=lambda s: None)
        assert sorted(seen) == sorted([Z, R, H])                                   # one GET each; ineligible/non-email skipped
        assert json.load(open(f"{d}/out/link_gone.json")).keys() == {"email:Zillow:1"}
        assert open(f"{d}/state.json").read() == before                             # state never edited
        assert "email:Zillow:1" not in json.load(open(f"{d}/out/shortlist.json"))
        assert "email:Zillow:1" in json.load(open(f"{d}/out/shortlist_gone.json"))  # notes kept
        assert [x["id"] for x in json.load(open(f"{d}/out/last_numbered.json"))] == ["email:Redfin:2"]
        last = json.load(open(f"{d}/out/gonecheck.json"))["last"]
        assert (last["checked"], last["gone"], last["unknown"], last["live"]) == (3, 1, 1, 1)
        seen.clear(); g.main(["--apply", "--daily"], get=lambda u: seen.append(u) or resp[u], sleep=lambda s: None)
        assert seen == []                                                           # at most once a day
        assert "marked gone | email:Zillow:1" in open(f"{d}/logs/gonecheck.log").read()
    finally:
        g.HERE, g.GONE_FILE, g.inbox_links = old; shutil.rmtree(d)

def test_dry_run_changes_nothing():
    d = _box(); old = g.HERE, g.GONE_FILE, g.inbox_links
    g.HERE, g.GONE_FILE = d, f"{d}/out/link_gone.json"; g.inbox_links = lambda: {"email:Zillow:1": Z}
    try:
        g.main([], get=lambda u: (404, None, ""), sleep=lambda s: None)
        assert not os.path.exists(f"{d}/out/link_gone.json") and "email:Zillow:1" in json.load(open(f"{d}/out/shortlist.json"))
    finally:
        g.HERE, g.GONE_FILE, g.inbox_links = old; shutil.rmtree(d)

def test_never_texts_and_still_available_text_ignores_it():
    src = open(os.path.join(HERE, "src", "gonecheck.py")).read()
    assert "notify" not in src.split('"""', 2)[2] and "photon" not in src.lower().split('"""', 2)[2]
    import features
    S = {"email:Zillow:1": {"gone_since": None}}; SL = {"email:Zillow:1": {"where": "Main", "likes": ["A"]}}
    assert features.gone_liked(S, SL) == []                                         # link_gone never feeds the 'Still available?' text

if __name__ == "__main__":
    n = 0
    for k, v in list(globals().items()):
        if k.startswith("test_"): v(); n += 1
    print(f"ok {n} tests")
