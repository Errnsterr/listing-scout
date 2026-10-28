"""v1.2.8 buying: a lot only when it's the home's own, a type only when stated, HOA only when stated."""
import os, sys, copy
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, yaml
C = yaml.safe_load(open("CRITERIA.example.yaml")); C["mode"] = "buy"
C["price_tiers"] = {"target_max": None, "stretch_max": None}; C.setdefault("buy", {}); C["buy"]["price_max"] = None; C["buy"]["target_max"] = None
sc.CFG.clear(); sc.CFG.update(C)

def L(addr, facts, title=""):
    l = dict(sc.buy_facts(facts), address=addr, title=(title or facts) + " " + addr, source="Redfin", url=None, ptype_raw=None)
    return l

def test_shared_community_lot_omitted():
    a = L("100 Example Ct, Exampleville, CA 90001", "10.42 acre lot • $635 HOA • 2 garage spots")
    assert a["hoa"] == 635 and a["lot"] == "10.42 acres" and sc.own_lot(a) is None      # HOA community's lot, not the home's
    b = L("310 Sample St #208, Exampleville, CA 90001", "0.86 acre lot • $1,023 HOA")
    assert sc.own_lot(b) is None                                                         # a unit never has its own lot
    c = L("986 Demo Ave, Exampleville, CA 90001", "6,120 sq ft lot • 2 garage spots")
    assert sc.own_lot(c) == "6,120 sq ft lot"
    d = L("12 Elm Pretend St, Exampleville, CA 90001", "0.3 acre lot • $55 HOA")
    assert sc.own_lot(d) == "0.3 acres"                                                  # small lot with a small HOA: its own
    e = L("5 Park Test Rd, Exampleville, CA 90001", "Near 5 acres of parkland")
    assert e["lot"] is None                                                              # not called a lot: not read as one

def test_buy_details_lines():
    a = L("100 Example Ct, Exampleville, CA 90001", "10.42 acre lot • $635 HOA")
    lines = sc.buy_details(a, C)
    assert "HOA $635/mo" in lines and not any(x.startswith("Lot") for x in lines)
    n = L("1 No HOA Way, Exampleville, CA 90001", "3 Beds 2 Baths")
    assert not any("HOA" in x for x in sc.buy_details(n, C))                             # HOA isn't a list fact: no 'not listed yet'
    assert not any("not listed" in x for x in sc.buy_details(n, C) if "HOA" in x)

def test_type_only_when_stated():
    a = L("292 Example St APT C2, Exampleville, CA", "2 bd | 3 ba | 1,377 sqft")
    assert sc.ptype(a) is None                                                           # 'APT' in the address is not a type
    b = L("12 Elm Pretend St, Exampleville, CA", "[image: House Icon] Open: Sat 1-4pm 3 bd | 2 ba")
    assert sc.ptype(b) is None                                                           # icon / open house: not a type
    c = L("12 Elm Pretend St, Exampleville, CA", "Condo for sale 2 bd | 2 ba")
    assert sc.ptype(c) == "condo"
    d = L("12 Elm Pretend St, Exampleville, CA", "Single family residence 3 bd")
    assert sc.ptype(d) == "house"

def test_no_price_limit_tiers():
    assert sc.tier_words(1_500_000, C) is None
    l = sc.classify(dict(L("12 Elm Pretend St, Exampleville, CA 90001", "3 bd"), price=1_500_000, beds=3, baths=2, text="", pets_raw=None), C)
    assert l["tier"] == "TARGET"

if __name__ == "__main__":
    n = 0
    for k, v in list(globals().items()):
        if k.startswith("test_"): v(); n += 1
    print(f"ok {n} tests")
