"""Consistency pass (synthetic data): /mo on every roundup entry, same entry shape in one text, baths shown or
'not listed yet' in single alerts, the user's own city spelling, Redfin building names and price ranges."""
import os, sys, copy
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, style
C = {"mode": "lease", "area": {"cities": ["Vista del Sol", "Springfield"], "zips": ["90001"]}, "beds_min": 2,
     "price_tiers": {"target_max": 4000, "stretch_max": 5000}, "baths": {"ok": 1, "ideal": 2}, "pets": {}, "match": {}, "show_source": False}
sc.CFG.clear(); sc.CFG.update(C)
def L(**k):
    l = dict(id="x", source="Zillow", url="https://www.zillow.com/x/", address="1 Example St, Springfield, IL 90001", price=3995,
             beds=2, baths=None, zip="90001", pets="not listed", flags=[], available=None, garage="not listed", layout="not listed")
    l.update(k); return {"reason": "new", "l": l}

def test_every_entry_has_mo_and_same_shape():
    A = [L(id="a", price=2995), L(id="b", price=3995, baths=2, address="2 Example St, VISTA DEL SOL, CA 90001")]
    t = sc.render(A, C)
    assert "$2,995/mo" in t and "$3,995/mo" in t, t
    assert all(len(x) <= style.MAX for x in t.split("\n")), t
    shapes = [len(sc.fact_lines(a["l"], C, sc.needs_split(A, C))) for a in A]
    assert len(set(shapes)) == 1, shapes                     # one line shape for every entry in the text

def test_city_in_users_spelling():
    a = L(address="2 Example St, VISTA DEL SOL, CA 90001")
    assert sc.area_name(a["l"]) == "Vista del Sol"

def test_single_alert_baths():
    t = sc.render([L(baths=None)], C); assert "Baths: not listed yet" in t, t
    t = sc.render([L(baths=1.5)], C); assert "1.5 bath" in t and "Baths:" not in t, t

def test_redfin_building_and_range():
    body = ("message_id 1\n\n$2,795-$4,070/mo\n\n1-2 Beds &middot; 1-2 Baths &middot; 617-1,258 Sq. Ft.\n\n"
            "Example Commons, Springfield, IL 90001 (https://redmail3.redfin.com/a/click?_t=a)\n\n"
            "$2,475/mo\n\n1 Bed &middot; 1 Bath &middot; 700 Sq. Ft.\n\nExample Villas, Springfield, IL 90001 (https://redmail3.redfin.com/a/click?_t=b)\n")
    X = sc._parse_text_cards(body, "Redfin", "f")
    assert len(X) == 2, X
    r, one = X
    assert r["price"] == 2795 and r["price_from"] and "-x-" in r["id"] and r["price_range"] == [2795, 4070]   # v1.2.10: lowest unit is the price; id unchanged and r["beds"] is None and r["beds_range"] == [1, 2]
    assert r["address"].startswith("Example Commons") and one["address"].startswith("Example Villas") and one["price"] == 2475
    sc.classify(r, C); sc.classify(one, C)
    assert r["eligible"] and r["match"] and not one["eligible"]   # a 2-bed unit may be in the range; the 1-bed is not
    t = sc.render([{"reason": "new", "l": r}], C)
    assert "$2,795-$4,070/mo" in t and "Rent: not listed yet" not in t and "1-2 bed" in t, t
    hi = copy.deepcopy(r); hi["price_range"] = [5100, 6000]; hi["price"] = 5100; sc.classify(hi, C); assert not hi["match"]

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} consistency tests passed")
