"""Render every Listing Scout text from real code + CRITERIA (sandbox copy; sends nothing)."""
import os, sys, json, copy, shutil, subprocess, yaml
import tempfile
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="render_all-"); SB = os.path.join(TMP, "sb")
shutil.copytree(SRC, SB, ignore=shutil.ignore_patterns("node_modules", "logs", "__pycache__"))
os.chdir(SB); sys.path.insert(0, SB)
crit = os.environ.get("RENDER_CRITERIA") or ("CRITERIA.yaml" if os.path.exists("CRITERIA.yaml") else "CRITERIA.example.yaml")   # RENDER_CRITERIA=tests/fixtures/CRITERIA.buy.test.yaml for buy mode
C = yaml.safe_load(open(crit))
C["recipients"] = [dict(C["recipients"][0], phone_last4="0000", **({"name": "Alex"} if crit.endswith("example.yaml") else {})), {"name": "Sarah", "channel": "imessage", "phone_last4": "1111", "role": "co_decider"}]
C["replies"] = True; yaml.safe_dump(C, open("CRITERIA.yaml", "w"))
for f in ("shortlist.json", "members.json", "last_numbered.json", "last_sent.json"):
    if os.path.exists("out/" + f): os.remove("out/" + f)
import style, scout as sc; sc.CFG.update(C)
own = C["recipients"][0]["name"].split()[0]
S = "tests/sample_alerts.json" if os.path.exists("tests/sample_alerts.json") else "tests/fixtures/sample_alerts.test.json"
A = json.load(open(S)); [a["l"].setdefault("flags", []) for a in A]
samp = json.load(open("out/sample.json")) if os.path.exists("out/sample.json") else A[:5]
[a["l"].setdefault("flags", []) for a in samp]
OUT = []; BAD = []
def R(name, t):
    p = style.check(t); OUT.append(f"### {name}\n```\n{t}\n```\n" + (f"PROBLEMS: {p}\n" if p else ""))
    if p: BAD.append((name, p))
al = lambda l, r="new", was=None, m=None: [{"reason": r, "was": was, "market": m, "l": l}]
OUT.append(f"# Listing Scout: every text, rendered from code ({SRC})\n")
OUT.append("## Flow A: owner setup\n")
R("A1 owner welcome (with card)", style.owner_welcome(own, 620, True))
R("A2 snapshot", sc.snapshot(samp, 620, C)); R("A2b snapshot, nothing fits", sc.snapshot([], 620, C))
R("A3 first-day note", style.first_day(620))
OUT.append("## Flow C: alerts\n")
R("C1 single new (approved)", sc.render([A[0]], C))
R("C2 price drop", sc.render(al(A[0]["l"], "price_drop", A[0]["l"]["price"] + 200, A[0].get("market")), C))
R("C3 relist", sc.render(al(A[0]["l"], "relist", None, A[0].get("market")), C))
R("C4 back, and lower", sc.render(al(A[0]["l"], "relist_lower", A[0]["l"]["price"] + 200), C))
a = copy.deepcopy(A[0]["l"]); b = copy.deepcopy(a); b.update(id="zillow:x", source="Zillow", price=a["price"] + 55)
R("C5 two sites, two prices", sc.render(al(sc.merge_dupes([a, b], C)[0]), C))
l = copy.deepcopy(A[0]["l"]); l.update(price=None, beds=None, address=None, available="", url=None); R("C6 missing fields", sc.render(al(l), C))
l = copy.deepcopy(A[0]["l"]); l["apply_url"] = "https://www.zillow.com/rental-manager/apply/synth-1/"; R("C9 with the listing's apply link", sc.render(al(l), C))
l = copy.deepcopy(A[0]["l"]); l["flags"] = ["suspicious payment/deposit wording"]; R("C7 scam caution (one signal)", sc.render(al(l), C))
l = copy.deepcopy(A[0]["l"]); l["flags"] = ["suspicious payment/deposit wording", "photo/address mismatch"]; R("C7b scam caution (two signals)", sc.render(al(l), C))
R("C8 bundle of 3", sc.render([A[0], A[1], dict(A[2], reason="price_drop", was=(A[2]["l"].get("price") or 0) + 100)], C))
if len(A) >= 10: R("C9 busy day (top 5 + overflow)", sc.render([dict(x, reason="new") for x in A[:12]], C))
R("C10 outage notice", style.outage_note("Example PM", "Mon 1:05 PM"))
OUT.append("## Flow B: sharing the search\n")
R("B1a invite intro (to owner)", style.owner_invite_intro("Sarah")); R("B1 invite note", style.invite("Sarah", line="+15550001234"))
R("B2 member welcome (co-decider, replies on)", style.member_welcome("Sarah", own, sc.reflect(C), role="co_decider", replies=True))
R("B2b member welcome (in the know)", style.member_welcome("Sarah", own, sc.reflect(C), role="in_the_know", replies=True))
R("B2c member welcome (replies off)", style.member_welcome("Sarah", own, sc.reflect(C), replies=False))
R("B3 owner: member is in", style.owner_member_in("Sarah", "co_decider", True))
R("B4 member prefs", style.member_prefs(own)); R("B5 owner nudge (no OK)", style.owner_nudge("Sarah"))
R("B6 hint: target not allowed", style.hint_target_not_allowed("Sarah", "XXXX"))
R("B7 full household (plan limit)", style.full_household(10)); R("B8 help", style.how_replies_work(own))
OUT.append("## Flow B: replies (replies.py --as, sandbox state)\n")
json.dump([{"id": x["l"]["id"], "where": __import__("notify").short_where(x["l"]), "price": f"${x['l']['price']:,.0f}/mo" if x["l"].get("price") else None} for x in A[:2]], open("out/last_numbered.json", "w"))
def sim(who, text, kind=None):
    cmd = ["python3", "replies.py", "--as", who, "--text", text] + (["--kind", kind] if kind else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    msgs = [m for m in r.stdout.split("--> to ") if m.strip()]
    if r.returncode: OUT.append(f"ERROR {r.stderr}\n")
    msgs = ["\n".join(x for x in m.splitlines() if not x.startswith(("[sim]", "LISTENER_STOP", "CLOSE_SAVED_SEARCHES", "FEEDBACK_EMAIL"))) for m in msgs]
    msgs = [m for m in msgs if m.strip()]
    for m in msgs:
        who_to, _, body = m.partition(":\n"); R(f'{who} says "{text}" -> {who_to.strip()}', body.strip())
    for line in r.stdout.splitlines():
        if line.startswith(("[sim]", "LISTENER_STOP", "CLOSE_SAVED_SEARCHES")): OUT.append(f"_{line}_\n")
for w, t, *k in [("Sarah", "OK"), ("Sarah", "love the yard!! but is the garage big enough for two cars?"), (own, "yes, close to work"),
                 ("Sarah", "tour Maple St"), (own, "shortlist"), ("Sarah", "hmm"), ("Sarah", "pic", "photo"),
                 ("Sarah", "pause"), ("Sarah", "resume"), (own, "help"), ("Sarah", "what do you keep"),
                 (own, "add 78745"), (own, "yes"), ("Sarah", "can we go up to 4,500?"), (own, "no"),
                 ("Sarah", "we found a place"), (own, "yes"), (own, "no"),
                 ("Sarah", "bug, the link didn't open"), ("Sarah", "yes"), (own, "idea: a map view"), (own, "no"),
                 ("Sarah", "leave"), ("Sarah", "STOP")]:
    sim(w, t, *k)
R("B9 media unsupported", style.media_unsupported()); R("B10 found ask", style.found_ask()); R("B11 congrats", style.wrapped_up())
R("B12 left (owner)", style.left_owner("Sarah")); R("B13 left (member)", style.left_member()); R("B14 stopped (owner)", style.stopped_owner("Sarah"))
R("B15 which one", style.which_one()); R("B16 empty shortlist", style.shortlist([]))
OUT.append("## Extra features\n")
R("F1 Take a break: owner removes someone (asks first)", style.remove_ask("Sarah")); R("F1b removed (owner)", style.removed_owner("Sarah"))
R("H1 first-alert note (once per person)", style.first_alert_note()); R("H2 what can you do (proven: Zillow)", style.capabilities(True, ["Zillow"])); R("H3 what can you do (none proven)", style.capabilities(False, [])); R("H4 help (Android)", style.how_replies_work("Sarah", android=True))
R("F2 Sleep mode offer (once, the morning after)", style.sleep_offer("2:14 AM")); R("F2b Sleep mode on", style.sleep_set(True)); R("F2c Sleep mode off", style.sleep_set(False))
R("F3 Still available? (liked place gone ~24h)", style.gone_note("Santa Isabel"))
R("F5 Fine-tune: read-back", style.change_ask("Add 78745 to the search.")); R("F5b co-decider suggestion (to owner)", style.change_suggested("Sarah", "can we add 78745?", "Add 78745 to the search."))
R("F5c done", style.change_done()); R("F5d unclear", style.change_unclear()); R("F5e passed (to co-decider)", style.change_passed(own)); R("F5f no change", style.no_change())
R("F6 We found it: co-decider says it (to owner)", style.found_relay("Sarah", "we found it!!")); R("F6b data offer (owner)", style.wrapup_data_offer())
R("F7 end my search: ask (owner)", style.end_ask()); R("F7b end my search: goodbye (everyone)", style.search_ended_note()); R("F7c Photon Users reminder (owner)", style.photon_users_note())
R("F6c final (cleared)", style.wrapup_final(True)); R("F6d final (kept)", style.wrapup_final(False))
R("F7 What I keep", style.data_note()); R("F7b delete everything (asks first)", style.purge_ask()); R("F7c deleted", style.purge_done())
OUT.append("## Make it better (bug or idea, confirm first, pending_review only)\n")
R("M1 confirm", style.feedback_ask("bug, the link didn't open")); R("M2 sent (after a clear yes)", style.feedback_sent())
R("M3 dropped (no)", style.feedback_dropped()); R("M4 DRAFT ONLY: You asked, it's fixed (sent by hand after approval + fix)", style.feedback_fixed("bug, the link didn't open"))
OUT.append("## Channels: iPhone (iMessage) vs Android (SMS/RCS)\n")
import notify as _nf
R("H1 reaction sent as text (to an iPhone)", style.reaction("Sarah", "\u2764\ufe0f", "loved", "Maple St"))
R("H1b reaction sent as text (to Android)", style.reaction("Sarah", "\u2764\ufe0f", "loved", "Maple St", True))
R("H2 alert (to Android: no emoji)", _nf.for_channel(sc.render(A[:1], C), None, "sms")[0])
R("H3 member welcome (to Android: no card, save line)", _nf.for_channel(style.member_welcome("Sarah", own, sc.reflect(C), "rental", "co_decider", True, True), "card.vcf", "sms")[0])
R("H4 owner invite intro (owner on Android)", style.owner_invite_intro("Sarah", "sms"))
OUT.append("## Criteria hygiene (must-have vs nice-to-have; confirm-first)\n")
R("K1 setup question", style.must_or_nice_q("garage")); R("K1b setup question (layout)", style.must_or_nice_q("layout"))
R("K2 trade-off (real counts)", style.tradeoff_text((2, 12))); R("K2b trade-off (can't count)", style.tradeoff_text(None))
R("K3 weekly near-miss check-in", style.near_miss_ask(3, "price", "Set your stretch to $5,200."))
R("K4 volume: quiet week", style.loosen_ask("Set your stretch to $5,200.")); R("K5 volume: busy week", style.tighten_ask("Make a garage a must-have."))
OUT.append("## Source line, quiet week, daily cap, first week\n")
l = copy.deepcopy(A[0]["l"]); l.update(source="Redfin", posted_ts=__import__("time").time() - 1200); R("P1 alert with Via + Posted (source gave a time)", sc.render(al(l), C))
R("P2 quiet-week pulse (real count)", style.quiet_week(620)); R("P2b quiet-week pulse (no count)", style.quiet_week(None))
R("P3 daily cap ask", style.change_ask("Cap alerts at 3 a day.")); R("P3b evening bundle", style.evening_bundle_intro(3) + "\n\n" + sc.render(A[:3], C).split("\n\n", 1)[1])
R("P6 what can you do (owner)", style.capabilities(True)); R("P6b what can you do (member)", style.capabilities(False))
R("P7 no check-ins", style.checkins_set(False)); R("P7b check-ins on", style.checkins_set(True))
R("P4 first-week ask", style.first_week_ask()); R("P4b all good", style.first_week_glad()); R("P5 listener back", style.listener_note())
if sc.is_buy(C):   # buy mode: real parser output from the synthetic for-sale fixtures
    import glob as _g
    OUT.append("## Buy mode (synthetic Zillow / Redfin / Realtor.com emails)\n")
    BL = {}
    for f in sorted(_g.glob("tests/fixtures/email_buy/*")):
        for l in sc.parse_email_file(f): BL[l["address"].split(",")[0]] = sc.classify(l, C)
    R("Y1 new home (HOA not listed)", sc.render(al(BL["123 Maple Test Dr"]), C))
    R("Y2 new home (HOA, lot, open house)", sc.render(al(BL["88 Spruce Sample Rd"]), C))
    R("Y3 price cut", sc.render(al(BL["5 Willow Test Pl"], "price_drop", 749000), C))
    R("Y4 back on market", sc.render(al(BL["300 Pine Demo Ave"], "relist"), C))
    R("Y5 coming soon", sc.render(al(BL["12 Elm Pretend St"]), C))
    R("Y6 pending (to shortlisters only)", style.off_market("9 Birch Fake Ct", "pending")); R("Y6b sold", style.off_market("77 Cedar Mock Way", "sold"))
    R("Y7 evening roundup", style.evening_bundle_intro(2, "home") + "\n\n" + sc.render([al(BL["123 Maple Test Dr"])[0], al(BL["12 Elm Pretend St"])[0]], C).split("\n\n", 1)[1])
    _ag = copy.deepcopy(BL["123 Maple Test Dr"]); _ag["agent_url"] = "https://www.redfin.com/CA/Exampleville/12-Fake-Ln-90001/home/7000123/tour"
    R("Y10 with the listing's agent link", sc.render(al(_ag), C))
    R("Y8 owner welcome (buy)", style.owner_welcome(own, 120, True, "home"))
    R("Y9 member welcome (buy)", style.member_welcome("Sarah", own, sc.reflect(C), "home", "co_decider", True, True))
open(os.path.join(TMP, "rendered.md"), "w").write("\n".join(OUT))
print("rendered:", os.path.join(TMP, "rendered.md")); print("texts:", sum(o.startswith("###") for o in OUT), "with problems:", len(BAD)); [print(b) for b in BAD]
