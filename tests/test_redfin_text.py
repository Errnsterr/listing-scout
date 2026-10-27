"""Redfin for-sale alert rendered as text (real layout, SYNTHETIC values): '[image: ...] (URL) $X' price lines,
'&middot;' separators, opaque trackers (never used as links), and 'Nearby similar homes' excluded."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc
F = "tests/fixtures/email_redfin_text/redfin_forsale_instant.txt"

def test_reads_the_match_only():
    L = sc.parse_email_file(F); assert len(L) == 1, L        # the similar-homes block is not a saved-search match
    l = L[0]
    assert (l["source"], l["price"], l["beds"], l["baths"]) == ("Redfin", 1349000, 4, 1.5)
    assert l["address"] == "100 Example St, Los Angeles, CA 90001" and l["lot"] == "6,120 sq ft lot" and l["sqft_buy"] == 1300

def test_never_a_tracker_link():
    l = sc.parse_email_file(F)[0]
    assert l["url"] is None                                   # opaque Redfin tracker: no link rather than a tokened one
    assert sc._clean_link("email:addr:x", "https://redmail3.redfin.com/a/click?_t=a&_e=b") is None
    assert sc._clean_link("email:addr:x", "https://click.mail.zillow.com/f/a/x~~/y?target=https%3A%2F%2Fwww.zillow.com%2Fapartments%2Fla%2Fsynth%2F5Xs%2F%3Frtoken%3Dt") \
        == "https://www.zillow.com/apartments/la/synth/5Xs/"   # tracker with the real page inside: plain public link

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for f in fns: f()
    print(f"{len(fns)} redfin-text tests passed")
