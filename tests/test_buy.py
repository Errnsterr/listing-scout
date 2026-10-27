"""Buy mode: synthetic Zillow / Redfin / Realtor.com for-sale emails (made-up addresses). No network, nothing sent."""
import os, sys, json, copy, shutil, subprocess, tempfile, glob
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import yaml, style, features, scout as sc
C = yaml.safe_load(open("tests/fixtures/CRITERIA.buy.test.yaml")); sc.CFG.clear(); sc.CFG.update(C)
ok = lambda m: not style.check(m)
def load():
    L = []
    for f in sorted(glob.glob("tests/fixtures/email_buy/*")): L += [sc.classify(l, C) for l in sc.parse_email_file(f)]
    return L
L = load(); M = sc.merge_dupes(copy.deepcopy(L), C); by = {l["address"].split(",")[0]: l for l in L}
al = lambda l, r="new", was=None: [{"reason": r, "was": was, "market": None, "l": l}]

def test_parse_fields():
    z = by["123 Maple Test Dr"]
    assert (z["price"], z["beds"], z["baths"], z["sqft_buy"], z["year_built"], z["dom"], z["status"]) == (850000, 3, 2, 1600, 1978, 2, "new")
    assert z["lot"] == "5,000 sq ft lot" and z["hoa"] is None                                   # HOA missing stays None
    assert by["45 Oak Sample Ln #2"]["hoa"] == 350 and by["45 Oak Sample Ln #2"]["email_was_price"] == 650000
    assert by["88 Spruce Sample Rd"]["lot"] == "0.25 acres" and by["88 Spruce Sample Rd"]["open_house"] == "Sun 12 PM - 3 PM"
    st = {l["address"].split(",")[0]: l["status"] for l in L}
    assert st["9 Birch Fake Ct"] == "pending" and st["77 Cedar Mock Way"] == "sold" and st["12 Elm Pretend St"] == "coming_soon"
    assert st["300 Pine Demo Ave"] == "back_on_market" and st["5 Willow Test Pl"] == "price_cut"
    assert {l["source"] for l in L} == {"Zillow", "Redfin", "Realtor.com"}
def test_ids_and_dupes():
    assert by["45 Oak Sample Ln #2"]["id"] == "email:Zillow:22222222" and by["300 Pine Demo Ave"]["id"] == "email:Redfin:7777777"
    assert by["88 Spruce Sample Rd"]["id"].startswith("email:addr:")                            # no zpid/Redfin id: address + unit
    assert len(M) == len(L) - 1 and any("Redfin + Zillow" in l["source"] for l in M)            # one home, one text across sites
def test_buy_filters():
    m = {l["address"].split(",")[0]: l["match"] for l in M}
    assert m["123 Maple Test Dr"] and m["88 Spruce Sample Rd"] and m["12 Elm Pretend St"]
    assert not m["45 Oak Sample Ln #2"]                                                         # 2 beds < 3
    assert not m["9 Birch Fake Ct"] and not m["77 Cedar Mock Way"]                              # pending / sold never alert
    c = copy.deepcopy(C); c["buy"]["hoa_max"] = 100
    assert not sc.classify(copy.deepcopy(by["88 Spruce Sample Rd"]), c)["match"]               # HOA $150 > max
    assert sc.classify(copy.deepcopy(by["123 Maple Test Dr"]), c)["match"]                      # HOA unknown: kept
    c["buy"]["home_types"] = ["condo"]; assert not sc.classify(copy.deepcopy(by["123 Maple Test Dr"]), c)["match"]
def test_buy_texts():
    t = sc.render(al(by["123 Maple Test Dr"]), C)
    assert t.startswith("New home that fits") and "/mo" not in t.split("HOA")[0] and "HOA" not in t and ok(t), t
    t = sc.render(al(by["88 Spruce Sample Rd"]), C); assert "HOA $150/mo" in t and "Open house Sun 12 PM - 3 PM" in t and "Lot 0.25 acres" in t and ok(t), t
    t = sc.render(al(by["5 Willow Test Pl"], "price_drop", 749000), C); assert "A price came down" in t and "Now $725,000 (was $749,000)" in t and ok(t), t
    t = sc.render(al(by["300 Pine Demo Ave"], "relist"), C); assert "Back on the market" in t and ok(t), t
    assert "Pets" not in sc.render(al(by["123 Maple Test Dr"]), C)
    for m in (style.off_market("9 Birch Fake Ct", "pending"), style.off_market("77 Cedar Mock Way", "sold"),
              style.evening_bundle_intro(3, "home"), style.owner_welcome("Alex", 120, True, "home"),
              style.member_welcome("Sam", "Alex", sc.reflect(C), "home", "co_decider", True, True)):
        assert ok(m), (m, style.check(m))
    assert "Not an agent or advice." in style.owner_welcome("Alex", 120, False, "home")
    assert "Not an agent or advice." not in style.owner_welcome("Alex", 120, False, "rental")
    assert len(style.BUY_LINE) <= 30
def test_pace():
    q = [{"reason": "new", "l": dict(by["88 Spruce Sample Rd"], match=True)}, {"reason": "new", "l": dict(by["300 Pine Demo Ave"], match=True, price=850000)}]
    now, later = features.pace_split(q, "standouts", C); assert len(now) == 1 and len(later) == 1   # within target: now; stretch: tonight
    assert features.pace_split(q, "instant", C) == (q, []) and features.pace_split(q, "evening", C) == ([], q)
    assert features.parse_change("text me everything right away", C)["value"] == "instant"
    assert features.parse_change("just the evening roundup", C)["value"] == "evening"
def _sandbox(shortlist):
    d = tempfile.mkdtemp(); [shutil.copy(os.path.join(HERE, "src", f) if str(f).endswith(".py") else f, d) for f in ("notify.py", "style.py", "features.py", "scout.py", "replies.py")]
    os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs"); c = copy.deepcopy(C); c["shadow"] = True
    c["recipients"] = [{"name": "Alex", "role": "owner", "phone_last4": "0000"}, {"name": "Sam", "role": "co_decider", "phone_last4": "1111"}]
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w")); json.dump(shortlist, open(f"{d}/out/shortlist.json", "w"))
    env = {k: v for k, v in os.environ.items() if k != "PHOTON_API_KEY"}; env["SCOUT_CRITERIA"] = f"{d}/CRITERIA.yaml"
    return d, lambda *a: subprocess.run([sys.executable, "notify.py", *a], cwd=d, capture_output=True, text=True, env=env)
def test_pending_only_to_shortlisters():
    d, run = _sandbox({"email:Zillow:33333333": {"where": "9 Birch Fake Ct", "price": "$700,000", "likes": ["Sam"]}})
    json.dump([{"id": "email:Zillow:33333333", "also_ids": [], "status": "pending", "where": "9 Birch Fake Ct"},
               {"id": "email:Zillow:44444444", "also_ids": [], "status": "sold", "where": "77 Cedar Mock Way"}], open(f"{d}/out/offmarket.json", "w"))
    o = run("offmarket", "--send"); rows = [json.loads(x) for x in open(f"{d}/out/shadow_texts.jsonl")]
    assert [r["to"] for r in rows] == ["Sam"], (rows, o.stdout, o.stderr)                      # only the person who shortlisted it
    assert "It's now pending." in rows[0]["text"] and rows[0]["style_ok"]
    run("offmarket", "--send"); assert len(open(f"{d}/out/shadow_texts.jsonl").read().splitlines()) == 1   # told once
def test_shadow_logs_not_sends():
    d, run = _sandbox({})
    strip = lambda l: {k: v for k, v in l.items() if k != "text"}
    json.dump([{"reason": "new", "was": None, "market": None, "l": strip(dict(by["88 Spruce Sample Rd"], match=True))},
               {"reason": "new", "was": None, "market": None, "l": strip(dict(by["123 Maple Test Dr"], match=True))}], open(f"{d}/a.json", "w"))
    o = run("alerts", "a.json", "--send"); rows = [json.loads(x) for x in open(f"{d}/out/shadow_texts.jsonl")]
    assert "[SHADOW]" in o.stdout and rows and all(r["style_ok"] for r in rows), (o.stdout, o.stderr)
    note = [r for r in rows if "Quick note on that one." in r["text"]]; rows = [r for r in rows if r not in note]
    assert sorted(r["to"] for r in note) == ["Alex", "Sam"]   # one-time heads-up: logged once each in shadow, never sent
    assert all("88 Spruce" in r["text"] and "123 Maple" not in r["text"] for r in rows)       # standout now, the other tonight
    ob = json.load(open(f"{d}/outbox.json")); assert len(ob["evening"]) == 1
    run("evening", "--now", "--send"); rows = [json.loads(x) for x in open(f"{d}/out/shadow_texts.jsonl")]
    ev = [r for r in rows if "roundup" in r["text"]]; assert ev and "123 Maple" in ev[0]["text"] and all(r["style_ok"] for r in ev)
    open(f"{d}/roundup.txt", "w").write(ev[0]["text"])

if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns: f()
    print(f"{len(fns)} buy tests passed")
