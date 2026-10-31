"""v1.2.13 duplicate fixes: one home, one text, unless truly re-listed."""
import os, sys, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import scout as sc
sc.MATCH_LOG = "/tmp/match_test.log"

def L(i, a, z, price, beds=2, **k): return dict(id=i, address=a, zip=z, price=price, beds=beds, **k)
def rec(l, **k): return dict(addr=sc.addr_key(l["address"]), loc=sc.loc_of(l), price=l["price"], beds=l.get("beds"), gone_since=None, **k)
def cs(l, S): return sc.cross_source(l, S, sc.addr_key(l["address"]))

def test_1_repeated_unit():
    K = sc.addr_key
    assert K("602 Begonia Ave #B-B-B, Corona del Mar, CA 92625") == K("602 Begonia Ave #B, Corona del Mar, CA 92625")
    assert K("602 Begonia Ave #B, Corona del Mar, CA 92625") != K("602 Begonia Ave #C, Corona del Mar, CA 92625")

def test_2_no_unit_vs_one_unit():
    a = L("email:addr:108-olive", "108 Olive St, Newport Beach, CA 92663", "92663", 4250)
    b = L("email:addr:108-olive-a", "108 Olive St #A, Newport Beach, CA 92663", "92663", 4250)
    assert cs(b, {a["id"]: rec(a)})[:2] == ("skip", a["id"])
    c = L("email:addr:108-olive-b", "108 Olive St #B, Newport Beach, CA 92663", "92663", 3900)
    assert cs(c, {a["id"]: rec(a), b["id"]: rec(b)}) is None             # a second unit at another price still alerts
    S = {b["id"]: rec(b), "x": rec(L("x", "108 Olive St #C, Newport Beach, CA 92663", "92663", 4250))}
    assert cs(a, S) is None                                               # bare street with two units on file: ambiguous

def test_3_spelled_number_is_a_building():
    l = sc._street_from_url({"id": "email:addr:27-seventy-five-mesa-verde", "address": "27 Seventy Five Mesa Verde, Costa Mesa, CA 92626",
                             "url": "https://www.redfin.com/CA/Costa-Mesa/1555-Mesa-Verde-Dr-E-92626/home/4555030"})
    assert l["address"].startswith("1555 Mesa Verde Dr E") and l["building"] == "27 Seventy Five Mesa Verde"
    assert sc._street_from_url({"id": "i", "address": "27 Main St, Town, CA 90001", "url": "https://www.redfin.com/CA/Town/9-Other-St-90001/home/1"})["address"].startswith("27 Main")

def test_4_building_name_to_street():
    f3 = L("email:addr:1525-placentia-f3", "1525 Placentia Ave APT F3, Newport Beach, CA 92663", "92663", 3160)
    S = {f3["id"]: rec(f3, bldg="Sandpointe Cove Apartment Homes")}
    red = dict(id="email:Redfin:m1-3160-2-870", address="Sandpointe Cove Apartment Homes", building="Sandpointe Cove Apartment Homes",
               zip="92663", city="Newport Beach", price=3160, beds=2)
    assert sc.cross_source(red, S, None)[:2] == ("skip", f3["id"])
    assert sc.cross_source(dict(red, price=3500), S, None) is None       # different price: not proven the same

def test_5_half_is_a_unit():
    b = L("email:addr:501-marguerite-b", "501 Marguerite Ave #B, Newport Beach, CA 92625", "92625", 4950)
    h = L("email:addr:501-1/2-marguerite", "501 1/2 Marguerite Ave, Corona del Mar, CA 92625", "92625", 4950)
    assert cs(h, {b["id"]: rec(b)})[:2] == ("skip", b["id"])
    assert cs(b, {h["id"]: rec(h)})[:2] == ("skip", h["id"])
    assert cs(dict(h, price=4500), {b["id"]: rec(b)}) is None

def test_6_relist_needs_every_copy_gone():
    now = time.time()
    S = {"tt:1": {"gone_since": now - 4 * 86400, "dup_of": None, "also_ids": ["appfolio:1"]},
         "appfolio:1": {"gone_since": None, "dup_of": "tt:1"}}
    assert sc.group_live("tt:1", S, now, 3) == "appfolio:1"
    S["appfolio:1"]["gone_since"] = now - 4 * 86400
    assert sc.group_live("tt:1", S, now, 3) is None

def test_7_unit_after_from_building():
    T = [{"id": "email:addr:400-enclave-cir", "bkeys": ["s:400|enclave|costa mesa"], "from_price": 2810}]
    u = dict(id="email:addr:400-enclave-cir-422-301", address="400 Enclave Cir #422-301, Costa Mesa, CA 92626", price=3590, zip="92626")
    u["bkeys"] = None
    orig = sc.bkeys; sc.bkeys = lambda l: ["s:400|enclave|costa mesa"]
    try:
        assert sc.from_building(u, T) == ("email:addr:400-enclave-cir", 2810)
        assert sc.from_building(dict(u, price=2700), T) is None          # below the 'From' price: real news, it texts
    finally: sc.bkeys = orig

if __name__ == "__main__":
    fs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fs: f()
    print(f"ok {len(fs)} v1.2.13 dupe tests")
