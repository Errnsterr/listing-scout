"""v1.2.10: held buildings text once as 'From $X/mo'; a daily market snapshot (inbox/market/*.json) fills email gaps
without re-texting; every text is logged (names only); Redfin unit ranges keep a price; long building names wrap."""
import os, sys, json, tempfile, shutil, subprocess, yaml, copy
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, style
FX = os.path.join(HERE, "tests", "fixtures")
C0 = yaml.safe_load(open(os.path.join(FX, "CRITERIA.test.yaml")))

def _box(market_rows=None):
    d = tempfile.mkdtemp()
    for x in ("out", "logs", "inbox", "inbox/market"): os.makedirs(os.path.join(d, x), exist_ok=True)
    for n in ("3021702", "3021665"): shutil.copy(os.path.join(FX, "hotpads_text", f"hotpads_{n}.txt"), os.path.join(d, "inbox", f"hotpads-{n}.txt"))
    C = copy.deepcopy(C0); C["beds_min"] = 2; C.setdefault("match", {})["price_max"] = 5000
    C["sources"] = [{"name": "alerts", "type": "email", "dir": "inbox"}, {"name": "Market snapshot", "type": "market", "dir": os.path.join(d, "inbox", "market")}]
    yaml.safe_dump(C, open(os.path.join(d, "CRITERIA.yaml"), "w"))
    if market_rows is not None: json.dump(market_rows, open(os.path.join(d, "inbox", "market", "m.json"), "w"))
    return d

def _run(d, *extra):
    p = subprocess.run([sys.executable, os.path.join(HERE, "src", "scout.py"), "--json", "--matches-only", *extra], cwd=d, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(p.stdout) if "--seed" not in extra else None

def test_held_building_texts_once():
    d = _box()
    _run(d, "--seed")
    st = json.load(open(f"{d}/state.json"))
    for k in ("email:addr:1562-testwood7", "email:addr:2238-testwood10"): st["listings"][k]["held_review"] = True
    json.dump(st, open(f"{d}/state.json", "w"))
    A = _run(d)
    assert [a["l"]["id"] for a in A] == ["email:addr:1562-testwood7"], [a["l"]["id"] for a in A]   # no price: stays held
    assert A[0]["reason"] == "new"
    t = sc.render_parts(A, yaml.safe_load(open(f"{d}/CRITERIA.yaml")))[0]
    assert "From $1,797/mo" in t and "0-2 bed" in t and not style.check(t), t
    st = json.load(open(f"{d}/state.json"))["listings"]
    assert not st["email:addr:1562-testwood7"]["held_review"] and st["email:addr:2238-testwood10"]["held_review"]
    assert _run(d) == []                                                   # never twice

def test_blocked_run_marks_nothing():
    d = _box(); _run(d, "--seed")
    st = json.load(open(f"{d}/state.json"))
    st["listings"]["email:addr:1562-testwood7"]["held_review"] = True; json.dump(st, open(f"{d}/state.json", "w"))
    json.dump({"reason": "test"}, open(f"{d}/out/search_ended.json", "w"))
    before = open(f"{d}/state.json").read()
    assert len(_run(d)) == 1 and open(f"{d}/state.json").read() == before     # previewed, never saved
    os.remove(f"{d}/out/search_ended.json")
    assert len(_run(d)) == 1 and _run(d) == []                              # after resume: once

def test_held_not_released_when_texted_or_gone():
    l = {"id": "a", "eligible": True, "match": True, "price": 2000, "price_from": True, "beds_range": [0, 2], "beds_max": 2}
    C = {"beds_min": 2, "match": {"price_max": 5000}}
    assert sc.held_release_ok(l, C, set(), {})
    assert not sc.held_release_ok(l, C, {"a"}, {}) and not sc.held_release_ok(l, C, set(), {"a": {}})
    assert not sc.held_release_ok(dict(l, price=5100), C, set(), {})
    assert not sc.held_release_ok(dict(l, beds_range=[0, 1], beds_max=1), C, set(), {})
    assert not sc.held_release_ok(dict(l, price=None), C, set(), {})

ROWS = [
    {"site": "Zillow", "address": "418 Larkspur Pl APT C, Shelbyville, CA", "zip": "90001", "price": "$3,600/mo", "beds": "2", "baths": "1", "age_shown": "1 day ago", "url": "https://www.zillow.com/homedetails/x/1_zpid/"},   # same place as an email (APT vs #)
    {"site": "HotPads", "address": "Testwood Seven Lofts, Los Angeles", "zip": "90002", "price": "$1,797+/mo", "beds": "Studio - 2", "baths": "", "age_shown": "New Today", "url": "https://hotpads.com/testwood-seven-lofts-los-angeles-ca-90002-abc123/pad"},
    {"site": "Zillow", "address": "77 New Market St #4, Los Angeles, CA", "zip": "90002", "price": "$3,100/mo", "beds": "2", "baths": "2", "age_shown": "2 hours ago", "url": "https://www.zillow.com/homedetails/77-New-Market/9_zpid/"},
    {"site": "Redfin", "address": "77 New Market St #4, Los Angeles, CA", "zip": "90002", "price": "$3,100", "beds": "2", "baths": "2", "age_shown": "NEW 2 HRS AGO", "url": "https://www.redfin.com/CA/x/home/9"},
    {"site": "HotPads", "address": "Brand New Court, Los Angeles", "zip": "90003", "price": "$2,400+/mo", "beds": "1 - 3", "baths": "", "age_shown": "New Today", "url": "https://hotpads.com/brand-new-court-los-angeles-ca-90003-zz9/pad"},
    {"site": "Zillow", "address": "9 Too Pricey Rd, Los Angeles, CA", "zip": "90001", "price": "$7,000/mo", "beds": "3", "baths": "2", "age_shown": "1 hour ago", "url": "https://www.zillow.com/homedetails/9/8_zpid/"},
]

def test_market_rows_parse():
    r = sc.market_row(ROWS[1]); assert r["price"] == 1797 and r["price_from"] and r["beds_range"] == [0, 2] and r["building"] == "Testwood Seven Lofts"
    r = sc.market_row(ROWS[2]); assert r["id"] == "email:addr:77-new-market-4" and r["beds"] == 2 and r["baths"] == 2 and not r["price_from"]
    assert sc.market_row({"site": "Redfin", "address": "1 A St, Town, CA", "price": "", "beds": "2"})["price"] is None   # blank price: unknown, never guessed

def test_market_source_dedupes_and_never_retexts():
    d = _box(ROWS)
    with open(f"{d}/inbox/market/m.json") as f: rows = json.load(f)
    os.rename(f"{d}/inbox/market/m.json", f"{d}/m.json")   # first: emails only, saved as seen
    _run(d, "--seed")
    texted = [{"id": "email:addr:1562-testwood7", "bkeys": ["n:testwood seven lofts"], "name": "Testwood Seven Lofts", "ts": "x"}]
    json.dump(texted, open(f"{d}/out/texted.json", "w"))
    os.rename(f"{d}/m.json", f"{d}/inbox/market/m.json")
    A = _run(d)
    ids = [a["l"]["id"] for a in A]
    assert ids.count("email:addr:77-new-market-4") == 1, ids                   # two sites, one place, one text
    assert "email:addr:418-larkspur-c" not in ids                               # emailed already (APT C == #C)
    assert not any("testwood-seven" in i for i in ids), ids                     # texted building (by name)
    assert any("brand-new-court" in i for i in ids), ids                        # a true miss
    assert not any("too-pricey" in i for i in ids)                              # over the cap
    assert _run(d) == []                                                        # next pass: nothing again
    st = json.load(open(f"{d}/state.json"))["listings"]
    assert st["email:addr:418-larkspur-c"]["price"] == 3600                      # a snapshot never rewrites a saved price

def test_url_key():
    assert sc.url_key("https://www.zillow.com/homedetails/a/12_zpid/") == sc.url_key("https://zillow.com/homedetails/b/12_zpid") == "z:12"
    assert sc.url_key("https://hotpads.com/x-ca-90001-ab/pad?utm=1") == "h:x-ca-90001-ab"
    assert sc.url_key("https://www.redfin.com/CA/T/1-Main-St-90001/home/55") == "r:55"

def test_redfin_range_has_price_and_shows_range():
    C = {"mode": "lease", "area": {"cities": ["Springfield"], "zips": ["90001"]}, "beds_min": 2, "price_tiers": {"target_max": 4000, "stretch_max": 5000},
         "baths": {"ok": 1, "ideal": 2}, "pets": {}, "match": {}, "show_source": False}
    sc.CFG.clear(); sc.CFG.update(C)
    body = "message_id 1\n\n$3,130-$3,295/mo\n\n2 Beds &middot; 2 Baths &middot; 862-932 Sq. Ft.\n\nThe Cape, Springfield, CA 90001 (https://redmail3.redfin.com/a/click?_t=a)\n"
    r = sc._parse_text_cards(body, "Redfin", "f")[0]
    assert r["price"] == 3130 and r["price_range"] == [3130, 3295] and r["id"].endswith("-x-2-932")
    sc.classify(r, C); t = sc.render([{"reason": "new", "l": r}], C)
    assert "$3,130-$3,295/mo" in t and "Rent: not listed yet" not in t and "target range" not in t, t

def test_long_building_name_wraps():
    L = sc.another_lines("Newport Bluffs Apartment Village")
    assert all(len(x) <= style.MAX for x in L) and " ".join(L) == "Another unit at Newport Bluffs Apartment Village", L

def test_building_name_is_not_a_type():
    l = {"title": "$3,324+/mo 1 to 2 beds Halcyon House 585 Anton Blvd, Costa Mesa, CA 92626", "home_type_raw": "house",
         "url": "https://hotpads.com/halcyon-house-costa-mesa-ca-92626-249h8zg/pad", "city": "Costa Mesa", "address": "585 Anton Blvd, Costa Mesa, CA 92626"}
    sc.CFG.clear(); sc.CFG.update({"mode": "lease"})
    assert sc.ptype(l) is None
    assert sc.ptype({"title": "Charming house, 2 bed", "home_type_raw": "house", "address": "1 A St, X, CA"}) == "house"

def test_text_log_names_only():
    d = tempfile.mkdtemp(); os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs")
    C = copy.deepcopy(C0); C["shadow"] = True
    C["recipients"] = [{"name": "Jordan", "channel": "imessage", "phone_last4": "1234"}]
    yaml.safe_dump(C, open(f"{d}/CRITERIA.yaml", "w"))
    al = [{"reason": "new", "was": None, "l": {"id": "email:addr:5-a", "source": "Zillow", "url": "https://www.zillow.com/homedetails/5/5_zpid/",
           "address": "5 A St, Los Angeles, CA 90001", "price": 3000, "beds": 2, "baths": 1, "zip": "90001", "pets": "unknown", "flags": [],
           "available": None, "garage": "unknown", "layout": "unknown", "match": True, "eligible": True}}]
    json.dump(al, open(f"{d}/a.json", "w"))
    json.dump({"Jordan": {"first_alert_note_sent": "x"}}, open(f"{d}/out/members.json", "w"))
    for f in ("notify.py", "scout.py", "style.py", "features.py"): shutil.copy(os.path.join(HERE, "src", f), d)
    env = {k: v for k, v in os.environ.items() if k != "PHOTON_API_KEY"}
    p = subprocess.run([sys.executable, "notify.py", "alerts", "a.json", "--send"], cwd=d, capture_output=True, text=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr[-800:]
    L = [json.loads(x) for x in open(f"{d}/out/text_log.jsonl")]
    a = next(x for x in L if x["ids"])
    assert a["to"] == "Jordan" and a["ids"] == ["email:addr:5-a"] and a["addresses"] == ["5 A St"] and "5 A St" in a["text"] and a["ts"]
    assert "1234" not in open(f"{d}/out/text_log.jsonl").read()
    assert json.load(open(f"{d}/out/texted.json"))[0]["id"] == "email:addr:5-a"

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} v1.2.10 tests passed")
