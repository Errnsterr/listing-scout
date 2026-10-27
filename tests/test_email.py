"""Email alert flow (approved 2026-10-26). Fixtures in tests/fixtures/email_tracked are SYNTHETIC (made-up listings and
tracker tokens, shaped like real Zillow / Redfin / HotPads alerts). Runs on temp copies; never touches live state, never sends."""
import os, re, sys, json, copy, shutil, subprocess, tempfile, time, importlib.util
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import yaml, scout as sc
FX = "tests/fixtures/email_tracked"
CRIT = "CRITERIA.yaml" if os.path.exists("CRITERIA.yaml") else "CRITERIA.example.yaml"
C = yaml.safe_load(open(CRIT))
by_file = lambda: {f: sc.parse_email_file(os.path.join(FX, f)) for f in sorted(os.listdir(FX))}

def test_tracked_links_read():
    P = by_file()
    assert len(P["zillow_tracked.html"]) == 2 and len(P["redfin_tracked.html"]) == 2 and len(P["hotpads_tracked.html"]) == 1
    assert P["welcome_no_listings.html"] == []
def test_stable_ids():
    P = by_file()
    assert [l["id"] for l in P["zillow_tracked.html"]] == ["email:Zillow:90000001", "email:Zillow:90000002"]   # zpid from img alt / encoded URL
    assert [l["id"] for l in P["redfin_tracked.html"]] == ["email:Redfin:70000001", "email:addr:100-example-b106"]
    assert P["hotpads_tracked.html"][0]["id"] == "email:addr:1800-sample"
    assert sc.parse_email_file(os.path.join(FX, "zillow_tracked.html"))[0]["id"] == P["zillow_tracked.html"][0]["id"]   # same every run
def test_fields_never_invented():
    P = by_file(); z = P["zillow_tracked.html"][0]
    assert (z["price"], z["beds"], z["baths"], z["address"]) == (3600, 2, 1, "100 Example St #B106, Los Angeles, CA 90002")
    assert z["sqft"] is None and z["pets_raw"] is None and z["available"] is None
    d = tempfile.mkdtemp(); open(f"{d}/a.html", "w").write('<!-- SYNTHETIC --><div><a href="https://click.mail.zillow.com/f/a/x~~/1">$3,100/mo</a> 2 bds</div>')
    l = sc.parse_email_file(f"{d}/a.html")[0]; assert l["price"] == 3100 and l["beds"] == 2 and l["baths"] is None and l["address"] is None
def test_price_cut_card():
    a = by_file()["zillow_tracked.html"][1]; assert a["price"] == 4200 and a["email_was_price"] == 4400
def test_no_price_only_cards():
    assert all(l["price"] != 3000 for l in by_file()["zillow_tracked.html"])   # 'Prices from $3,000' footer is not a home

def run_scout(files, state=None):
    d = tempfile.mkdtemp(); [shutil.copy(os.path.join(HERE, "src", f) if str(f).endswith(".py") else f, d) for f in ("scout.py", "style.py", "features.py")]
    os.makedirs(f"{d}/inbox"); [shutil.copy(os.path.join(FX, f), f"{d}/inbox/{f}") for f in files]
    c = copy.deepcopy(C); c["sources"] = [{"name": "Alerts", "type": "email", "dir": "./inbox"}]
    c["area"] = {**c["area"], "zips": ["90001", "90002", "90003"], "cities": ["Los Angeles", "Shelbyville"]}   # the fixtures' (synthetic) area
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    if state: json.dump(state, open(f"{d}/state.json", "w"))
    p = subprocess.run([sys.executable, "scout.py", "--json"], cwd=d, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(p.stdout or "[]"), json.load(open(f"{d}/state.json")), d
def test_duplicates_one_text():
    out, st, d = run_scout(["zillow_tracked.html", "redfin_tracked.html", "hotpads_tracked.html"])
    pac = [x for x in out if "Example St" in (x["l"].get("address") or "")]
    assert len(pac) == 1, [x["l"]["id"] for x in out]    # same home on Zillow and Redfin: one alert
    out2, _, _ = run_scout(["zillow_tracked.html", "redfin_tracked.html", "hotpads_tracked.html"], st)
    assert out2 == []                                   # same emails again next run: nothing new
def test_price_drop_across_emails():
    _, st, _ = run_scout(["zillow_tracked.html"])
    st["listings"]["email:Zillow:90000001"]["price"] = 3800   # pretend an earlier email had it at $3,800
    out, _, _ = run_scout(["zillow_tracked.html"], st)
    r = [x for x in out if x["l"]["id"] == "email:Zillow:90000001"]; assert r and r[0]["reason"] == "price_drop" and r[0]["was"] == 3800
def test_report_and_zero():
    _, _, d = run_scout(["hotpads_tracked.html", "welcome_no_listings.html"])
    rep = json.load(open(f"{d}/out/email_parse.json"))
    assert rep["welcome_no_listings.html"]["count"] == 0 and rep["hotpads_tracked.html"]["count"] == 1
    assert os.path.exists(f"{d}/inbox/welcome_no_listings.html")   # kept for review

# ---------- notify: owner-only watch + per-person sends ----------
def notify_box():
    d = tempfile.mkdtemp(); [shutil.copy(os.path.join(HERE, "src", f) if str(f).endswith(".py") else f, d) for f in ("notify.py", "scout.py", "style.py", "features.py")]
    os.makedirs(f"{d}/out"); os.makedirs(f"{d}/logs"); c = copy.deepcopy(C)
    c["recipients"] = [{"name": "Alex", "role": "owner"}, {"name": "Sarah", "role": "co_decider"}]
    c["alert_inbox"] = "alerts@example.com"; c["paused"] = False; c["daily_cap"] = 0
    c["quiet_hours"] = {"start": 0, "end": 0} if isinstance(C.get("quiet_hours"), dict) else C.get("quiet_hours")
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w")); json.dump({}, open(f"{d}/out/members.json", "w"))
    os.environ["SCOUT_CRITERIA"] = f"{d}/CRITERIA.yaml"
    spec = importlib.util.spec_from_file_location(f"nt{time.time_ns()}", f"{d}/notify.py"); n = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(n); sent = []
    n.recipients = lambda: [{"name": "Alex", "role": "owner", "phone": "+10000000001", "line_last4": "0000"},
                            {"name": "Sarah", "role": "co_decider", "phone": "+10000000002", "line_last4": "0000"}]
    n.features.in_quiet = lambda C_: False
    n.member = lambda r: {"first_alert_note_sent": "test"}   # one-time note: covered in test_headsups.py
    return d, n, sent
def call(n, *args): sys.argv = ["notify.py", *args]; n.main()
def test_zero_alarm_owner_only_once():
    d, n, sent = notify_box(); n.send = lambda r, t, really, card=None: sent.append((r["name"], t)) or True
    json.dump({"x.html": {"count": 0, "portal": "HotPads", "mtime": time.time()}}, open(f"{d}/out/email_parse.json", "w"))
    open(f"{d}/out/routine_heartbeat.txt", "w").write("ok")
    call(n, "emailwatch", "--send"); call(n, "emailwatch", "--send")
    assert [s[0] for s in sent] == ["Alex"] and "HotPads email" in sent[0][1]
def test_heartbeat_stale_and_site_quiet():
    d, n, sent = notify_box(); n.send = lambda r, t, really, card=None: sent.append((r["name"], t)) or True
    hb = f"{d}/out/routine_heartbeat.txt"; open(hb, "w").write("ok"); old = time.time() - 3 * 86400; os.utime(hb, (old, old))
    json.dump({"z.html": {"count": 2, "portal": "Zillow", "mtime": old}, "r.html": {"count": 0, "portal": "Redfin", "mtime": old}},
              open(f"{d}/out/email_parse.json", "w"))
    json.dump({"zero_told": ["r.html"]}, open(f"{d}/logs/email_watch.json", "w"))
    call(n, "emailwatch", "--send"); call(n, "emailwatch", "--send")
    txt = [t for _, t in sent]; assert all(w == "Alex" for w, _ in sent) and len(sent) == 2, sent
    assert any("stopped syncing" in t for t in txt) and any("No Zillow emails" in t for t in txt)
    assert not any("Redfin" in t for t in txt)   # Redfin never sent a real alert yet: no 48h note
def alert(i, price=3500): return {"reason": "new", "was": None, "market": None, "l": {**json.load(open(SAMPLE))[0]["l"], "id": f"t:{i}", "price": price}}
SAMPLE = "tests/sample_alerts.json" if os.path.exists("tests/sample_alerts.json") else "tests/fixtures/sample_alerts.test.json"
def test_first_find_now_then_bundle_then_retry_one():
    d, n, sent = notify_box(); fail = {"Sarah"}
    n.send = lambda r, t, really, card=None: (sent.append(r["name"]) or True) if r["name"] not in fail else (sent.append("x" + r["name"]) or False)
    n.record_numbered = lambda q: None
    f = f"{d}/out/a.json"; json.dump([alert(1)], open(f, "w")); call(n, "alerts", f, "--send")
    assert sent == ["Alex", "xSarah"]                         # first find goes out at once; Sarah's send failed
    fail.clear(); json.dump([], open(f, "w")); call(n, "alerts", f, "--send")
    assert sent[2:] == ["Sarah"]                              # retry only Sarah, right away
    json.dump([alert(2)], open(f, "w")); call(n, "alerts", f, "--send")
    assert sent[3:] == []                                     # within the cooldown: held for the bundle
    ob = json.load(open(f"{d}/outbox.json")); assert len(ob["queue"]) == 1
    ob["last_sent"] = 0; json.dump(ob, open(f"{d}/outbox.json", "w")); json.dump([], open(f, "w")); call(n, "alerts", f, "--send")
    assert sent[3:] == ["Alex", "Sarah"]

# ---------- real Zillow text render (live: real, personal details removed; template: synthetic values, same layout) ----------
REAL = "tests/fixtures/email_real/zillow_rental_instant.txt"
EXP = ({"id": "email:Zillow:25470327", "price": 4650, "beds": 3, "baths": 2, "sqft": 1560, "city": "Los Angeles"}
       if "25470327" in open(REAL).read() else
       {"id": "email:Zillow:90000555", "price": 3950, "beds": 2, "baths": 1, "sqft": 980, "city": "Sample City"})
def test_real_zillow_text_render():
    L = sc.parse_email_file(REAL); assert len(L) == 1, L
    l = L[0]
    for k, v in EXP.items(): assert l[k] == v, (k, l[k])
    assert l["address"] is None and l["url"] == f"https://www.zillow.com/homedetails/{EXP['id'].split(':')[-1]}_zpid/"
    assert "rtoken" not in (l["url"] or "") and l["pets_raw"] is None
def test_real_no_zpid_stable_id_and_link():
    d = tempfile.mkdtemp(); b = open(REAL).read(); zp = EXP["id"].split(":")[-1]
    b = b.replace(f"zpid_target%2F{zp}_zpid", "x").replace(f"{zp}_zpid", "x").replace(zp, "0")
    open(f"{d}/zillow-1.txt", "w").write(b)
    a, b2 = sc.parse_email_file(f"{d}/zillow-1.txt"), sc.parse_email_file(f"{d}/zillow-1.txt")
    assert len(a) == 1 and a[0]["id"] == b2[0]["id"] and re.fullmatch(r"email:Zillow:m\w+-\d+-\d+-\d+", a[0]["id"]), a[0]["id"]
    u = a[0]["url"]   # never a tracker: the plain public page if the tracker carries it, else no link
    assert u is None or (u.startswith("https://www.zillow.com/") and "?" not in u and "click." not in u), u
def test_undisclosed_address_render():
    import style
    l = sc.classify(sc.parse_email_file(REAL)[0], {**C, "area": {**C["area"], "cities": [EXP["city"]], "zips": ["00000"]}})
    assert l["in_area"] and l["eligible"]
    t = sc.render([{"reason": "new", "was": None, "market": None, "l": l}], C)
    assert f"{EXP['city']}\nAddress not shown\nhttps://www.zillow.com/homedetails/" in t and not style.check(t), t
def test_wrapper_tags_and_header_ignored():
    d = tempfile.mkdtemp(); b = open(REAL).read()
    open(f"{d}/w.txt", "w").write("<cursor_untrusted_data_x source=\"r\">\n" + b + "\n</cursor_untrusted_data_x>")
    assert [l["id"] for l in sc.parse_email_file(f"{d}/w.txt")] == [EXP["id"]]

if __name__ == "__main__":
    T = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in T: t()
    print(f"{len(T)} email tests passed")
