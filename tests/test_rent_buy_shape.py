"""Buy single alerts use the rental single-alert shape exactly (Ern's standard: the rental texts)."""
import os, sys, copy, re
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, style, yaml
R = yaml.safe_load(open("CRITERIA.example.yaml"))
B = yaml.safe_load(open("tests/fixtures/CRITERIA.buy.test.yaml"))

def shape(t):
    """Each block -> its role list: headline / summary (beds, area, price, range) / details (... Via) / where (street, link) / close."""
    out = []
    for b in t.split("\n\n"):
        ls = b.split("\n")
        out.append(["url" if l.startswith("http") else "via" if l.startswith("Via ") else "range" if re.search(r"range$", l) else
                    "price" if l.startswith("$") or l.startswith("From $") else "line" for l in ls])
    return out

def rent():
    sc.CFG.clear(); sc.CFG.update(R)
    l = dict(sc.buy_facts(""), id="t:r", source="Demo PM", url="https://example.com/listing/1", title="1 bed 1 bath apartment",
             address="100 Example St Unit 4, Los Angeles, CA 90001", price=1695, beds=1, baths=1, available="12/1/26", pets_raw=None, text="", city=None, zip=None)
    l = sc.classify(l, R); l["flags"] = []
    return sc.render([{"l": l, "reason": "new", "was": None}], R)

def buy(url="https://www.zillow.com/homedetails/11111111_zpid/"):
    sc.CFG.clear(); sc.CFG.update(B)
    l = dict(sc.buy_facts("Single family $150 HOA 1,600 sq ft 5,000 sq ft lot"), id="t:b", source="Zillow", url=url, title="Single family",
             address="123 Maple Test Dr, Exampleville, CA 90001", price=850000, beds=3, baths=2, pets_raw=None, text="", city=None, zip=None)
    l = sc.classify(l, B); l["flags"] = []
    return sc.render([{"l": l, "reason": "new", "was": None}], B)

def test_same_blocks_same_order():
    r, b = rent(), buy()
    sr, sb = shape(r), shape(b)
    assert len(sr) == len(sb) == 6, (r, b)
    assert sr[0] == sb[0] == ["line"]                                   # headline
    assert sr[1][-2:] == sb[1][-2:] == ["price", "range"] and len(sr[1]) == len(sb[1]) == 4   # beds/type, area, price, range
    assert sr[2][-1] == sb[2][-1] == "via"                              # details end with Via
    assert sr[3] == sb[3] == ["line", "url"]                            # street, then its link
    assert r.split("\n\n")[4:] == b.split("\n\n")[4:] == ["No rush.", "I'll keep watching."]
    assert r.startswith("New place that fits") and b.startswith("New home that fits")
    assert "HOA $150/mo" in b and "Lot 5,000 sq ft" in b and "not listed" not in b

def test_buy_range_from_buy_budget():
    C = copy.deepcopy(B); C["price_tiers"] = {"target_max": None, "stretch_max": None}; C["buy"]["price_max"] = 900000
    assert sc.tier_words(850000, C) == "top of your stretch range" or sc.tier_words(850000, C) == "in your target range"
    C["buy"]["target_max"] = 800000
    assert sc.tier_words(850000, C) == "in your stretch range"

def test_zip_typo_conservative():
    C = copy.deepcopy(R); C["area"]["zips"] = ["92627"]; C["area"]["cities"] = ["Costa Mesa"]
    assert sc.zip_typo("02627", {"address": "292 Example St, Costa Mesa, CA 02627"}, C) == "92627"
    assert sc.zip_typo("02627", {"address": "292 Example St, Boston, MA 02627"}, C) == "02627"     # city disagrees: as written
    assert sc.zip_typo("02628", {"address": "292 Example St, Costa Mesa, CA 02628"}, C) == "02628"  # not a search ZIP
    assert sc.zip_typo("12627", {"address": "x, Costa Mesa, CA 12627"}, C) == "12627"              # only a leading 0

def test_no_link_rule_same_both():
    r = rent().replace("https://example.com/listing/1\n", ""); b = buy(url=None)
    assert shape(b)[3] == ["line"]           # no clean link from any copy: the street alone, as rentals do


def test_hoa_open_house_cross_site():
    sc.CFG.clear(); sc.CFG.update(B)
    z = sc.classify(dict(sc.buy_facts("2 bd 2 ba"), id="email:Zillow:1", source="Zillow", url="https://www.zillow.com/homedetails/1_zpid/", title="",
                         address="310 Sample St APT 208, Exampleville, CA", price=850000, beds=2, baths=2, pets_raw=None, text="", city=None, zip=None), B)
    r = sc.classify(dict(sc.buy_facts("$1,023 HOA Open house: Sat 1-4pm"), id="email:addr:310", source="Redfin", url=None, title="",
                         address="310 Sample St #208, Exampleville, CA 90001", price=850000, beds=2, baths=2, pets_raw=None, text="", city=None, zip=None), B)
    (m,) = sc.merge_dupes([z, r], B)
    assert m["hoa"] == 1023 and m["open_house"] and m["url"].startswith("https://www.zillow.com/")

if __name__ == "__main__":
    n = 0
    for k, v in list(globals().items()):
        if k.startswith("test_"): v(); n += 1
    print(f"ok {n} tests")
