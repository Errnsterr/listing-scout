"""v1.2.20: a pre-v1.2 space-joined addr in state.json must never crash a pass."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import scout

def test_fuzzy_dup_skips_legacy_addr():
    S = {"appfolio:old": {"addr": "2 sample", "price": 4000, "loc": {"zip": "92625", "city": "Corona del Mar"}},
         "email:addr:x": {"addr": "80 sample beach", "price": 4000, "loc": {"zip": "92625"}}}
    l = {"id": "zillow:new", "price": 4000, "zip": "92625", "address": "2 Sample Ave, Corona del Mar, CA 92625"}
    ak = scout.addr_key(l["address"])
    assert scout.fuzzy_dup(l, S, ak) is None   # used to raise ValueError

def test_normalize_moves_legacy_and_is_idempotent():
    S = {"a": {"addr": "2 sample"}, "b": {"addr": "1|main|"}, "c": {}}
    assert scout.normalize_state_addrs(S) == 1
    assert "addr" not in S["a"] and S["a"]["legacy_addr"] == "2 sample"
    assert S["b"]["addr"] == "1|main|"
    assert scout.normalize_state_addrs(S) == 0

def test_zipidx_tolerates_legacy():
    scout.build_zipidx({"a": {"addr": "6707 sample", "loc": {"zip": "92627", "city": "Costa Mesa"}}})

def test_addr_key_always_three_parts():
    for a in ["2 Sample Ave", "421 Sample St #425", "702 1/2 Sample Ave"]:
        k = scout.addr_key(a)
        assert k is None or k.count("|") == 2

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f()
    print("ok")
