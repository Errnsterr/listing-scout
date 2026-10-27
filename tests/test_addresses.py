"""Street addresses: fractions, ranges, no mid-line misreads, building name -> street from the listing URL slug."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc

def a(x):
    m = sc.ADDR.search(x); return m.group() if m else None

def test_addr_regex():
    assert a("417 1/2 Heliotrope Ave, Corona del Mar, CA 92625") == "417 1/2 Heliotrope Ave, Corona del Mar, CA 92625"
    x = "Eight 80 Newport Beach, Newport Beach, CA 92663"; m = sc.ADDR.search(x); assert m is None or sc._name_prefix(x[:m.start()])
    assert not sc._name_prefix("Apartment for rent ")
    assert a("301-307 Avocado St #1X1B, Costa Mesa, CA 92627").startswith("301-307 Avocado")
    assert a("260 Cagney Ln #209, Newport Beach, CA 92663").startswith("260 Cagney Ln #209")

def test_hp_street():
    for s in ("1800-1838 Westcliff Dr N", "417 1/2 Heliotrope Ave", "218.5 Opal Ave #1", "12B Main St"): assert sc.HP_STREET.match(s), s
    assert not sc.HP_STREET.match("Royan Ln")

def test_slug():
    assert sc.slug_street("https://www.redfin.com/CA/Newport-Beach/1544-Placentia-Ave-92663/home/4579991") == "1544 Placentia Ave"
    assert sc.slug_street("https://www.redfin.com/CA/Newport-Beach/260-Cagney-Ln-92663/unit-209/home/5263802") == "260 Cagney Ln #209"
    assert sc.slug_street("https://www.redfin.com/CA/Corona-del-Mar/417-1-2-Heliotrope-Ave-92625/home/1") == "417 1/2 Heliotrope Ave"
    assert sc.slug_street("https://www.redfin.com/CA/Newport-Beach/Eight-80-Newport-Beach/apartment/177359471") is None
    assert sc.slug_street("https://www.zillow.com/homedetails/1-A-St-Costa-Mesa-CA-92627/12345678_zpid/", "Costa Mesa") == "1 A St"
    assert sc.slug_street("https://hotpads.com/x/pad") is None and sc.slug_street(None) is None

def test_building_name_uses_slug():
    l = {"id": "email:Redfin:m1-3150-2-900", "address": "Newport Seaside, Newport Beach, CA 92663",
         "url": "https://www.redfin.com/CA/Newport-Beach/1544-Placentia-Ave-92663/home/4579991"}
    o = sc._street_from_url(l)
    assert o["address"] == "1544 Placentia Ave, Newport Beach, CA 92663" and o["building"] == "Newport Seaside"
    assert o["id"] == "email:addr:1544-placentia"
    assert sc.street(o) == "1544 Placentia Ave"

def test_no_slug_keeps_name():
    l = {"id": "x", "address": "Eight 80 Newport Beach, Newport Beach, CA 92663",
         "url": "https://www.redfin.com/CA/Newport-Beach/Eight-80-Newport-Beach/apartment/177359471"}
    assert sc._street_from_url(l)["address"] == l["address"]
    l2 = {"id": "x", "address": "Some Villas, Costa Mesa, CA 92626", "url": None}
    assert sc._street_from_url(l2) == l2
    l3 = {"id": "x", "address": "12 Main St, Costa Mesa, CA 92626", "url": "https://www.redfin.com/CA/Costa-Mesa/99-Other-St-92626/home/1"}
    assert sc._street_from_url(l3) == l3                                        # a real street from the email always wins

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} address tests passed")
