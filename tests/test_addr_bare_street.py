"""v1.2.12: '125 Baker St' and '125 E Baker St' are one home even when a card gives the street alone (ZIP/city on the listing)."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc

def L(i, a, z=None, city=None, price=4000): return {"id": i, "address": a, "zip": z, "city": city, "price": price}

def rec(l): return {"addr": sc.addr_key(l["address"]), "loc": sc.loc_of(l), "price": l["price"], "gone_since": None}

def test_bare_street_dedupes():
    a = L("email:addr:125-baker", "125 Baker St", "92627")
    b = L("email:addr:125-e-baker", "125 E Baker St, Costa Mesa, CA 92627")
    assert sc.addr_key(a["address"]) == sc.addr_key(b["address"]) == "125|baker|"
    assert sc.cross_source(b, {a["id"]: rec(a)}, sc.addr_key(b["address"])) == ("skip", a["id"])
    assert sc.cross_source(a, {b["id"]: rec(b)}, sc.addr_key(a["address"])) == ("skip", b["id"])

def test_bare_street_never_guesses():
    a = L("email:addr:125-baker", "125 Baker St")                       # no ZIP, no city anywhere
    b = L("email:addr:125-e-baker", "125 E Baker St, Costa Mesa, CA 92627")
    assert sc.cross_source(b, {a["id"]: rec(a)}, sc.addr_key(b["address"])) is None
    c = L("email:addr:125-baker-x", "125 Baker St", "92660")           # other ZIP
    assert sc.cross_source(b, {c["id"]: rec(c)}, sc.addr_key(b["address"])) is None
    d = L("email:addr:125-w-baker", "125 W Baker St", "92627")         # W vs E: different homes
    assert sc.cross_source(b, {d["id"]: rec(d)}, sc.addr_key(b["address"])) is None

def test_lower_price_still_alerts():
    a = L("email:addr:125-baker", "125 Baker St", "92627", price=4200)
    b = L("email:addr:125-e-baker", "125 E Baker St, Costa Mesa, CA 92627", price=3900)
    assert sc.cross_source(b, {a["id"]: rec(a)}, sc.addr_key(b["address"])) == ("lower", a["id"], 4200)

if __name__ == "__main__":
    for f in (test_bare_street_dedupes, test_bare_street_never_guesses, test_lower_price_still_alerts): f()
    print("ok 3 bare-street tests")
