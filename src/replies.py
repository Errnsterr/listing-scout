#!/usr/bin/env python3
"""Reply handling for shared searches (no AI). Called by listen.mjs with {"from": handle, "text": ...} on stdin.
People reply naturally: "yes", "no", "no, too far from work", "love the kitchen", "tour it", "yes to Maple St".
- A reply attaches to the most recent listing sent to that person. In a text with a few places, naming the
  street picks one; otherwise it attaches to the first place in that text, and every relay names the street.
- Keywords (yes / no / love / tour / pass) only mark the shared shortlist. The person's own words are relayed
  verbatim, trimmed and quoted. Never reworded, never invented. No landlord contact, no booking.
  python3 src/replies.py --as "Alex" --text "love the kitchen"     # simulate (no Photon, prints what would be sent)
  echo '{"from": "+1...", "text": "yes"}' | python3 src/replies.py --send   # live (from listen.mjs)"""
import os, sys, re, json, time
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
sys.path.insert(0, _SRC)
_IN_SRC = os.path.basename(_SRC) == "src"
import yaml, style, features
CRIT_PATH = os.environ.get("SCOUT_CRITERIA", os.path.join(HERE, "CRITERIA.yaml"))
C = yaml.safe_load(open(CRIT_PATH))
for _r in C.get("recipients") or []:   # "co-decider" / "Co Decider" -> "co_decider"
    if _r.get("role"): _r["role"] = re.sub(r"[\s-]+", "_", str(_r["role"]).strip().lower())
SL, NUM, MEM = (os.path.join(HERE, "out", f) for f in ("shortlist.json", "last_numbered.json", "members.json"))
load = lambda f, d: json.load(open(f)) if os.path.exists(f) else d
A = sys.argv[1:]; really = "--send" in A; sim = "--as" in A

YES = r"\b(yes|yep|yeah|yup|love|loved|like|liked|great|nice|perfect|interested|want it|into it|beautiful|gorgeous)\b|👍|❤️|😍"
NO = r"^\s*(no|nope|nah|pass)\b|\b(not for (us|me)|pass on|skip it|too (far|small|expensive|pricey|much))\b|👎"
TOUR = r"\b(tour|see it|visit|showing|look at it in person)\b"

def people():
    R = [dict(r) for r in C["recipients"] if r.get("phone_last4") or sim]
    for i, r in enumerate(R): r.setdefault("role", "owner" if i == 0 else "co_decider")
    return R

def chan(r):
    """Saved channel for a person (members.json); iMessage until a check says otherwise."""
    return load(MEM, {}).get(r["name"], {}).get("channel") or "imessage"

def deliver(r, t, card=None):
    m = load(MEM, {}).get(r["name"], {})
    if m.get("stopped") or m.get("left"): print(f"(not texting {r['name']}: stopped or left)"); return False
    if not really or sim:
        ch = chan(r)
        import notify; t, card = notify.for_channel(t, card, ch)   # same SMS/RCS adaptation as a live send
        print(f"--> to {r['name']}{'' if ch == 'imessage' else f' [{ch}]'}:{' [+ contact card]' if card else ''}\n{t}\n"); return True
    import notify
    live = {x["name"]: x for x in notify.recipients()}
    if r["name"] not in live: print(f"WARNING: not texting {r['name']}: not a live Photon user"); return False
    return bool(notify.send(live[r["name"]], t, True, card))

# Confirm-first answers. Negation is checked FIRST: any no/not/don't anywhere means no.
# A yes must be the whole message, a clear affirmative ("yes", "yes please", "sure", "do it", "ok"); bare "please" is not a yes.
NOR = r"\b(no|nope|nah|not|don'?t|do not|never|cancel|stop|wait|hold off|keep it|nevermind|never mind)\b|n't\b"
_YES1 = r"(yes|yep|yeah|yup|sure|ok|okay|k|do it|go ahead|sounds good|please do|yes please|ok do it|okay do it|yes do it|sure thing|go for it|👍)"
YESR = rf"^{_YES1}(\s+{_YES1})*(\s+please)?$"

WORD_YES = r"(yes|yes please|do it|go ahead|yes do it|yes go ahead)"   # delete-all / data deletion: no "k", no emoji
def norm(t):
    t = re.sub(r"[.!,?]+", " ", (t or "").lower().replace("\u2019", "'")).strip(); return re.sub(r"\s+", " ", t)

def answer(t):
    """'no' | 'yes' | None. Never guesses: anything not clearly yes or no lets the question lapse."""
    t = re.sub(r"[.!,?]+", " ", (t or "").lower().replace("\u2019", "'")).strip(); t = re.sub(r"\s+", " ", t)
    if re.search(NOR, t): return "no"
    if re.fullmatch(YESR, t): return "yes"
    return None

def stop_listener():
    """Finish line: the scout loop already stopped (out/search_ended.json); tell listen.mjs to exit after this text."""
    print("LISTENER_STOP")

def do_pending(pend, me, P, M, owner, save_m):
    """Runs only after a clear yes to the question that was asked."""
    k = pend["type"]
    if k == "remove":
        r = next((x for x in P if x["name"] == pend["name"]), None)
        if r: deliver(r, style.left_member())
        features.purge_member(pend["name"]); M.clear(); M.update(load(MEM, {}))
        deliver(me, style.removed_owner(pend["name"].split()[0])); return
    if k == "feedback":   # Make it better: the person said a clear yes; saved as pending_review (never queued or built)
        item = features.record_feedback(pend["payload"])
        to = (C.get("feedback_email") or "").strip()
        if to:   # template installs only; the live install has no feedback_email, so nothing is emailed
            print("FEEDBACK_EMAIL " + json.dumps({"to": to, "subject": f"Listing Scout feedback (v{item['version']})",
                  "body": {k_: item[k_] for k_ in ("words", "version", "last_text")}}))
        deliver(me, style.feedback_sent()); return
    if k == "purge":
        features.purge_all(); deliver(me, style.purge_done()); return
    if k == "sleep":
        M.setdefault(me["name"], {})["sleep"] = True; save_m(); deliver(me, style.sleep_set(True, features.wake_label(C))); return
    if k == "change":
        if really and not sim:
            features.apply_change(pend["change"], CRIT_PATH)
            import subprocess   # quiet re-seed so places already out there don't flood in
            subprocess.Popen(["python3", "src/scout.py" if _IN_SRC else "scout.py", "--seed"], cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        else: print(f"[sim] would back up and update CRITERIA ({pend['change']['kind']} = {pend['change']['value']}), then re-seed quietly")
        deliver(me, style.change_done())
        by = pend.get("by")
        if by and by != me["name"]:
            r = next((x for x in P if x["name"] == by), None)
            if r: deliver(r, style.change_done())
        return
    if k == "wrapup":
        for x in P:
            if x["name"] != me["name"]: deliver(x, style.wrapped_up())
        deliver(me, style.wrapped_up())
        for r in P: M.setdefault(r["name"], {})["paused"] = True
        M[me["name"]]["pending"] = {"type": "wrapup_data"}; save_m()
        os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
        json.dump({"ended": time.strftime("%F %T %Z")}, open(features.ENDED, "w"))   # run_loop.sh exits on its next pass
        deliver(me, style.wrapup_data_offer()); return
    if k == "end_search":   # owner said a word yes: goodbye to everyone, stop the loop and listener, bot pauses its routines
        for x in P:
            if x["name"] != me["name"]: deliver(x, style.search_ended_note())
        deliver(me, style.search_ended_note())
        for r in P: M.setdefault(r["name"], {})["paused"] = True
        M[me["name"]]["pending"] = {"type": "wrapup_data"}; save_m()
        os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
        json.dump({"ended": time.strftime("%F %T %Z"), "reason": "end_my_search", "pause_routines": True}, open(features.ENDED, "w"))   # run_loop.sh exits; ensure_running.sh starts nothing
        print("PAUSE_ROUTINES (the bot pauses its own inbox-reader and health-check routines; not done from code)")
        deliver(me, style.photon_users_note())
        deliver(me, style.wrapup_data_offer()); return
    if k == "wrapup_data":
        if really and not sim: features.purge_all(everything=True)
        else: print("[sim] would delete the search data (replies, shortlist, members, state, logs)")
        json.dump({"ended": time.strftime("%F %T %Z"), "close_saved_searches": True}, open(features.ENDED, "w"))
        print("CLOSE_SAVED_SEARCHES (the agent closes the Zillow/Redfin/HotPads saved searches; not done from code)")
        deliver(me, style.wrapup_final(True)); stop_listener(); return

def target(text, latest, ctx_id):
    """Street named in the reply wins; else this person's last context (a relay they got); else the first place."""
    low = text.lower()
    named = [L for L in latest if L["where"].lower() in low]
    if named: return named[0]
    if ctx_id:
        hit = next((L for L in latest if L["id"] == ctx_id), None)
        if hit: return hit
        sl = load(SL, {})
        if ctx_id in sl: return {"id": ctx_id, "where": sl[ctx_id]["where"], "price": sl[ctx_id]["price"]}
    return latest[0] if latest else None

def react(rx, me, first, others, M):
    """iPhone tapback sent as text over SMS (Liked "...", Loved "...", ...). One short line to the others:
    'Sarah \u2764\ufe0f Maple St' (iMessage) or 'Sarah loved Maple St' (SMS/RCS). Removals are dropped silently.
    Not relayed as their words, not a command, no shortlist change, no ack."""
    emoji, word, quoted = rx
    if emoji == "remove": print("reaction removed; dropped silently"); return
    L = target(quoted or "", load(NUM, []), M.get(me["name"], {}).get("context"))
    where = L["where"] if L else None
    got = [o for o in others if deliver(o, style.reaction(first, emoji, word, where, chan(o) != "imessage"))]
    if not got: print(f"reaction from {me['name']} reached no one")

def main():
    if "--media-failed" in A:   # Photon couldn't forward a photo/voice note: say so, once, to the person who'd have got it
        import notify; ph = A[A.index("--media-failed") + 1]
        r = next((x for x in notify.recipients() if x.get("phone") == ph), None)
        if r: deliver(r, style.media_unsupported())
        return
    if sim: who, text = A[A.index("--as") + 1], A[A.index("--text") + 1]
    else:
        d = json.load(sys.stdin); text = d.get("text", "")
        who = next((r["name"] for r in people() if r.get("phone_last4") and d.get("from", "").endswith(r["phone_last4"])), None)
    P = people(); me = next((r for r in P if r["name"] == who), None)
    if not me: print("reply from someone not on the recipients list; ignored"); return
    M0 = load(MEM, {})
    if M0.get(me["name"], {}).get("left"): print("left the search; ignored"); return
    first = me["name"].split()[0]
    others = [r for r in P if r["name"] != me["name"] and r["role"] in ("owner", "co_decider")]
    owner = next(r for r in P if r["role"] == "owner")
    t = text.strip().lower().rstrip(".!")
    S, N, M = load(SL, {}), load(NUM, []), load(MEM, {})
    save_m = lambda: json.dump(M, open(MEM, "w"), indent=1)
    if me["role"] != "owner" and not M.get(me["name"], {}).get("joined"):
        # Her first text ("Hi Listing Scout, I'm in." or anything): received at once, like the owner's setup.
        import notify
        M.setdefault(me["name"], {})["joined"] = time.strftime("%F %T %Z"); save_m()
        if really and not sim:   # per-person channel at join (Photon SDK); a failed check assumes iMessage and never blocks
            live = {x["name"]: x for x in notify.recipients()}
            if me["name"] in live: notify.channel_of(live[me["name"]], refresh=True)
            M.clear(); M.update(load(MEM, {}))
        card = notify.card_for(me)
        deliver(me, style.member_welcome(first, owner["name"].split()[0], notify._sc().reflect(C), notify.KIND,
                                         me.get("role", "co_decider"), bool(C.get("replies")), bool(card)), card)
        deliver(owner, style.owner_member_in(first, me["role"], bool(C.get("replies"))))
        if really and not sim:   # snapshot a minute later, same as the owner's
            import subprocess
            subprocess.Popen(f'sleep 60 && python3 {"src/notify.py" if _IN_SRC else "notify.py"} snapshot "{me["name"]}" --send', shell=True, cwd=HERE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        else: print(f"(in 60s) --> to {me['name']}: snapshot, same as the owner's")
        return
    rx = style.parse_reaction(text)
    if rx: return react(rx, me, first, others, M)   # tapback text: never their own words, never a command or a like/pass
    owner_first = owner["name"].split()[0]
    if re.fullmatch(r"(stop|stopall|unsubscribe|cancel|end|quit)( please| now)?", re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", t)).strip()):   # carrier keywords: FIRST (punctuation/emoji ignored)
        mm = M.setdefault(me["name"], {}); mm.pop("pending", None)            # the waiting question is dropped; nothing is applied
        mm.update(paused=True, stopped=time.strftime("%F %T %Z")); save_m()   # no reply to them (instant opt-out)
        if me["role"] != "owner": deliver(owner, style.stopped_owner(first))
        return
    pend = M.get(me["name"], {}).get("pending")
    if pend:   # confirm-first: a question is waiting on this person's yes
        M[me["name"]].pop("pending"); save_m()
        if pend["type"] == "feedback_open":   # "Anything bugging you so far?": a no is fine; anything else goes into Make it better (still gated)
            if answer(text) == "no" or re.fullmatch(r"(nothing|all good|it'?s good|good|great|fine|nope)( so far)?( thanks)?", norm(text)):
                deliver(me, style.first_week_glad()); return
            if answer(text) is None:
                last = "alert" if load(os.path.join(HERE, "out", "last_sent.json"), {}).get("ts") else "welcome"
                M.setdefault(me["name"], {})["pending"] = {"type": "feedback", "payload": features.feedback_payload(text.strip(), last)}; save_m()
                deliver(me, style.feedback_ask(text)); return
            return
        ans = answer(text)
        if ans == "yes" and pend["type"] in ("purge", "wrapup_data", "end_search") and not re.fullmatch(WORD_YES, norm(text)): ans = None   # deleting data needs a word yes
        if ans == "yes": return do_pending(pend, me, P, M, owner, save_m)
        if ans == "no":
            if pend["type"] == "wrapup_data": deliver(me, style.wrapup_final(False)); stop_listener()
            elif pend["type"] == "feedback": deliver(me, style.feedback_dropped())
            elif pend["type"] != "sleep": deliver(me, style.no_change())
            return
        if pend["type"] == "wrapup_data": deliver(me, style.wrapup_final(False)); stop_listener(); return
        # anything else: the question lapses quietly and this text is handled as usual
    if features.is_feedback(text):   # Make it better: confirm first; only a clear yes sends it on
        last = "alert" if load(os.path.join(HERE, "out", "last_sent.json"), {}).get("ts") else "welcome"
        M.setdefault(me["name"], {})["pending"] = {"type": "feedback", "payload": features.feedback_payload(text.strip(), last)}; save_m()
        deliver(me, style.feedback_ask(text)); return
    if t in ("what do you keep", "what do you store", "my data", "privacy", "what data do you keep"):
        deliver(me, style.data_note()); return
    if re.fullmatch(r"(turn )?sleep mode( on)?|sleep mode please|hold (alerts|texts) overnight", t):
        M.setdefault(me["name"], {}).update(sleep=True, sleep_offered=True); save_m(); deliver(me, style.sleep_set(True, features.wake_label(C))); return
    if re.fullmatch(r"(turn )?sleep mode off|no sleep mode|alerts? right away", t):
        M.setdefault(me["name"], {}).update(sleep=False, sleep_offered=True); save_m(); deliver(me, style.sleep_set(False)); return
    if me["role"] == "owner":
        m_ = re.fullmatch(r"(?:please )?(?:remove|take) (\w+)(?: off(?: the search)?| from the search)?", t)
        who_ = next((r for r in P if m_ and r["role"] != "owner" and r["name"].split()[0].lower() == m_.group(1)), None)
        if who_:
            M.setdefault(me["name"], {})["pending"] = {"type": "remove", "name": who_["name"]}; save_m()
            deliver(me, style.remove_ask(who_["name"].split()[0])); return
        if re.fullmatch(r"(please )?(end|stop|cancel|close|finish) (my|our|the) (search|listing scout)( for good)?( please)?|end listing scout", t):
            M.setdefault(me["name"], {})["pending"] = {"type": "end_search"}; save_m(); deliver(me, style.end_ask()); return
        if t in ("delete everything", "delete all data", "delete my data", "delete our data", "delete the data"):
            M.setdefault(me["name"], {})["pending"] = {"type": "purge"}; save_m(); deliver(me, style.purge_ask()); return
    if re.search(style.STEER_RX, t) and re.search(r"\b(only|show|find|filter|search|want|need|looking|add|prefer|near|in a|area)\b", t):   # fair housing: never filter on or describe areas, schools or who lives there
        deliver(me, style.steer_note()); return
    if me["role"] in ("owner", "co_decider"):
        ch = features.parse_change(text, C)
        if ch and ch.get("unclear") and me["role"] == "owner": deliver(me, style.change_unclear()); return
        if ch and not ch.get("unclear"):
            om = M.setdefault(owner["name"], {})
            om["pending"] = {"type": "change", "change": ch, "by": me["name"]}; save_m()
            if me["role"] == "owner": deliver(me, style.change_ask(ch["desc"][0].upper() + ch["desc"][1:]))
            else:
                deliver(owner, style.change_suggested(first, text, ch["desc"][0].upper() + ch["desc"][1:]))
                deliver(me, style.change_passed(owner_first))
            return
    if t in ("ok", "okay", "k", "got it"):
        if me["role"] != "owner" and not M.get(me["name"], {}).get("ok"):
            M.setdefault(me["name"], {})["ok"] = time.strftime("%F %T %Z"); save_m()
            deliver(me, style.member_prefs(owner["name"].split()[0]))
        return
    if t.rstrip("?") in ("what can you do", "what do you do", "commands", "menu", "what can i say"):
        deliver(me, style.capabilities(me["role"] == "owner")); return
    if re.fullmatch(r"(no|stop|skip|turn off)( the)? check.?ins?( off)?|check.?ins? off", t):
        M.setdefault(me["name"], {})["no_checkins"] = True; save_m(); deliver(me, style.checkins_set(False)); return
    if re.fullmatch(r"(turn on |resume )?check.?ins?( on| back on)?", t):
        M.setdefault(me["name"], {}).pop("no_checkins", None); save_m(); deliver(me, style.checkins_set(True)); return
    if t in ("help", "?", "how"):
        o = others[0]["name"].split()[0] if len(others) == 1 else None
        deliver(me, style.how_replies_work(o, android=chan(me) in ("sms", "rcs"))); return
    if t in ("leave", "leave the search", "remove me"):
        deliver(me, style.left_member())   # say goodbye before marking them as left (deliver skips people who left)
        M.setdefault(me["name"], {}).update(left=time.strftime("%F %T %Z"), paused=True); save_m()
        features.purge_member(me["name"])   # their replies go with them (Your data stays put)
        if me["role"] != "owner": deliver(owner, style.left_owner(first))
        return
    if re.search(r"^(we )?found (one|a place|it|our place)\b|signed (the|a) lease|we got (it|the place)", t):
        om = M.setdefault(owner["name"], {}); om["pending"] = {"type": "wrapup"}; save_m()   # only the owner's yes ends it
        if me["role"] == "owner": deliver(me, style.found_ask())
        else: deliver(owner, style.found_relay(first, text)); deliver(me, style.change_passed(owner_first))
        return
    if t in ("pause", "resume", "start"):
        on = t in ("resume", "start"); M.setdefault(me["name"], {})["paused"] = not on
        if on: M[me["name"]].pop("stopped", None)
        save_m()
        deliver(me, style.paused_text(on))
        if me["role"] != "owner": deliver(owner, style.text([[f"{first} {'resumed' if on else 'paused'} their texts."]]))
        return
    if me["role"] == "in_the_know":
        o = owner["name"].split()[0]
        for x in [owner]: deliver(x, style.relay(first, (target(text, N, None) or {"where": "a listing"})["where"], text))
        if not M.get(me["name"], {}).get("replied"):
            M.setdefault(me["name"], {})["replied"] = True; save_m(); deliver(me, style.passed_to(o))
        return
    if t == "shortlist":
        items = []
        for lid, v in S.items():
            if not (v.get("likes") or v.get("tour")): continue
            lk = sorted(set(v.get("likes", [])))
            note = "you both like it" if len(lk) >= 2 else (f"{lk[0]} likes it" if lk else "")
            if v.get("tour"): note = (note + ", " if note else "") + "tour asked"
            items.append((v["where"], v["price"], note))
        deliver(me, style.shortlist(items)); return
    if sim and "--kind" in A: kind = A[A.index("--kind") + 1]
    else: kind = (d.get("kind") if not sim else None) or "text"
    L = target(text, N, M.get(me["name"], {}).get("context"))
    if not L: deliver(me, style.which_one()); return
    meta = load(os.path.join(HERE, "out", "last_sent.json"), {})
    named = any(x["where"].lower() in t for x in N)
    if (not named and meta.get("prev") and time.time() - meta.get("ts", 0) < 1800 and not M.get(me["name"], {}).get("context")
            and meta.get("ts", 0) > M.get(me["name"], {}).get("asked_ts", 0)):
        M.setdefault(me["name"], {})["asked_ts"] = time.time(); save_m()   # ask which place, once per new alert
        deliver(me, style.which_one()); return
    if kind in ("photo", "voice", "attachment"):
        for o in others: deliver(o, style.media_relay(first, L["where"], "voice note" if kind == "voice" else "photo"))
        if really and not sim:
            import notify; live = {x["name"]: x["phone"] for x in notify.recipients()}
            print("FORWARD_MEDIA " + json.dumps([live[o["name"]] for o in others if o["name"] in live]))   # listen.mjs forwards it as is
        else: print("[sim] would forward the media as is to", [o["name"] for o in others])
        return
    act = "tour" if re.search(TOUR, t) else "pass" if re.search(NO, t) else "like" if re.search(YES, t) else "note"
    e = S.setdefault(L["id"], {"where": L["where"], "price": L.get("price"), "likes": [], "pass": [], "tour": [], "notes": []})
    if act != "note":
        for k in ("likes", "pass", "tour"):
            if first in e[k]: e[k].remove(first)
        e["likes" if act == "like" else act].append(first)
        if act == "tour": e["likes"].append(first)
    e["notes"].append([first, text, time.strftime("%F %T %Z")])
    json.dump(S, open(SL, "w"), indent=1)
    both = act in ("like", "tour") and len(set(e["likes"])) >= 2 and not e.get("mutual_sent")
    if both: e["mutual_sent"] = True; json.dump(S, open(SL, "w"), indent=1)
    w = L["where"]
    for o in others:   # the other person's next plain reply attaches to this place
        M.setdefault(o["name"], {})["context"] = L["id"]
    save_m()
    # Acks: one warm "Passed that to X." after someone's very first reply; later, only tours get one.
    first_reply = not M.get(me["name"], {}).get("replied")
    if first_reply: M.setdefault(me["name"], {})["replied"] = True; save_m()
    got = [o for o in others if deliver(o, style.relay(first, w, text))]   # the relay itself teaches that replies travel
    if not got: print(f"WARNING: reply from {me['name']} reached no one (no other active members); no ack sent")
    fn = [o["name"].split()[0] for o in got]
    names = fn[0] if len(fn) == 1 else (", ".join(fn[:-1]) + " and " + fn[-1] if fn else "")
    other1 = names if len(f"Passed that to {names}.") <= 30 else "everyone"
    if act == "tour":
        deliver(me, style.saved(w))
        for o in others: deliver(o, style.tour_note(first, w, o["role"] == "owner"))
    elif first_reply and not both and got:
        deliver(me, style.passed_to(other1))
    if both:   # the 'aha' moment: first mutual yes on a place
        for o in [me] + others: deliver(o, style.mutual(w))

if __name__ == "__main__": main()
