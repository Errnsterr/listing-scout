"""v1.2.7: card-own IDs/links (Zillow text emails), one alert per place, 'Another unit at', ZIP backfill, link fix."""
import os, sys, json, tempfile
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, style, yaml
C = yaml.safe_load(open("CRITERIA.example.yaml")); sc.CFG.update(C)

Z = "https://click.example.com/f/a/x?target=https%3A%2F%2Fwww.zillow.com%2F"
def card(link, price, bd, ba, addr):
    return f"({Z}{link})\n\n{price}\n\n{bd} bd\n|\n{ba} ba\n|\n850 sqft\n\n{addr}\n\n({Z}{link})\n\n● For rent\n\nNew\n\n[image]\n\n"
BODY = ("Subject: 3 Rental Results\n<!-- from: instant-updates@mail.zillow.com | x -->\nWe found 3 rentals.\n\n"
        + card("homedetails%2F11111111_zpid%2F", "$3,400/mo", 2, 1, "1 Elm Pretend St, Exampleville, CA")
        + card("apartments%2Fexampleville-ca%2F994-test-dr%2F9Abc1x%2F", "$3,995/mo", 3, 2, "994 Test Dr #6, Exampleville, CA")
        + card("homedetails%2F22222222_zpid%2F", "$6,100/mo", 3, 2, "404 Sample Way, Exampleville, CA")
        + "Unsubscribe\n")

def _parse():
    f = os.path.join(tempfile.mkdtemp(), "zillow-9999.txt"); open(f, "w").write(BODY)
    return sc.parse_email_file(f)

def test_card_own_id_and_link():
    L = {l["address"].split(",")[0]: l for l in _parse()}
    assert len(L) == 3, L.keys()
    mid = L["994 Test Dr #6"]
    assert "22222222" not in mid["id"] and "22222222" not in mid["url"], mid   # never the NEXT card's zpid
    assert mid["url"].endswith("/apartments/exampleville-ca/994-test-dr/9Abc1x/")
    assert L["404 Sample Way"]["id"] == "email:Zillow:22222222" and L["404 Sample Way"]["price"] == 6100
    assert L["1 Elm Pretend St"]["id"] == "email:Zillow:11111111"

def test_building_name_and_keys():
    r = {"id": "email:Redfin:m1", "address": None, "url": "https://www.redfin.com/CA/Town/Example-Villas-at-the-Park/apartment/1"}
    z = {"id": "email:addr:400", "address": "400 Example Cir #439-203, Town, CA", "url": "https://www.zillow.com/apartments/town-ca/example-villas-at-the-park/9Xyz1a/"}
    assert sc.building_name(r) == sc.building_name(z) == "Example Villas at the Park"
    assert set(sc.bkeys(r)) & set(sc.bkeys(z))
    T = [{"id": r["id"], "bkeys": sc.bkeys(r), "name": "Example Villas at the Park"}]
    assert sc.another_unit(z, T) == "Example Villas at the Park"
    assert sc.another_unit(r, T) is None                      # its own earlier text is not 'another unit'
    s = {"id": "email:addr:994-6", "address": "994 Test Dr #6, Town, CA", "url": None}
    T2 = [{"id": "x", "bkeys": sc.bkeys({"address": "994 Test Dr #2, Town, CA"}), "name": None}]
    assert sc.another_unit(s, T2) == "994 Test Dr"
    assert all(len(x) <= style.MAX for x in sc.another_lines("Example Villas at the Park"))

def test_single_alert_with_another_unit():
    l = dict(_parse()[1], eligible=True, match=True, flags=[], pets="unknown")
    l = sc.classify(l, C); l["flags"] = []
    t = sc.render_parts([{"l": l, "reason": "new", "was": None, "another_at": "994 Test Dr"}], C)
    assert len(t) == 1 and "Another unit at 994 Test Dr" in t[0] and "New place that fits" in t[0]
    assert "today" not in t[0].split("\n")[0]
    for ln in t[0].split("\n"):
        assert len(ln) <= style.MAX or ln.startswith("http"), ln

def test_zip_backfill():
    S = {"a": {"addr": "100|samplegrove|", "loc": {"zip": "90001", "city": "town"}}}
    sc.ZIPIDX = sc.build_zipidx(S)
    try:
        assert sc.zip_backfill({"address": "100 Samplegrove #2H-1149, Town, CA"}) == "90001"
        assert sc.zip_backfill({"address": "5 Other St, Town, CA"}) is None
        S["b"] = {"addr": "100|samplegrove|9", "loc": {"zip": "90002", "city": "town"}}; sc.ZIPIDX = sc.build_zipidx(S)
        assert sc.zip_backfill({"address": "100 Samplegrove #2H-1149, Town, CA"}) is None   # two ZIPs: never guessed
    finally:
        sc.ZIPIDX = {}

def test_link_fix_style():
    m = style.link_fix("994 Test Dr #6", "https://www.zillow.com/apartments/x/994-test-dr/9Abc1x/")
    assert m.split("\n\n")[:2] == ["Fix for 994 Test Dr #6", "The link I sent was wrong."]
    assert "Here is the right one:\nhttps://" in m
    for ln in m.split("\n"): assert len(ln) <= style.MAX or ln.startswith("http")

if __name__ == "__main__":
    n = 0
    for k, v in list(globals().items()):
        if k.startswith("test_"): v(); n += 1
    print(f"ok {n} tests")
