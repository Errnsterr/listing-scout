"""Missing facts never drop a place; ranges / 'from' prices fit if any unit could; only stated facts are shown."""
import os, sys, copy, yaml
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc
C = yaml.safe_load(open("tests/fixtures/CRITERIA.test.yaml")) if os.path.exists("tests/fixtures/CRITERIA.test.yaml") else yaml.safe_load(open("CRITERIA.example.yaml"))
sc.CFG.update(C)
Z = (C["area"].get("zips") or ["90001"])[0]
CAP = (C.get("match") or {}).get("price_max") or C["price_tiers"]["stretch_max"]
BMIN = C["beds_min"]

def L(**k):
    b = dict(id="t:1", source="HotPads", url="https://hotpads.com/x/pad", title="", text="", address=f"1 Example St, Town, CA {Z}",
             price=None, beds=None, baths=None, pets_raw=None, photo_alt=None)
    b.update(k); return sc.classify(b, C)

def test_unknowns_kept():
    l = L(); assert l["eligible"] and l["match"]
    l = L(price=CAP - 1); assert l["match"]                      # no beds stated: kept

def test_stated_fail_drops():
    assert not L(beds=BMIN - 1)["match"]
    assert not L(price=CAP + 1)["match"]

def test_bed_range_and_beds_max():
    assert L(beds=None, beds_range=[BMIN - 1, BMIN])["match"]
    assert L(beds=None, beds_max=BMIN + 1, beds_range=[0, BMIN + 1])["match"]
    assert not L(beds=None, beds_range=[0, BMIN - 1])["match"]

def test_from_price():
    l = L(price=CAP - 100, price_from=True, beds_range=[1, 2])
    assert l["match"]
    lines = sc.summary_block({"l": l, "reason": "new", "was": None}, C)
    assert any(x.startswith("From $") for x in lines) and not any("range" in x.lower() for x in lines)
    assert sc.fact_lines(l, C)[0].startswith("From $")
    assert not L(price=CAP + 100, price_from=True)["match"]         # even the lowest unit is over

def test_hotpads_range_card():
    body = "\n".join(["from $1,797+/mo", "", "1 to 3 beds", "", "Example Terrace", "", "100 Example St", "", f"Town, CA {Z}", "",
                      "(https://hotpads.com/example-terrace-town-ca-x1/pad?nid=1)Contact (https://hotpads.com/x) View listing (https://hotpads.com/x)"])
    l = sc._parse_hotpads_text(body, "t.txt")[0]
    assert l["beds"] is None and l["beds_range"] == [1, 3] and l["price_from"] and l["price"] == 1797
    t = sc.render([{"l": sc.classify(l, C), "reason": "new", "was": None}], C)
    import style; assert not style.check(t), style.check(t)
    assert "From $1,797/mo" in t and "1-3 bed" in t

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} matching tests passed")
