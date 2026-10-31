"""v1.2.14: Zillow listing numbers aren't units; long address/name lines wrap to 30."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, style
sc.MATCH_LOG = "/tmp/match_test.log"

def test_long_digit_unit_dropped():
    K = sc.addr_key
    assert K("955 W 19th St #3606403, Costa Mesa, CA 92627") == K("955 W 19th St, Costa Mesa, CA 92627")
    assert K("100 Vilaggio #134810, Newport Beach, CA 92660") == "100|vilaggio|"
    assert K("100 Vilaggio #2H-1149, Newport Beach, CA 92660") == "100|vilaggio|2h-1149"
    assert K("125 E Baker St #2104, Costa Mesa, CA 92626") == "125|baker|2104"

def test_street_display_drops_listing_number():
    assert sc.street({"address": "955 W 19th St #3606403, Costa Mesa, CA"}) == "955 W 19th St"
    assert sc.street({"address": "125 E Baker St #2104, Costa Mesa, CA"}) == "125 E Baker St #2104"

def test_ids_unchanged():
    assert sc.addr_id_key("955 W 19th St #3606403, Costa Mesa, CA").endswith("3606403")

def test_long_name_wraps():
    l = {"address": None, "street_only": None, "url": "https://www.redfin.com/x"}
    out = sc.fit_lines("Sandpointe Cove Apartment Homes")
    assert all(len(x) <= style.MAX for x in out) and " ".join(out) == "Sandpointe Cove Apartment Homes"
    assert sc.fit_lines("955 W 19th St") == ["955 W 19th St"]
    assert sc.fit_lines("12. Sandpointe Cove Apartment Homes")[0].startswith("12. ")

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} tests passed")
