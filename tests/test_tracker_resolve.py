"""Opaque Redfin/Zillow trackers resolve to a clean listing page via redirects (network mocked)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc
T = "https://redmail3.redfin.com/a/click?_t=SECRET&_e=x"

def _setup(chain):
    sc.RESOLVE_LINKS = True; sc.RESOLVE_CACHE = tempfile.mktemp(suffix=".json"); calls = []
    def hop(url, m):
        calls.append((url, m)); return (302, chain.get(url)) if chain.get(url) else (403, None)
    sc._hop = hop; return calls

def test_redfin_resolves_clean():
    calls = _setup({T: "https://www.redfin.com/CA/Newport-Beach/1544-Placentia-Ave-92663/home/4579991?utm=1#x"})
    assert sc._clean_link("email:addr:x", T) == "https://www.redfin.com/CA/Newport-Beach/1544-Placentia-Ave-92663/home/4579991"
    n = len(calls); sc._clean_link("email:addr:x", T); assert len(calls) == n      # cached
    assert "SECRET" not in open(sc.RESOLVE_CACHE).read()                           # tracker never stored

def test_non_listing_is_none():
    _setup({T: "https://www.redfin.com/zipcode/92663/apartments-for-rent?x=1"})
    assert sc._clean_link("email:addr:x", T) is None
    _setup({T: "https://www.redfin.com/login-v2"}); assert sc._clean_link("email:addr:x", T) is None
    _setup({T: "https://evil.example/CA/x/home/1"}); assert sc._clean_link("email:addr:x", T) is None

def test_head_then_get_and_errors():
    seen = []
    sc.RESOLVE_LINKS = True; sc.RESOLVE_CACHE = tempfile.mktemp()
    def hop(url, m):
        seen.append(m)
        if m == "HEAD": raise OSError("boom")
        return 301, "https://www.redfin.com/CA/Costa-Mesa/1-A-St-92627/apartment/12345"
    sc._hop = hop
    assert sc._clean_link("email:addr:x", T) == "https://www.redfin.com/CA/Costa-Mesa/1-A-St-92627/apartment/12345" and seen == ["HEAD", "GET"]

def test_zillow_opaque():
    z = "https://click.mail.zillow.com/f/a/abc~~/def"
    _setup({z: "https://www.zillow.com/homedetails/1-A-St-Costa-Mesa-CA-92627/12345678_zpid/?rtoken=t"})
    assert sc._clean_link("email:addr:x", z) == "https://www.zillow.com/homedetails/1-A-St-Costa-Mesa-CA-92627/12345678_zpid/"

def test_off_by_default():
    sc.RESOLVE_LINKS = False; assert sc.resolve_tracker(T) is None

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} tracker-resolve tests passed")
