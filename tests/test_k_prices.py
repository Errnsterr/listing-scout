"""'$30K'-style prices (HotPads, 2026-10-26: two emails read as 0 homes and tripped the 'couldn't read homes' note).
'$30K', 'from $1.8K', '$36.6K', '$2.12K' = the number x 1000, with or without '/mo'. Old formats keep working. Fixture is made up."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc
FX = os.path.join("tests", "fixtures", "hotpads_text", "hotpads_9000001.txt")

def test_num_k():
    for s, v in (("$30K", 30000), ("1.8K", 1800), ("$36.6K", 36600), ("$2.12K", 2120), ("$2.12 k", 2120), ("$4,350", 4350), ("4350", 4350), (None, None)):
        assert sc.num(s) == v, (s, sc.num(s))

def test_price_patterns():
    for s, v in (("$30K/mo", 30000), ("$1.8K", 1800), ("from $36.6K/mo", 36600), ("$2.12K", 2120), ("$4,350/mo", 4350), ("$1,797+/mo", 1797)):
        m = sc.HP_PRICE.match(s); assert m and sc.num(m.group(1)) == v, s
    for s, v in (("$30K/mo", 30000), ("from $1.8K", 1800), ("$4,350/mo", 4350), ("$4350", 4350)):
        m = sc.PRICE_LINE.match(s); assert m and sc.num(m.group(1)) == v, s
    assert not sc.PRICE_LINE.match("$1,797+/mo")   # unchanged: '+/mo' cards are not plain price lines
    assert [sc.num(x) for x in sc.PRICE.findall("Rent $30K/mo, was $4,350, or $2.12K")] == [30000, 4350, 2120]

def test_k_card_email_parses():
    got = {l["address"]: l["price"] for l in sc.parse_email_file(FX)}
    assert got == {"100 Testwood Ln, Shelbyville, CA 90001": 30000, "200 Testwood Ave, Shelbyville, CA 90001": 1800,
                   "300 Testwood Ct, Shelbyville, CA 90001": 36600, "400 Testwood Way, Shelbyville, CA 90001": 2120,
                   "500 Testwood Pl, Shelbyville, CA 90001": 4350}, got

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
