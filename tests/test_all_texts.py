"""Every text builder in src/style.py, rendered with realistic args, must pass style.check().
A new builder without an entry here fails the test, so nothing ships unchecked. Sends nothing."""
import os, sys, inspect, json, copy
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import yaml, style, scout as sc
NOT_TEXTS = {"sentences", "wrap", "quote", "text", "check", "fit", "shorten", "sms_link", "join_link", "fmt_phone",
             "proven_sites", "proven_lines", "parse_reaction", "plain"}
CH = "Set your stretch to $5,200."
LONG = "1234 Extraordinarily Longname Boulevard"
CASES = {
    "link_fix": [("994 Example Dr #6", "https://www.zillow.com/apartments/town-ca/994-example-dr/9Abc1x/"), ("9999 Very Long Example Boulevard #12", "https://www.zillow.com/homedetails/1_zpid/")],
 "apply_ack": [("Maple St",), (LONG,)], "apply_expired": [("Maple St",), (LONG,)], "apply_need_profile": [()], "apply_no_place": [()],
 "capabilities": [(), (True,), (True, ["Zillow", "Redfin"]), (True, [], False)], "change_ask": [(CH,)], "change_done": [()], "change_passed": [("Alex",)],
 "change_suggested": [("Sarah", "go up to 5.2k", CH)], "change_unclear": [()], "checkins_set": [(True,), (False,)], "data_note": [()],
 "email_zero_note": [("Zillow",)], "end_ask": [()], "evening_bundle_intro": [(1,), (3,), (3, "buy")], "feedback_ask": [("the texts are too long",)],
 "feedback_dropped": [()], "feedback_fixed": [("the texts are too long",)], "feedback_sent": [()], "first_alert_note": [()],
 "first_day": [(0,), (4,)], "first_week_ask": [()], "first_week_glad": [()], "found_ask": [()], "found_relay": [("Sarah", "we signed!")],
 "full_household": [(), (5,)], "gone_note": [("Maple St",), (LONG,)], "hint_target_not_allowed": [("Sarah", "1111")],
 "how_replies_work": [(), ("Sarah",), ("Sarah", True), ("Sarah", False, False)], "invite": [("Sarah",), ("Sarah", "buy"), ("Sarah", "rental", "+15555550123")],
 "left_member": [()], "left_owner": [("Sarah",)], "listener_note": [()], "loosen_ask": [(CH,)],
 "media_relay": [("Sarah", "Maple St"), ("Sarah", "Maple St", "voice note")], "media_unsupported": [(), ("voice note",)],
 "member_prefs": [("Alex",)], "member_welcome": [("Sarah", "Alex", ["2+ beds", "Up to $4,000/mo"]), ("Sarah", "Alex", ["2+ beds"], "buy", "co_decider", True, True),
                                                 ("Sarah", "Alex", ["2+ beds"], "rental", "in_the_know")],
 "must_or_nice_q": [("parking",)], "mutual": [("Maple St",)], "near_miss_ask": [(3, "price", CH)], "no_change": [()],
 "off_market": [("Maple St", "pending"), ("Maple St", "rented")], "outage_note": [("Example PM", "Mon 1:05 PM")],
 "owner_invite_intro": [("Sarah",), ("Sarah", "sms")], "owner_invite_link": [("Hi Listing Scout, I'm in.",)],
 "owner_member_in": [("Sarah",), ("Sarah", "co_decider", True), ("Sarah", "in_the_know")], "owner_nudge": [("Sarah",)],
 "owner_welcome": [("Alex", 3), ("Alex", 0, True), ("Alex", 2, False, "buy")], "passed_to": [("Sarah",), ("everyone",)],
 "paused_text": [(True,), (False,)], "photon_users_note": [()], "purge_ask": [()], "purge_done": [()], "quiet_week": [(0,), (2,)],
 "reaction": [("Sarah", "❤️", "loved", "Maple St"), ("Sarah", "❤️", "loved", "Maple St", True)], "relay": [("Sarah", "Maple St", "love the kitchen")],
 "remove_ask": [("Sarah",)], "removed_owner": [("Sarah",)], "routine_stale_note": [(190,)], "saved": [("Maple St",)],
 "search_ended_note": [()], "shortlist": [([("Maple St", "$3,900/mo", "Sarah liked it")],), ([],)], "site_quiet_note": [("Redfin",)],
 "sleep_offer": [("10 PM",)], "sleep_set": [(True,), (False,), (True, "8 AM")], "steer_note": [()], "stopped_owner": [("Sarah",)],
 "tighten_ask": [(CH,)], "tour_note": [("Sarah", "Maple St", True), ("Sarah", "Maple St", False)], "tradeoff_text": [({"price": 3, "beds": 1},)],
 "which_one": [()], "member_paused": [("Sarah", True), ("Sarah", False)], "wrapped_up": [()], "wrapup_data_offer": [()], "wrapup_final": [(True,), (False,)],
}
def builders():
    return [n for n, f in inspect.getmembers(style, inspect.isfunction) if f.__module__ == "style" and not n.startswith("_") and n not in NOT_TEXTS]

def test_every_builder_has_a_case():
    missing = [n for n in builders() if n not in CASES]; assert not missing, f"add these to CASES: {missing}"

def test_every_text_passes_check():
    bad, n = [], 0
    for name in builders():
        for args in CASES[name]:
            try: m = getattr(style, name)(*args)
            except (TypeError, style.StyleError) as e: bad.append((name, args, f"call failed: {e}")); continue
            if m is None: continue
            for msg in (m if isinstance(m, (list, tuple)) else [m]):
                if not isinstance(msg, str): continue
                n += 1; p = style.check(msg)
                if p: bad.append((name, args, p, msg))
    assert not bad, json.dumps(bad, indent=1, default=str, ensure_ascii=False)
    return n

def test_names_and_voice():
    words = []
    for name in builders():
        for args in CASES[name]:
            m = getattr(style, name)(*args); words += [m] if isinstance(m, str) else [x for x in (m or []) if isinstance(x, str)]
    blob = "\n".join(words)
    for wrong in ("GrokBot", "Grok bot", "grok bot app", "listing scout", "ListingScout", "short list", "short-list", "not listed.", "N/A", "TBD", "Unknown", "URGENT", "WARNING", "!!"):
        assert wrong not in blob, wrong

def test_alerts_render_clean():
    for crit in ("CRITERIA.example.yaml", "tests/fixtures/CRITERIA.buy.test.yaml"):
        C = yaml.safe_load(open(crit)); sc.CFG.clear(); sc.CFG.update(C)
        A = json.load(open("tests/fixtures/sample_alerts.test.json"))
        for a in A: a["l"].setdefault("flags", [])
        for k in (1, 3, 8):
            t = sc.render(A[:k], C); assert not style.check(t), (crit, k, style.check(t))

if __name__ == "__main__":
    test_every_builder_has_a_case(); n = test_every_text_passes_check(); test_names_and_voice(); test_alerts_render_clean()
    print(f"all-texts: {n} texts from {len(builders())} builders passed")
