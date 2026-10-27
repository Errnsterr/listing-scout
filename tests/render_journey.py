"""Owner vs member journey, beat by beat, rendered from real code + CRITERIA. Sends nothing.
Usage: python3 tests/render_journey.py [MemberName] -> out/journey-compare.md"""
import os, sys, json, re, yaml
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "src")); os.chdir(HERE)
import style, scout as sc
C = yaml.safe_load(open("CRITERIA.yaml")); sc.CFG.update(C)
R = C["recipients"]; own = R[0]["name"].split()[0]
mem = sys.argv[1] if len(sys.argv) > 1 else (R[1]["name"] if len(R) > 1 else "Sarah")
mf = mem.split()[0]; tag = mem.replace(" ", "-")
kind = "home" if C.get("mode") == "buy" else "rental"
link_f = f"out/invite-{tag}.txt"
inv = open(link_f).read().strip() if os.path.exists(link_f) else style.invite(mf, kind)
inv = re.sub(r"(sms:\+1)\d{6}", r"\1******", re.sub(r"\(\d{3}\) \d{3}-", "(•••) •••-", inv))   # show only the line's last 4 here
samp = json.load(open("out/sample.json")) if os.path.exists("out/sample.json") else []
for a in samp: a["l"].setdefault("flags", [])
N = len(json.load(open("state.json"))["listings"]) if os.path.exists("state.json") else None   # your real count after the first run
if N is None: N = 40; print("(Counts below are a sample, not your data.)")
snap = sc.snapshot(samp, N, C)
alert = sc.render(samp[:1], C) if samp else "(no sample listing)"
rep = bool(C.get("replies"))
beats = [
 ("1. Invite / how it starts", f"({own} set it up in chat with the bot: the setup flow is the invite.)", f"The bot texts {own}:\n\n%s\n\nthen the invite. {own} forwards it to %s, who gets:\n\n%s" % (style.owner_invite_intro(mf), mf, inv)),
 ("2. Feeling received + contact card", "[+ contact card]\n" + style.owner_welcome(own, N, True),
  "[+ contact card] (sent the moment she texts)\n" + style.member_welcome(mf, own, sc.reflect(C), kind, R[1].get("role", "co_decider") if len(R) > 1 else "co_decider", rep, True)),
 ("3. Reply OK (receipt)", f"{own} replies OK. Nothing more is needed.", "%s replies OK. They get one optional note:\n\n%s" % (mf, style.member_prefs(own))),
 ("4. What's out there right now (1 minute later)", snap, snap),
 ("5. Closing the loop for the owner", f"(n/a: {own} is the owner)", f"{own} gets, as soon as they text:\n\n" + style.owner_member_in(mf, R[1].get("role", "co_decider") if len(R) > 1 else "co_decider", rep)),
 ("6. Calm alerts (same text, same moment)", alert, alert),
 ("7. Quiet day one", style.first_day(N), "(shared: the same one-time note, if it fires, goes to both)"),
 ("8. If they never text (after ~24h, once)", "(n/a)", f"{own} gets:\n\n" + style.owner_nudge(mf)),
]
out = [f"# Journey compare: {own} (owner) vs {mf} (member)\n", "Rendered from code (style.py, scout.py, CRITERIA.yaml). Nothing sent.\n"]
for t, a, b in beats:
    out += [f"## {t}\n", f"**{own}**\n```\n{a}\n```\n", f"**{mf}**\n```\n{b}\n```\n"]
    for x in (a, b):
        body = "\n".join(l for l in x.split("\n") if not l.startswith("[+") and not l.startswith("(")) if "\n" in x else ""
open("out/journey-compare.md", "w").write("\n".join(out)); print("out/journey-compare.md")
