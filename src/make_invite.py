#!/usr/bin/env python3
"""Household invite kit: two texts the bot sends the OWNER (never the member), then the owner forwards one.
Usage: python3 src/make_invite.py Name   (run after make_contact.py "Name")
Writes:
  out/invite-<Name>-intro.txt  "Here's <Name>'s invite." / "Forward the next text to <Name>."
  out/invite-<Name>.txt        the plain invite to forward: no URLs, ends with the bot line, formatted (iPhone auto-links it)
  out/invite-<Name>-link.txt   internal fallback only, never texted: sms: link with the invite prefilled
Privacy: no hosted or third-party page is used, so nobody outside the two phones sees who is invited.
The invite holds only the bot's line for them (read from out/Listing-Scout-<Name>.vcf), never their own number.
Nothing is sent here; the bot sends the two texts to the owner with notify.py only after the owner says yes."""
import os, re, sys, json, time
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
sys.path.insert(0, _SRC)
import style, yaml
C = yaml.safe_load(open(os.path.join(HERE, "CRITERIA.yaml")))
KIND = "rental" if C.get("mode", "lease") == "lease" else "home"
name = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
first = name.split()[0]; tag = name.replace("'s", "s").replace(" ", "-")
vcf = os.path.join(HERE, "out", f"Listing-Scout-{tag}.vcf")
m = re.search(r"^TEL[^:]*:(\+?\d+)", open(vcf).read(), re.M) if os.path.exists(vcf) else None
if not m: sys.exit(f"No card for {name} yet: run python3 src/make_contact.py \"{name}\" first.")
mf0 = os.path.join(HERE, "out", "members.json")   # owner's saved channel (notify.channel_of): Android gets Android steps
och = (json.load(open(mf0)) if os.path.exists(mf0) else {}).get(C["recipients"][0]["name"], {}).get("channel", "imessage")
intro, inv = style.owner_invite_intro(first, och), style.invite(first, KIND, m.group(1))
for t in (intro, inv): assert not style.check(t), style.check(t)
o = lambda f: os.path.join(HERE, "out", f)
open(o(f"invite-{tag}-intro.txt"), "w").write(intro + "\n")
open(o(f"invite-{tag}.txt"), "w").write(inv + "\n")
open(o(f"invite-{tag}-link.txt"), "w").write(style.owner_invite_link(inv) + "\n")
# start the 24h clock for the owner's one gentle heads-up (notify.py nudge check)
mf = o("members.json"); M = json.load(open(mf)) if os.path.exists(mf) else {}
M.setdefault(name, {}).setdefault("invited_ts", time.time()); json.dump(M, open(mf, "w"), indent=1)
print("\n".join([o(f"invite-{tag}-intro.txt"), o(f"invite-{tag}.txt"), o(f"invite-{tag}-link.txt")]))
