"""v1.2.12: baths/pets come from the listing page when the card leaves them out; 'not listed yet' only when truly absent."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc, gonecheck as gc

PAGE = '<script type="application/ld+json">{"@type":"Apartment","numberOfBedrooms":3,"numberOfBathroomsTotal":2,"petsAllowed":"Cats and Dogs Allowed"}</script>'

def test_page_facts_reads_jsonld():
    assert gc.page_facts(PAGE) == {"baths": 2.0, "pets_raw": "Cats and Dogs Allowed"}
    assert gc.page_facts('{"petsAllowed":false}') == {"pets_raw": "No pets"}
    assert gc.page_facts("<html>Pet policy</html>") == {}            # nothing stated: nothing filled
    assert gc.page_facts("") == {}

def test_fill_never_overwrites_or_invents():
    pf = {"email:addr:1-a": {"baths": 2.0, "pets_raw": "Cats and Dogs Allowed"}}
    l = sc.fill_page_facts({"id": "email:addr:1-a", "baths": None, "pets_raw": None}, pf)
    assert l["baths"] == 2.0 and l["pets_raw"] == "Cats and Dogs Allowed"
    l = sc.fill_page_facts({"id": "email:addr:1-a", "baths": 1.0, "pets_raw": "Cats only"}, pf)
    assert l["baths"] == 1.0 and l["pets_raw"] == "Cats only"        # the card's own facts win
    l = sc.fill_page_facts({"id": "email:addr:2-b", "baths": None, "pets_raw": None}, pf)
    assert l["baths"] is None and l["pets_raw"] is None              # no page facts: stays unknown -> 'not listed yet'
    l = sc.fill_page_facts({"id": "email:addr:1-a", "baths": None, "baths_range": [1, 2], "pets_raw": None}, pf)
    assert l["baths"] is None                                        # a building range is never collapsed to one unit's number

if __name__ == "__main__":
    test_page_facts_reads_jsonld(); test_fill_never_overwrites_or_invents(); print("ok 2 page-facts tests")
