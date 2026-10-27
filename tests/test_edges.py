"""Edge cases (approved 2026-10-26). Runs on a temp copy; never touches live state, never sends."""
import os, sys, json, copy, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import yaml, scout as sc, style
SAMPLES = "tests/sample_alerts.json" if os.path.exists("tests/sample_alerts.json") else "tests/fixtures/sample_alerts.test.json"
CRIT = "CRITERIA.yaml" if os.path.exists("CRITERIA.yaml") else "CRITERIA.example.yaml"
C = yaml.safe_load(open(CRIT)); sc.CFG.update(C); A = json.load(open(SAMPLES))
al = lambda l, r="new", was=None: [{"reason": r, "was": was, "market": None, "l": l}]
ok = lambda m: not style.check(m)

def test_two_sources_two_prices():
    a = copy.deepcopy(A[0]["l"]); b = copy.deepcopy(a); b.update(id="zillow:x", source="Zillow", price=a["price"] + 55)
    m = sc.merge_dupes([a, b], C); assert len(m) == 1 and m[0]["price"] == a["price"]
    t = sc.render(al(m[0]), C); assert "on Zillow" in t and ok(t)
def test_back_and_lower():
    t = sc.render(al(A[0]["l"], "relist_lower", A[0]["l"]["price"] + 200), C); assert t.startswith("Back, and lower") and "(was " in t and ok(t)
def test_missing_never_guessed():
    l = copy.deepcopy(A[0]["l"]); l.update(price=None, beds=None, address=None); t = sc.render(al(l), C)
    for k in ("Beds", "Rent", "Address"): assert f"{k}: not listed yet" in t
    assert ok(t)
def test_one_caution_line():
    l = copy.deepcopy(A[0]["l"]); l["flags"] = ["suspicious payment/deposit wording", "photo/address mismatch"]
    t = sc.render(al(l), C); assert t.count("See it before paying anything.") == 1 and "money before" not in t and ok(t)
def test_busy_day_top5():
    if len(A) < 10: return
    t = sc.render([dict(x, reason="new") for x in A[:12]], C); assert "And 7 more fit today." in t and "5. " in t and "6. " not in t and ok(t)
def test_templates_clean():
    for m in (style.stopped_owner("Sarah"), style.left_owner("Sarah"), style.left_member(), style.found_ask(), style.wrapped_up(),
              style.media_relay("Sarah", "Maple St"), style.media_unsupported(), style.outage_note("Example PM", "Mon 1:05 PM"), style.full_household()):
        assert ok(m), (m, style.check(m))

def _replies():
    d = tempfile.mkdtemp(); [shutil.copy(os.path.join(HERE, "src", f) if str(f).endswith(".py") else f, d) for f in ("replies.py", "style.py", "notify.py", "scout.py", "features.py", CRIT)]
    os.makedirs(f"{d}/out"); c = yaml.safe_load(open(CRIT)); c["replies"] = True
    c["recipients"] = [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co_decider"}]
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    json.dump([{"id": "a", "where": "Maple St"}, {"id": "b", "where": "Oak Ave"}], open(f"{d}/out/last_numbered.json", "w"))
    json.dump({"Sarah": {"joined": "x"}}, open(f"{d}/out/members.json", "w"))
    run = lambda who, t: subprocess.run([sys.executable, "replies.py", "--as", who, "--text", t], cwd=d, capture_output=True, text=True,
                                        env={**os.environ, "SCOUT_CRITERIA": f"{d}/CRITERIA.yaml"}).stdout
    return d, run
def test_reply_cases():
    d, run = _replies()
    assert "Passed that to Alex." in run("Sarah", "love the kitchen")
    assert "Passed that" not in run("Sarah", "nice yard too")                       # ack once only
    o1, o2 = run("Sarah", "first"), run("Alex", "second")                            # arrival order kept (sequential)
    assert '"first"' in o1 and '"second"' in o2
    json.dump({"Sarah": {"replied": True, "joined": "x"}}, open(f"{d}/out/members.json", "w"))
    json.dump({"ts": __import__("time").time(), "prev": [{"id": "z", "where": "Elm St"}]}, open(f"{d}/out/last_sent.json", "w"))
    assert "Which place" in run("Sarah", "this one looks nice")                    # late reply: ask once
    assert "Sarah on Maple St" in run("Sarah", "this one looks nice")          # then attach to latest
    o = run("Sarah", "STOP"); assert "Sarah turned off texts." in o and "--> to Sarah" not in o
    assert "--> to Sarah" not in run("Alex", "love Oak Ave")                     # stopped: never texted
    assert "wrap up the search" in run("Alex", "we found a place")
    o = run("Alex", "yes"); assert "Congrats on the new place!" in o and "No more listing texts from me." in o and "clear our search data" in o
    o = run("Alex", "no"); assert "keep it for now" in o and "LISTENER_STOP" in o
    os.remove(f"{d}/out/search_ended.json")
    json.dump({"Sarah": {"joined": "x"}}, open(f"{d}/out/members.json", "w"))
    o = run("Sarah", "leave"); assert "Sarah left the search." in o
    assert "ignored" in run("Sarah", "hello")

def test_member_first_text_is_received_at_once():
    d, run = _replies()
    json.dump({}, open(f"{d}/out/members.json", "w"))
    o = run("Sarah", "Hi Listing Scout, I'm in.")
    assert "--> to Sarah:" in o and "Alex said you'd stop by." in o and "Here's what we're looking for:" in o
    assert "--> to Alex:\nSarah is in." in o and "snapshot, same as the owner's" in o
    assert "Sarah is in." not in run("Sarah", "ok")                                 # OK is a receipt, not a second join

def test_member_plain_hi_is_received():
    d, run = _replies()
    json.dump({}, open(f"{d}/out/members.json", "w"))
    o = run("Sarah", "hi")
    assert "--> to Sarah:" in o and "Alex said you'd stop by." in o
    assert "--> to Alex:\nSarah is in." in o

def test_welcome_reflects_real_criteria():
    import re
    lines = sc.reflect(C); w = style.member_welcome("Sarah", "Alex", lines, replies=True); assert ok(w), style.check(w)
    flat = " ".join(lines)
    for city in C["area"].get("cities") or []: assert city in flat, city
    assert f"{C['beds_min']}+ bed" in flat
    for k in ("target_max", "stretch_max"): assert f"{C['price_tiers'][k]:,}" in flat
    if (C.get("match") or {}).get("garage_min"): assert "garage" in flat.lower()
    for x in (C.get("match") or {}).get("layout_any") or []:
        assert {"first_floor": "ground floor", "single_story": "single story", "two_story_townhome": "townhome"}.get(x, x) in flat.lower()
    pet = (C.get("pets") or {}).get("dog") or (C.get("pets") or {}).get("cat")
    if pet: assert pet in flat
    allowed = set(re.findall(r"\d[\d,]*", yaml.safe_dump(C).replace(",", ""))) | {f"{n:,}" for n in (C["price_tiers"]["target_max"], C["price_tiers"]["stretch_max"])}
    for n in re.findall(r"\d[\d,]*", flat): assert n in allowed or n.replace(",", "") in allowed, f"invented number {n}"

if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); n += 1
    print(f"{n} edge tests passed")
