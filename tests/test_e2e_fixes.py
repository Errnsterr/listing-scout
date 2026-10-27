"""e2e-audit fixes: timezone (New York user), plan-aware email staleness, end my search. Temp copies only; never sends."""
import os, sys, json, time, calendar
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "tests"))
import style, features
from test_features import sandbox

NY = {"timezone": "America/New_York"}
TS = calendar.timegm((2026, 10, 27, 3, 30, 0))   # 03:30 UTC = 11:30 PM in New York, 8:30 PM in Los Angeles

def test_timezone_new_york():
    assert features.local_hour(NY, TS) == 23
    assert features.local_hour({}, TS) == 20                          # default America/Los_Angeles
    assert features.in_quiet(NY, ts=TS) and not features.in_quiet({}, ts=TS)   # Sleep mode / quiet hours follow the search's zone
    assert features.local_str(NY, "%-I:%M %p", TS) == "11:30 PM"       # Sleep offer "That last one came at ..."
    morning = calendar.timegm((2026, 10, 27, 12, 0, 0))               # 8 AM New York
    assert not features.in_quiet(NY, ts=morning)
    eve = calendar.timegm((2026, 10, 27, 22, 30, 0))                  # 6:30 PM New York, 3:30 PM LA: roundup due only for NY
    assert features.local_hour(NY, eve) >= 18 and features.local_hour({}, eve) < 18

def test_example_has_timezone():
    import yaml
    C = yaml.safe_load(open(os.path.join(HERE, "CRITERIA.example.yaml")))
    assert C.get("timezone") == "America/Los_Angeles" and C.get("mode") == "lease"   # rentals stay the default
    assert C.get("buy") and C.get("pace")                                            # buying (experimental) settings ship, used only in mode: buy

def test_via_names_the_linked_site():
    import scout
    U = scout.U
    base = dict(garage=U, layout=U, pets=U, price=700000, beds=3, baths=2, address="1 Example St, Los Angeles, CA 90001")
    r = dict(base, id="redfin:1", source="Redfin", url=None); z = dict(base, id="zillow:1", source="Zillow", url="https://www.zillow.com/homedetails/1_zpid/")
    C = {"baths": {"ideal": 2}, "match": {}, "area": {"zips": ["90001"]}}
    scout.is_match = lambda l, C: True
    m = scout.merge_dupes([r, z], C)[0]
    assert "zillow.com" in m["url"] and scout.via_line(m) == "Via Zillow", (m["source"], m["url"])
    r2 = dict(base, id="redfin:1", source="Redfin", url="https://www.redfin.com/CA/x/home/1"); m = scout.merge_dupes([r2, dict(base, id="zillow:1", source="Zillow", url=z["url"])], C)[0]
    assert scout.via_line(m) == "Via Redfin" and "redfin.com" in m["url"]

def test_stale_limit_follows_plan():
    assert features.email_stale_limit({"plan_mode": "lean"}) == 15 * 3600   # 12h routine + 3h: no false 'stalled' on Lean
    assert features.email_stale_limit({"plan_mode": "standard"}) == 5 * 3600
    assert features.email_stale_limit({"plan_mode": "hands_on"}) == 4 * 3600
    assert features.email_stale_limit({"plan_mode": "lean", "inbox_pull": "api"}) == 3 * 3600

def test_end_texts_fit():
    for t in (style.end_ask(), style.search_ended_note(), style.photon_users_note()): assert not style.check(t), (t, style.check(t))

def test_end_my_search_needs_word_yes_then_ends():
    d, run = sandbox()
    o = run("Alex", "end my search"); assert "End your search for good?" in o and not os.path.exists(f"{d}/out/search_ended.json")
    o = run("Alex", "k"); assert "This search has ended." not in o                 # 'k' is not a word yes
    o = run("Alex", "end my search"); o = run("Alex", "yes")
    assert o.count("This search has ended.") == 2 and "--> to Sarah" in o          # one goodbye to everyone
    assert "PAUSE_ROUTINES" in o and "Users page" in o and "clear our search data" in o
    e = json.load(open(f"{d}/out/search_ended.json")); assert e["pause_routines"] and e["reason"] == "end_my_search"
    o = run("Alex", "yes"); assert "LISTENER_STOP" in o and "CLOSE_SAVED_SEARCHES" in o and "Done, it's all cleared." in o

def test_end_only_owner():
    d, run = sandbox(); o = run("Sarah", "end my search"); assert "End your search for good?" not in o

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); print("ok", k)
