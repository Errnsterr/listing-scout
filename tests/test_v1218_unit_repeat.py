"""v1.2.18: a copy with no unit vs stored copies with units (the 1142 Buckingham repeat). No network, no sends."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); TOP = os.path.dirname(HERE)
SRC = os.path.join(TOP, "src") if os.path.exists(os.path.join(TOP, "src", "scout.py")) else TOP; sys.path.insert(0, SRC)
import scout

def rec(addr, price, beds=2.0, zip_=None, city="town", bldg=None):
    return {"first_seen": "2026-10-30", "price_history": [], "price": price, "gone_since": None, "eligible": True,
            "addr": addr, "loc": {"dirs": "", "zip": zip_, "city": city}, "bldg": bldg, "beds": beds}
def L(id_, address, price, beds=2.0):
    return dict(id=id_, address=address, zip="90001", city="Town", state="CA", price=price, beds=beds, source="Redfin")
def cs(l, S): return scout.cross_source(l, S, scout.addr_key(l["address"]))

def test_buckingham_repeat_reproduced():
    # stored as a named building unit, no ZIP on the record (exactly the live miss)
    S = {"email:addr:100-sample-1121e": rec("100|sample|1121e", 3580.0, bldg="Sample Glen")}
    assert cs(L("email:addr:100-sample", "100 Sample Dr, Town, CA 90001", 3580.0), S) == ("skip", "email:addr:100-sample-1121e")

def test_lower_price_is_price_drop():
    S = {"a": rec("100|sample|1121e", 3580.0)}
    assert cs(L("b", "100 Sample Dr, Town, CA 90001", 3400.0), S) == ("lower", "a", 3580.0)

def test_several_units_building_quiet():
    S = {"a": rec("100|sample|1", 3000.0, zip_="90001"), "b": rec("100|sample|2", 3900.0, zip_="90001")}
    r = cs(L("c", "100 Sample Dr, Town, CA 90001", 2500.0), S)
    assert r and r[0] == "skip", r   # never a new text, even at a lower price

def test_two_units_stay_different():
    S = {"a": rec("100|sample|1", 3000.0, zip_="90001")}
    assert cs(L("b", "100 Sample Dr #2, Town, CA 90001", 3000.0), S) is None

def test_unit_not_blocked_by_building_range():
    S = {"a": rec("100|sample|", 2500.0, beds=None, zip_="90001")}   # held building 'From $2,500'
    assert cs(L("b", "100 Sample Dr #7, Town, CA 90001", 3100.0), S) is None

def test_other_city_no_match():
    S = {"a": rec("100|sample|1121e", 3580.0, city="elsewhere")}
    assert cs(L("b", "100 Sample Dr, Town, CA 90001", 3580.0), S) is None

def test_gone_record_not_matched():
    r = rec("100|sample|1121e", 3580.0); r["gone_since"] = 1.0
    assert cs(L("b", "100 Sample Dr, Town, CA 90001", 3580.0), {"a": r}) is None

def test_unit_vs_stored_bare_no_zip():   # the 108 Olive kind: bare home first, same home with #A later
    S = {"a": rec("100|sample|", 4250.0)}
    r = cs(L("b", "100 Sample St #A, Town, CA 90001", 4250.0), S)
    assert r == ("skip", "a"), r

def test_building_range_after_unit_quiet():   # the 400 Enclave kind: unit texted, then 'From $2,810' building card
    S = {"a": rec("100|sample|422-301", 3590.0)}
    l = dict(L("b", "100 Sample Cir, Town, CA 90001", 2810.0, beds=None), price_from=True, beds_range=[1, 2])
    assert cs(l, S) == ("skip", "a")

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
