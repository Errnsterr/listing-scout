"""Cross-site address matching: same home across sites, never two units or two streets."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc
K, P = sc.addr_key, lambda a, b: sc.same_place(sc.addr_loc(a), sc.addr_loc(b))

def same(a, b): return K(a) == K(b) and P(a, b)

def test_same_home():
    assert same("125 Baker St, Town, CA 90001", "125 E Baker St, Town, CA 90001")
    assert same("125 East Baker Street, Town, CA 90001", "125 Baker St, Town, CA 90001")
    assert same("10 Main Dr N, Town, CA 90001", "10 North Main Drive, Town, CA 90001")
    assert same("260 Cagney Ln #209, Town, CA 90001", "260 Cagney Lane Unit 209, Town, CA 90001")
    assert same("260 Cagney Ln APT 209, Town, CA 90001", "260  cagney ln. ste 209 , Town, CA 90001")
    assert same("241 Example Street - A, Town, CA 90001", "241 Example St Unit A, Town, CA 90001")
    assert same("218.5 Opal Ave, Town, CA 90001", "218 1/2 Opal Ave, Town, CA 90001")
    assert same("412 Colton St, Town, CA", "412 Colton St, Town, CA 90001")       # one has no ZIP: city decides
    for x in ("Pl", "Ct", "Rd", "Way", "Cir", "Ter", "Pkwy", "Hwy", "Blvd"):
        assert same(f"5 Oak {x}, Town, CA 90001", "5 Oak, Town, CA 90001"), x

def test_never_over_merge():
    assert not same("125 Baker St, Town, CA 90001", "127 Baker St, Town, CA 90001")
    assert not same("260 Cagney Ln #209, Town, CA 90001", "260 Cagney Ln #210, Town, CA 90001")
    assert not same("260 Cagney Ln #209, Town, CA 90001", "260 Cagney Ln, Town, CA 90001")      # a unit is not the whole building's key
    assert not same("100 N Main St, Town, CA 90001", "100 S Main St, Town, CA 90001")
    assert not same("100 Main St, Town, CA 90001", "100 Main St, Town, CA 90002")
    assert not same("100 Main St, Town, CA", "100 Main St, Other, CA")
    assert not same("417 1/2 Heliotrope Ave, Town, CA 90001", "417 Heliotrope Ave, Town, CA 90001")
    assert K("Example Villas, Town, CA 90001") is None
    assert K("308-A2 Santa Isabel Ave, Town, CA 90001") == K("308 Santa Isabel Ave #A2, Town, CA 90001") != K("308-A3 Santa Isabel Ave, Town, CA 90001")

def test_cross_source_uses_it():
    S = {"email:addr:125-e-baker": {"addr": K("125 E Baker St, Town, CA 90001"), "loc": sc.addr_loc("125 E Baker St, Town, CA 90001"), "price": 3000}}
    l = {"id": "email:Redfin:1", "address": "125 Baker St, Town, CA 90001", "price": 3100}
    assert sc.cross_source(l, S, K(l["address"])) == ("skip", "email:addr:125-e-baker")
    l2 = {"id": "email:Redfin:2", "address": "125 W Baker St, Town, CA 90001", "price": 3100}
    S2 = {"x:1": dict(S["email:addr:125-e-baker"])}
    assert sc.cross_source(l2, S2, K(l2["address"])) is None
    S3 = {"appfolio:a": {"addr": K("5 Oak St, Town, CA 90001"), "loc": sc.addr_loc("5 Oak St, Town, CA 90001")}}
    assert sc.cross_source({"id": "appfolio:b", "address": "5 Oak St, Town, CA 90001"}, S3, K("5 Oak St, Town, CA 90001")) is None   # one feed, two listings

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} address-match tests passed")
