"""HotPads text alerts shaped like the real ones (2026-10-26; places, streets, ZIPs, tokens made up). Regression for the 'Nine new places today' digest:
link off-by-one (each card got the PREVIOUS card's link), /user/searches parsed as a listing, street+city on two lines
read as no address, '$X+/mo' and 'Call for price' cards merged into a neighbour (wrong address)."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc
FX = "tests/fixtures/hotpads_text"
P = lambda i: sc.parse_email_file(os.path.join(FX, f"hotpads_{i}.txt"))
slug = lambda u: u.split("hotpads.com/")[1].split("/")[0]

def test_link_matches_its_own_address():
    for i in ("3021665", "3021702", "3021944"):
        for l in P(i):
            assert l["url"].startswith("https://hotpads.com/") and l["url"].endswith("/pad") and "?" not in l["url"]
            n = (l["address"] or "").split()[0] if l["address"] else None
            if n and n.isdigit() and slug(l["url"])[0].isdigit(): assert slug(l["url"]).startswith(n + "-"), (l["address"], l["url"])

def test_first_card_pairs():
    a = P("3021665")
    assert (a[0]["price"], a[0]["address"], a[0]["city"], a[0]["zip"]) == (3600, "418 Larkspur Pl #C, Shelbyville, CA 90001", "Shelbyville", "90001")
    assert a[0]["url"] == "https://hotpads.com/418-larkspur-pl-shelbyville-ca-90001-l4ku2t/c/pad"
    assert (a[1]["price"], a[1]["address"]) == (2995, "742 E Testwood1 St, Shelbyville, CA 90001")
    assert "fernby-742-e-testwood1" in a[1]["url"]

def test_never_user_searches():
    for i in ("3021665", "3021702", "3021944"):
        assert not any("/user/" in l["url"] for l in P(i))
    assert sc.hotpads_url("https://hotpads.com/user/searches?nid=x") is None

def test_no_misattributed_address():
    b = {l["price"]: l for l in P("3021702")}
    assert b[4000]["address"] == "6820 Testwood9 Rd #A, Los Angeles, CA 90002" and "6820-testwood9-rd" in b[4000]["url"]
    nt = [l for l in P("3021702") if l["price"] is None][0]   # 'Call for price' is its own card, not glued to $4,000
    assert nt["address"].startswith("2238 Testwood10 Ave") and "sampleport-terrace" in nt["url"]
    ei = b[1797]; assert (ei["beds"], ei["beds_max"], ei["beds_range"], ei["price_from"]) == (None, 2, [0, 2], True) and ei["address"].startswith("1562 Testwood7 Ave")

def test_no_street_number_stays_unknown():
    x = [l for l in P("3021702") if l["price"] == 4247][0]
    assert x["address"] is None and x["city"] == "Los Angeles"   # email says only '31st St': never invented

def test_image_prefix_beds():
    c = {l["price"]: l for l in P("3021944")}
    assert c[7500]["beds"] == 2 and c[7500]["address"].startswith("9158 Testwood15 Pl")

def _run(paths):
    import copy, json, shutil, subprocess, tempfile, yaml
    C = yaml.safe_load(open("CRITERIA.yaml" if os.path.exists("CRITERIA.yaml") else "CRITERIA.example.yaml"))
    d = tempfile.mkdtemp(); [shutil.copy(os.path.join(HERE, "src", f), d) for f in ("scout.py", "style.py", "features.py")]
    os.makedirs(f"{d}/inbox"); [shutil.copy(p, f"{d}/inbox/{os.path.basename(p)}") for p in paths]
    c = copy.deepcopy(C); c["sources"] = [{"name": "Alerts", "type": "email", "dir": "./inbox"}]
    c["area"] = {**c["area"], "zips": ["90001", "90002", "90003"], "cities": ["Shelbyville", "Los Angeles", "Springfield"]}
    c["beds_min"] = 1; c["price_tiers"] = {**c["price_tiers"], "target_max": 20000, "stretch_max": 20000}
    yaml.safe_dump(c, open(f"{d}/CRITERIA.yaml", "w"))
    p = subprocess.run([sys.executable, "scout.py", "--json"], cwd=d, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(p.stdout or "[]")

def test_one_queue_cross_source_dedupe():
    """HotPads + Zillow emails in one run -> one alert list (one message), same home once (normalized address)."""
    import tempfile
    z = os.path.join(tempfile.mkdtemp(), "zillow_same_home.html")
    open(z, "w").write('<!-- SYNTHETIC --><div><a href="https://www.zillow.com/homedetails/x/">$3,600/mo</a> 2 bds 1 ba'
                       '<p>418 Larkspur Place Unit C, Shelbyville, CA 90001</p></div>')
    out = _run([os.path.join(FX, "hotpads_3021665.txt"), z])
    hits = [a for a in out if "418" in (a["l"].get("address") or "")]
    assert len(hits) == 1, [a["l"]["id"] for a in hits]
    assert len({a["l"]["id"] for a in out}) == len(out) and len(out) >= 8   # all sources in the same list
    assert not any("/user/" in (a["l"].get("url") or "") for a in out)

def test_same_email_twice_one_alert():
    import tempfile, shutil
    d = tempfile.mkdtemp(); p2 = os.path.join(d, "hotpads_copy.txt"); shutil.copy(os.path.join(FX, "hotpads_3021702.txt"), p2)
    out = _run([os.path.join(FX, "hotpads_3021702.txt"), p2])
    one = _run([os.path.join(FX, "hotpads_3021702.txt")])
    assert len(out) == len({a["l"]["id"] for a in out}) == len(one) > 0

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_") and callable(f): f(); print("ok", k)
