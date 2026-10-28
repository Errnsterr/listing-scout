import os
"""Listing Scout text style: the ONE formatter for every text a person receives.
Rules (calm style):
- one sentence per line; blocks separated by one blank line
- a sentence must fit on ONE line (<= 30 chars, an iPhone screen). Never wrap. Write shorter instead.
- links always alone on their own line
- headlines: "New place that fits" etc. (no emoji in any text); close: "No rush. I'll keep watching."
Use: style.text([block, block, ...]) where each block is a str or list of str.
"""
import math, re

MAX = 30
URL = re.compile(r"(?:https?://|sms:)\S+")   # web links and sms: tap-to-text links (exempt from MAX, own line)
SENT = re.compile(r"(?<!^\d\.)(?<!\s\d\.)(?<!^\d\d\.)(?<=[.!?])\s+(?=[A-Z\"'(])")
CLOSE = "No rush. I'll keep watching."

def sentences(line):
    """split a line into sentences; URLs become their own lines."""
    out = []
    for part in re.split(r"\s*((?:https?://|sms:)\S+)\s*", line):
        if not part: continue
        if URL.fullmatch(part): out.append(part); continue
        out += [s.strip() for s in SENT.split(part) if s.strip()]
    return out

def _greedy(words, w):
    lines, cur = [], ""
    for x in words:
        if cur and len(cur) + 1 + len(x) > w: lines.append(cur); cur = x
        else: cur = f"{cur} {x}" if cur else x
    if cur: lines.append(cur)
    return lines

def wrap(s, width=MAX):
    """balanced wrap with no single-word lines (when the sentence has 2+ words)."""
    if URL.fullmatch(s) or len(s) <= width: return [s]
    if ", " in s:                        # prefer a natural break at a comma
        best = None
        for m in re.finditer(r", ", s):
            a, b = s[:m.start() + 1], s[m.end():]
            if len(a) <= width and len(b) <= width and len(a.split()) > 1 and len(b.split()) > 1:
                d = abs(len(a) - len(b))
                if best is None or d < best[0]: best = (d, [a, b])
        if best: return best[1]
    words = s.split()
    k = math.ceil(len(s) / width)
    for lines_wanted in (k, k + 1):
        for w in range(math.ceil(len(s) / lines_wanted), width + 1):
            ls = _greedy(words, w)
            if len(ls) == lines_wanted and all(len(l.split()) > 1 for l in ls):
                return ls
    ls = _greedy(words, width)          # fallback: fix orphan by moving words down
    for i in range(len(ls) - 1, 0, -1):
        if len(ls[i].split()) == 1 and len(ls[i - 1].split()) > 2:
            a = ls[i - 1].rsplit(" ", 1); ls[i - 1], ls[i] = a[0], f"{a[1]} {ls[i]}"
    return ls

class StyleError(ValueError): pass

class Group(list):
    """lines that stay together with no blank lines: alert fact groups,
    numbered steps (with their intro line), an address with its link."""

class Quote(str):
    """A person's own words, verbatim, in quotes. Never reworded; long ones wrap inside the quote."""

def quote(words):
    """A person's own words, exactly as written, in quotes. Only outer whitespace is trimmed.
    No wrapping, no line breaks added, no length limit, no style rules (check() exempts it)."""
    return Quote('"' + (words or "").strip() + '"')

FACT_LABEL = re.compile(r"^(Working so far|Pets|Garage|Layout|HOA|Price|Move-in date|Rent|Beds|Baths|Address|Link|Sq ft):\s")   # stay on one line

def _colon_break(s_):
    """'2. Text it: Hi Listing Scout, I'm in.' -> '2. Text it:\nHi Listing Scout, I'm in.'"""
    if URL.fullmatch(s_) or FACT_LABEL.match(s_): return s_
    m = re.search(r":\s+(?=\S)", s_)
    if not m or URL.match(s_[m.end():]): return s_
    return s_[:m.start() + 1] + "\n\n" + s_[m.end():]   # blank line after a colon

def _lines(ln):
    out = []
    for s_ in sentences(ln):
        for part in _colon_break(s_).split("\n"):
            if not URL.fullmatch(part) and len(part) > MAX and re.search(r"[.!?]$", part):
                raise StyleError(f"sentence too long ({len(part)}), rewrite shorter: {part!r}")
        out += _colon_break(s_).split("\n\n")
    return out

def text(blocks):
    """Every sentence is its own block (blank line after it). Never wraps.
    A Group keeps its lines together. Over-long sentences raise StyleError."""
    out = []
    for b in blocks:
        if isinstance(b, Quote): out.append(str(b)); continue
        if isinstance(b, Group):
            ls = [x for ln in b for x in _lines(ln)]
            if not ls: continue
            # an intro line ending in ':' gets a blank line before its list (links stay right under)
            if ls[0].endswith(":") and "\n" not in ls[0] and len(ls) > 1 and not URL.fullmatch(ls[1]):
                out.append(ls[0]); ls = ls[1:]
            # numbered steps each get their own block (blank line between steps)
            cur = []
            for j, x in enumerate(ls):
                if re.match(r"^\d+\.", x) and cur: out.append("\n".join(cur)); cur = []
                cur.append(x)
                nxt = ls[j + 1] if j + 1 < len(ls) else None
                if x.endswith(":") and nxt and not URL.fullmatch(nxt):   # blank line after a colon
                    out.append("\n".join(cur)); cur = []
            if cur: out.append("\n".join(cur))
            continue
        for ln in ([b] if isinstance(b, str) else b):
            for x in _lines(ln):
                if URL.fullmatch(x) and out: out[-1] += "\n" + x   # link sits under its line
                else: out.append(x)
    return "\n\n".join(out)

def _bot_blocks(blocks):
    """Drop quoted relay bodies (from a block starting with '"' to the block ending with '"')."""
    out, inq = [], False
    for b in blocks:
        if not inq and b.startswith('"'):
            inq = not (len(b) > 1 and b.endswith('"'))
            continue
        if inq:
            if b.endswith('"'): inq = False
            continue
        out.append(b)
    return out

def check(msg, width=MAX):
    """return list of style problems (used by tests and before every send)."""
    probs = []
    blocks = msg.split("\n\n")
    for k, b in enumerate(_bot_blocks(blocks)):   # a line ending in ':' needs a blank line after it (a link may sit right under)
        ls = b.split("\n")
        for i, ln in enumerate(ls):
            if ln.endswith(":") and not FACT_LABEL.match(ln) and i + 1 < len(ls) and not URL.fullmatch(ls[i + 1]):
                probs.append(f"blank line needed after colon: {ln!r}")
    msg = "\n\n".join(_bot_blocks(blocks))   # a relayed quote is the person's own words: never checked
    ML = msg.split("\n")
    for i, ln in enumerate(ML):
        if not ln or URL.fullmatch(ln): continue
        if URL.search(ln): probs.append(f"link not alone: {ln!r}")
        labels_link = i + 1 < len(ML) and URL.fullmatch(ML[i + 1]) and not ln.endswith(":")   # a street address labeling its link stays whole
        if len(ln) > width and not labels_link: probs.append(f"too long ({len(ln)}): {ln!r}")
        if re.fullmatch(r"\d+\.", ln.strip()): probs.append(f"list number alone: {ln!r}")
        if len(SENT.split(ln)) > 1: probs.append(f"two sentences on one line: {ln!r}")
    for b in msg.split("\n\n"):
        ls = [l for l in b.split("\n") if l and not URL.fullmatch(l)]
        for i in range(1, len(ls)):   # a line starting lowercase continues the previous line's sentence
            if re.match(r"^[a-z]", ls[i]):
                probs.append(f"sentence spans lines: {ls[i-1]!r} / {ls[i]!r}")
    for ln in msg.split("\n"):    # after a colon, return a line (fact labels excepted for now)
        if not URL.search(ln) and not FACT_LABEL.match(ln) and re.search(r":\s+\S", ln):
            probs.append(f"text after a colon must go on the next line: {ln!r}")
    for b in msg.split("\n\n"):
        ls = b.split("\n")
        for k in range(len(ls) - 1):
            if ls[k].endswith(":") and re.match(r"^\d+\.", ls[k + 1]):
                probs.append(f"intro line needs a blank line before its list: {ls[k]!r}")
        for k in range(len(ls) - 1):   # numbered steps need a blank line between them
            if re.match(r"^\d+\.", ls[k + 1]) and k >= 0 and any(re.match(r"^\d+\.", l) for l in ls[:k + 1]):
                probs.append(f"numbered steps need a blank line between them: {ls[k + 1]!r}")
        for k in range(len(ls) - 1):   # a full sentence must be followed by a blank line
            cur, nxt = ls[k], ls[k + 1]
            if re.search(r"[.!?]$", cur) and not URL.fullmatch(nxt) and not re.match(r"^\d+\.", cur) \
               and not re.match(r"^\d+\.", nxt) and not cur.endswith(":"):
                probs.append(f"sentence not followed by blank line: {cur!r}")
    for b in msg.split("\n\n"):   # unknowns: one wording, and always last in their block
        ls = [l for l in b.split("\n") if l and not URL.fullmatch(l)]
        for i, l in enumerate(ls):
            if ("not listed" in l.lower() or "not available" in l.lower()) and l != UNKNOWN_NORMAL_LINE:   # the welcome heads-up is the one exempt line
                if not re.fullmatch(r"[A-Z][\w ,'/-]*: not listed yet", l):
                    probs.append(f"unknown wording should be 'X: not listed yet': {l!r}")
                later = [x for x in ls[i + 1:] if "not listed yet" not in x]
                if later: probs.append(f"unknowns go last: {l!r} before {later[0]!r}")
    for ln in msg.split("\n"):
        if re.search(r"[.!?]\s*[\U0001F300-\U0001FAFF]", ln): probs.append(f"no period before an emoji (heading style): {ln!r}")
        if re.search(r"\bjust say (resume|pause)\b|\bsay resume\b", ln, re.I): probs.append(f"use 'Resume works whenever you're ready.' wording: {ln!r}")
        if re.search(r"\brented\b", ln, re.I): probs.append(f"never say rented (we can't know); say 'no longer listed': {ln!r}")
        if re.search(r"\b(free plan)\b", ln): probs.append(f"plan names are capitalized (Free): {ln!r}")
    if "\n\n\n" in msg: probs.append("more than one blank line between blocks")
    return probs

# ---------- templates (all end-user texts) ----------
# Header wording and the colon rule:
# a sentence with text after a colon fails check(). Write headers as plain sentences
# ("This is a sample, not a new listing.") or end the line with the colon and put the rest
# on the next line, after a blank line. Only fact labels (Pets:, Garage:, Rent:...) keep text after ':'.
# Tone: never instruct people to reply. Replying is offered as a gentle option, never a command.
# No 'Reply ...' lines; the first-text receipt is soft ('Did this come through okay?').

FIRST_TEXT = '"Hi Listing Scout, I\'m in."'
UNKNOWN = "not listed yet"

# Every bot line below is a whole thought of 30 characters or fewer (MAX). Names are filled in per user;
# when a name would push a line past MAX, the line falls back to wording without the name (fit()).

FIRST_TEXT = '"Hi Listing Scout, I\'m in."'
UNKNOWN = "not listed yet"

BUYING_NEW_LINE = "Buying is still new."   # buy mode is experimental: both welcomes say so
BUY_LINE = "Not an agent or advice."        # buy mode only: not a real estate agent, not financial advice (DISCLAIMER.md)
SAFETY_LINE = "See it before paying anything."     # disclaimer, one line, in the welcome (see DISCLAIMER.md)
FEEDBACK_LINE = "Spot a bug, just let me know."   # Make it better: mentioned once, in the welcome
RECEIPT = "Did this come through okay?"
APPLY_LINE = "Text apply on one you like."
APPLY_YES_LINE = "Nothing goes out before a yes."   # "Nothing goes out without your yes." is 34 chars, over the 30-char line rule   # Apply for me (rentals): the bot fills it, nothing goes without a yes
AGE_LINE = "By staying in, you're 18+."   # both welcomes, right before STOP (text-first opt-in)
STOP_LINE = "Text STOP anytime to stop."   # members are told once, in their welcome (SMS consent norm)
CHECKINS_LINE = "Text no check-ins to skip."   # opt-out for quiet-week / first-week / near-miss check-ins   # the soft receipt, re-split to fit 30 characters
UNKNOWN_NORMAL_LINE = "Not listed yet is normal."   # heads-up in both welcomes: listings often skip details
CREDIT_LINE = "Built by @errnsterr"   # public credit, last line of "what can you do"
DUPES_LINE = "Each home shows up once."             # heads-up in both welcomes: the same home can come from two sites
ANDROID_LINES = ["Emoji may show as words.", "Reactions may too.", "That's just Android."]   # help only, SMS/RCS people

def proven_sites(here=None):
    """Alert-email sites proven by a real parsed alert (out/sources_proven.json), in the order they were proven.
    Config-driven: nothing is hardcoded; scout.py records each site the first time one of its emails parses."""
    import json as _j
    if here is None:
        _src = os.path.dirname(os.path.abspath(__file__))
        here = os.path.dirname(_src) if os.path.basename(_src) == "src" else _src
    f = os.path.join(here, "out", "sources_proven.json")
    try: d = _j.load(open(f))
    except Exception: return []
    return sorted(d, key=lambda k: str(d[k].get("first", ""))) if isinstance(d, dict) else []

def proven_lines(sites):
    if not sites: return [["Sites are still warming up."]]
    names = sites[0] if len(sites) == 1 else ", ".join(sites[:-1]) + " and " + sites[-1]
    t = f"Working so far: {names}."
    return [[t]] if len(t) <= MAX else [Group(["Working so far:", names + "."])]

def first_alert_note():
    """One-time note, sent once per person right after their first real alert (flag: first_alert_note_sent)."""
    return text([["Quick note on that one."], ["Missing details say so."], ["The site didn't list them."],
                 ["Links open the listing itself."]])

def fit(line, fallback):
    """The line with a person's name if it fits on one iPhone line, else the nameless fallback."""
    return line if len(line) <= MAX else fallback

def owner_welcome(first, n, card=False, kind="rental"):
    """Owner's first text. Merged test + welcome: one soft receipt."""
    b = [fit(f"Hi {first}!", "Hi!"), "It's Listing Scout."]   # trimmed "You're all set." to make room for STOP
    if card: b.append("Tap the card to save me.")
    b += [fit(f"I'm watching {n:,} places.", "I'm watching for you."), "Quiet days mean nothing fit.",
          SAFETY_LINE, UNKNOWN_NORMAL_LINE, DUPES_LINE] + ([BUYING_NEW_LINE, BUY_LINE] if kind == "home" else [APPLY_LINE]) + [AGE_LINE, STOP_LINE, FEEDBACK_LINE, RECEIPT]
    return text(b)


def first_day(n):
    """One-time note on day one if nothing new fit (capped: sent at most once, ever)."""
    return text([fit(f"I checked {n:,} places today.", "I checked every place today."), "Nothing new fit yet.",
                 "That's normal on day one.", CLOSE])

FIRST_TEXT_RAW = "hi"  # suggested only; any first text works

def sms_link(to="", body=""):
    """iOS-compatible tap-to-text link: sms:<to>&body=<urlencoded>. Empty `to` = pick a contact.
    Everything is percent-encoded (spaces %20, comma %2C, apostrophe %27, newline %0A) so iOS keeps it intact."""
    from urllib.parse import quote as q
    to = re.sub(r"[^\d+]", "", to or "")
    return f"sms:{to}&body={q(body, safe='')}"

def join_link(line):
    """Member side: their own Listing Scout line (the bot's number, never theirs), first text prefilled."""
    return sms_link(line, FIRST_TEXT_RAW)

def fmt_phone(line):
    """+15551234567 -> (555) 123-4567 (iPhone auto-links it). Other shapes pass through."""
    d = "".join(c for c in (line or "") if c.isdigit())
    if len(d) == 11 and d[0] == "1": d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else (line or "")

def invite(first, kind="rental", line=None):
    """Household invite: a plain, forwardable text with no URLs. Privacy: no third-party page ever sees
    who is invited. iPhone auto-links the number. The welcome reply carries the contact card."""
    return text([[fit(f"Hi {first}!", "Hi!"),
                  "I set up Listing Scout for us.",
                  "It texts us homes that fit.",
                  "Tap the number to say hi:"],
                 [fmt_phone(line) if line else "(000) 000-0000"]])

def owner_invite_intro(name, channel="imessage"):
    """Bot -> owner, sent just before the invite text, which the owner forwards.
    The forwarding steps follow the OWNER's phone: iPhone (iMessage) or Android (SMS/RCS)."""
    steps = [["Press and hold it."], ["Tap More, then the arrow."]] if channel == "imessage" else \
            [["Press and hold it."], ["Tap the menu, then Forward."]]
    return text([[fit(f"Here's {name}'s invite.", "Here's the invite.")],
                 [fit(f"Forward the next text to {name}.", "Forward the next text.")]] + steps + [
                 [fit(f"Pick {name} and press Send.", "Pick them and press Send.")]])

def owner_invite_link(invite_text):
    """Internal fallback only (never texted): sms: link with no recipient and the invite prefilled."""
    return sms_link("", invite_text)

def hint_target_not_allowed(name, line4):
    return text([[fit(f"My text to {name} didn't go.", "My text didn't go through.")],
                 ["Nothing is wrong on their end."], ["Their line isn't open yet."],
                 [fit(f"Please ask {name} to text it.", "Please ask them to text it.")],
                 [f"It's the number ending {line4}."], ["Any text works, like \"hi\"."],
                 ["Then I'll try again."]])

VCARD_NOTE = "Your quiet home hunter"   # the card subheader, rent or buy

# ---------- case B: sharing your search with a co-decider or someone "in the know" ----------
def _offer(other):
    """'Decide together': the feature, as a benefit, once (only when replies are on)."""
    return [["We can decide together here."], ["Tell me what you think of one."],
            [fit(f"I'll share it with {other}.", "I'll share it with them.")], ["I'll keep a shared shortlist."]]

def member_welcome(first, owner, search_lines, kind="rental", role="co_decider", replies=False, card=False):
    """Member's first text (= their receipt). Names who invited them and reflects the shared search."""
    b = [[fit(f"Hi {first}!", "Hi!")], ["It's Listing Scout."],
         [fit(f"{owner} said you'd stop by.", "I've been expecting you.")]]
    if card: b.append(["Tap the card to save me."])
    b += [Group(["Here's what we're looking for:"] + search_lines)]
    b.append([fit(f"You get {owner}'s alerts too.", "You'll get the same alerts.")])
    if replies and role == "co_decider": b += [["We can decide together here."],
                                               ["Tell me what you think of one."],
                                               [fit(f"I'll share it with {owner}.", "I'll share it with them.")]]
    elif replies:
        b.append([fit(f"I'll pass your thoughts to {owner}.", "I'll pass your thoughts on.")])
    b += [[SAFETY_LINE], [UNKNOWN_NORMAL_LINE], [DUPES_LINE]] + ([[BUYING_NEW_LINE], [BUY_LINE]] if kind == "home" else []) + [[AGE_LINE], [STOP_LINE], [RECEIPT]]   # trimmed FEEDBACK_LINE (owner welcome keeps it) to fit the 18+ line
    return text(b)

def _commands(apply_=True, change_=True, owner=False):
    """The one command list (help and 'what can you do', owner and member alike). Only what replies.py handles."""
    b = [["Text me your thoughts."], ["Text shortlist for picks."]]
    if apply_: b.append(["Text apply to start one."])   # rentals, owner/co-decider only
    if change_: b.append(["Text a change to the search."])   # owner decides; a co-decider's idea goes to the owner
    b += [["Text pause or resume anytime."], ["Text leave to get off."]]
    if owner: b.append(["Text end my search to end."])
    b += [[STOP_LINE], ["I never contact landlords."]]   # the one STOP wording, same as the welcomes
    return b

def how_replies_work(other=None, android=False, apply_=True, change_=True, owner=False):
    """Only on 'help' (never advertised)."""
    p = fit(f"I'll pass your words to {other}.", "I'll pass your words along.") if other else "I'll pass your words along."
    return text([[p], ["Naming the street helps."]] + _commands(apply_, change_, owner) + ([[x] for x in ANDROID_LINES] if android else []))

def capabilities(owner=False, sites=None, apply_=True, change_=False):
    """Reply to 'what can you do' (anyone). Plain, honest, nothing unbuilt."""
    b = [["I text new places that fit."]] + _commands(apply_, change_ or owner, owner)
    b += proven_lines(proven_sites() if sites is None else sites) + [["The next step is always yours."], [CREDIT_LINE]]
    return text(b)

def checkins_set(on):
    return text([["Okay, check-ins are back on."]] if on else [["Okay, no more check-ins."], ["Alerts keep coming as usual."]])

def member_prefs(owner):
    """Choices the member can ask the owner for. (A daily summary stays hidden until it's built.)"""
    return text([["This can fit you, too."],
                 Group([fit(f"{owner} can set it up if you like:", "Just ask if you'd like:"),
                        "1. Only target-range places.",
                        "2. Alerts without replies."]),
                 ["Text pause if it gets busy."]])

def owner_member_in(name, role="co_decider", replies=False):
    b = [[fit(f"{name} is in.", "They're in.")], [fit(f"{name}'s texts are set up.", "Their texts are set up.")],
         [fit(f"{name} gets your alerts too.", "They get your alerts too.")]]
    if replies and role == "co_decider": b += _offer(name)
    return text(b)

def owner_nudge(name):
    """One time, if a member hasn't texted within about a day."""
    return text([[fit(f"{name} hasn't texted me yet.", "They haven't texted me yet.")], ["No rush."], ["Want me to resend the invite?"]])

def shorten(where, room):
    """The street as people say it (no house number, no 'Avenue'), or None if it can't fit whole.
    Never cuts a name mid-way; callers fall back to wording without the street."""
    w = re.sub(r"^\s*[\d\-A-Za-z]*\d[\w\-]*\s+", "", where or "").strip()
    w = re.sub(r"\s+(Avenue|Ave|Drive|Dr|Street|St|Road|Rd|Lane|Ln|Boulevard|Blvd|Way|Place|Pl|Court|Ct)\.?$", "", w, flags=re.I).strip()
    if where and len(where) <= room: return where
    ws = w.split()   # drop trailing words only (never the first), so the street is never lost
    while ws and len(" ".join(ws)) > room and len(ws) > 1: ws = ws[:-1]
    return " ".join(ws) if ws and len(" ".join(ws)) <= room else None

def relay(name, where, words):
    """Their own words, verbatim and quoted, under 'Alex on Main:' (blank line after the colon).
    The relay itself is the teaching moment: no instructions."""
    w = shorten(where, MAX - len(f"{name} on :"))
    return text([[f"{name} on {w}:" if w else fit(f"{name} replied:", "A reply came in:")], quote(words)])

def mutual(where):
    w = shorten(where, MAX - len("You both like ."))
    return text([[f"You both like {w}." if w else "You both like this one."], ["It's on your shortlist."]])

def tour_note(name, where, to_owner):
    w = shorten(where, MAX - len(f"{name} wants to tour ."))
    b = [[f"{name} wants to tour {w}." if w else fit(f"{name} wants to tour it.", "A tour was asked for.")], ["It's on your shortlist."]]
    if to_owner: b += [["I won't contact anyone."], ["The next step is yours."]]
    return text(b)

def passed_to(other):
    """One-time confirmation after someone's very first reply."""
    return text([[fit(f"Passed that to {other}.", "Passed that along.")]])

def saved(where):
    w = shorten(where, MAX - len("Saved ."))
    return text([[f"Saved {w}." if w else "Saved it."], ["It's on your shortlist."]])

def shortlist(items):
    """items: [(where, price_str, note)]; note e.g. 'you both like it' or ''."""
    if not items: return text([["Your shortlist is empty."], ["Places you both like go here."]])
    lines = ["Your shared shortlist:"]
    for k, (w, p, note) in enumerate(items, 1):
        lines += [f"{k}. {w}", p] + ([note[0].upper() + note[1:]] if note else [])
    return text([Group(lines)])

def which_one():
    return text([["Which place do you mean?"], ["Naming the street helps."]])

def paused_text(on):
    return text([["Welcome back."], ["Text pause anytime."]] if on else
                [["Got it, texts are paused."], ["Text resume anytime."]])

# ---------- edge cases ----------
def stopped_owner(name):
    return text([[fit(f"{name} turned off texts.", "Someone turned off texts.")], ["I'll stay quiet for them."],
                 ["They can text START anytime."]])

def left_owner(name):
    return text([[fit(f"{name} left the search.", "Someone left the search.")], ["Their texts have stopped."]])

def left_member():
    return text([["You're off the search now."], ["Thanks for helping look."]])

def found_ask():
    """Owner only: only the owner's yes ends the search."""
    return text([["That's wonderful news!"], ["Want me to wrap up the search?"]])

def found_relay(name, words):
    """A co-decider said they found it: their words verbatim, then the owner decides."""
    return text([[fit(f"{name} wrote:", "A note came in:")], quote(words), ["Want me to wrap up the search?"]])

def wrapped_up():
    return text([["Congrats on the new place!"], ["The search is wrapped up."], ["No more listing texts from me."]])

# ---------- Take a break (removing someone; STOP stays instant and silent) ----------
def remove_ask(name):
    return text([[fit(f"Take {name} off the search?", "Take them off the search?")]])

def removed_owner(name):
    return text([[fit(f"{name} is off the search.", "They're off the search.")], ["I deleted their replies too."]])

# ---------- Sleep mode (off by default; offered once, after a late alert) ----------
def sleep_offer(when):
    return text([[fit(f"That last one came at {when}.", "That last one came in late.")],
                 ["Overnight finds can wait."], ["They'd come at 7 AM instead."], ["Want me to?"]])

def sleep_set(on, wake="7 AM"):
    return text([["Sleep mode is on."], [fit(f"Night finds come at {wake}.", "Night finds come in the morning.")]] if on else
                [["Sleep mode is off."], ["Alerts come right away."]])

# ---------- Still available? (only places someone liked; never 'rented') ----------
def gone_note(where):
    w = shorten(where, MAX - len("Heads up on :"))
    return text([[f"Heads up on {w}:" if w else "Heads up on a saved place:"], ["It's no longer listed."],
                 ["I'll say if it comes back."]])

# ---------- Fine-tune the search (read back, apply only on the owner's yes) ----------
def change_ask(change):
    """change: one short line in plain words, e.g. 'add 78745 to the search.'"""
    return text([["Got it:"], [change], ["Want me to make that change?"]])

def change_suggested(name, words, change):
    """A co-decider's idea, verbatim, then the read-back for the owner to decide."""
    return text([[fit(f"{name} suggested:", "A suggestion came in:")], quote(words), [change], ["Want me to make that change?"]])

def change_done():
    return text([["Done, the search is updated."], ["New matches start from now."]])

def change_unclear():
    return text([["I'm not sure what to change."], ["Could you say it another way?"]])

def change_passed(owner):
    return text([[fit(f"I passed that to {owner}.", "I passed that along.")], [fit(f"{owner} gets the final say.", "The owner gets the final say.")]])

def no_change():
    return text([["Okay, nothing changed."]])

# ---------- Quiet-week pulse, daily cap, first-week ask, listener note ----------
def quiet_week(n):
    """After a silent week only; n = real places checked (None = no count line)."""
    b = [["Quiet week, still watching."]]
    if n: b.append([fit(f"I checked {n:,} places.", "I checked every source.")])
    b.append(["Nothing new fit yet."]); b.append([CHECKINS_LINE])
    return text(b)

def evening_bundle_intro(n, kind="rental"):
    if kind == "home":
        s = "home" if n == 1 else "homes"
        return text([[fit(f"Today's roundup, {n} {s}:", "Today's roundup:")]])
    s = "find" if n == 1 else "finds"
    return text([[fit(f"Today's other {n} {s}:", "Today's other finds:")]])

def off_market(where, status):
    """A shortlisted home went pending or sold: one calm note, only to the people who shortlisted it."""
    w = shorten(where, MAX - len("Heads up on :"))
    word = "It sold." if status == "sold" else "It's now pending."
    return text([[f"Heads up on {w}:" if w else "Heads up on a saved home:"], [word], ["I'll keep watching."]])

def first_week_ask():
    return text([["A few days in."], ["Anything bugging you so far?"], [CHECKINS_LINE]])

def first_week_glad():
    return text([["Glad it's working well."]])

def listener_note():
    return text([["Replies paused for a moment."], ["They're working again now."]])

# ---------- Criteria hygiene (one plain question at a time; confirm-first) ----------
THINGS = {"garage": "a garage", "layout": "ground floor", "price": "price", "beds": "beds", "baths": "baths", "pets": "pet rules"}

def must_or_nice_q(thing):
    w = {"garage": "Is a garage a must-have?", "layout": "Is ground floor a must-have?"}.get(thing, f"Is {thing} a must-have?")
    return text([[w], ["Or just nice to have?"]])

def tradeoff_text(counts):
    """counts: (as_must_have, as_nice_to_have) from real listings, or None."""
    if not counts: return text([["I can't count that one yet."], ["Either way works for now."]])
    m, n = counts
    return text([["Here's the trade-off today:"], [fit(f"As a must-have, about {m} fit.", f"Must-have: about {m} fit.")],
                 [fit(f"As a nice-to-have, about {n}.", f"Nice-to-have: about {n}.")]])

def near_miss_ask(n, thing, change):
    """change: the exact one-line change a yes applies, e.g. 'Set your stretch to $5,200.'"""
    w = THINGS.get(thing, thing); s = "place" if n == 1 else "places"
    return text([[fit(f"{n} {s} missed only on {w}.", f"{n} {s} were close this week.")],
                 ["To see places like these:"], [change], ["Want me to make that change?"]])

def loosen_ask(change):
    return text([["No new matches in a week."], ["Loosening one thing may help:"], [change], ["Want me to make that change?"]])

def tighten_ask(change):
    return text([["Lots of matches lately."], ["One change could trim them:"], [change], ["Want me to make that change?"]])

# ---------- Your data stays put ----------
def data_note():
    return text([["Replies stay while we search."], ["When it ends, I delete them."], ["Only Photon sees the texts."]])

def purge_ask():
    return text([["Delete all the search data?"], ["This can't be undone."]])

def purge_done():
    return text([["Done, it's all deleted."]])

def end_ask():
    return text([["End your search for good?"], ["Everyone gets one goodbye."], ["Then no more texts."], ["Text yes to end it."]])

def search_ended_note():
    return text([["This search has ended."], ["No more listing texts from me."], ["Thanks for searching with me."]])

def photon_users_note():
    return text([["One last step is yours."], ["Open Photon's Users page."], ["Remove each person there."]])

def wrapup_data_offer():
    return text([["I can clear our search data."], ["And close the saved searches."], ["Want me to?"]])

def wrapup_final(cleared):
    return text([["Done, it's all cleared."] if cleared else ["Okay, I'll keep it for now."], ["Thanks for searching with me."]])

def media_relay(name, where, kind="photo"):
    w = shorten(where, MAX - len(f"{name} sent a {kind} of ."))
    return text([[f"{name} sent a {kind} of {w}." if w else fit(f"{name} sent a {kind}.", f"A {kind} came in.")]])

def media_unsupported(kind="photo"):
    s_ = f"I can't pass a {kind} on yet."
    return text([[s_ if len(s_) <= MAX else "I can't pass that on yet."], ["Words come through fine."]])

def outage_note(source, since):
    return text([[fit(f"{source} is quiet today.", "One site is quiet today.")], ["I'll keep checking it."],
                 ["Your other sites are fine."]])

def full_household(n=None):
    """Only when the owner set photon.user_limit (their plan's limit; see photon.codes/pricing)."""
    return text([[fit(f"Your search has {n} people.", "Your search is full.") if n else "Your search is full."],
                 ["That's your plan's limit."], ["To add someone, remove one."]])

STEER_RX = r"\b(safe|safer|safest|crime|good schools?|school district|best schools?|no kids|kid.?free|family.?friendly|good neighbou?rhood|nice area|bad area|quiet,? no kids|adults? only|young professionals?|no section 8|no vouchers?)\b"
def steer_note():
    """Fair-housing guardrail: never filter on or describe areas, schools or who lives there."""
    return text([["I stick to the listing facts."], ["I can't judge areas or people."],
                 ["Try ZIPs, price or beds."]])


# ---------- channels: iMessage vs SMS/RCS (Android) ----------
CARD_LINE = "Tap the card to save me."
SAVE_LINE = "Save me as Listing Scout."   # SMS/RCS: no contact card, just this line
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u203C\u2049\u2753-\u2757\uFE0F\u200D\u20E3]")

def plain(msg):
    """SMS/RCS version of any text: no emoji (they force 70-char SMS segments), no card line.
    Same words otherwise; member words inside quotes are left exactly as written."""
    out, inq = [], False
    for ln in msg.split("\n"):
        if inq or ln.startswith('"'):   # quoted member words (may span lines): verbatim
            out.append(ln); inq = not (ln.endswith('"') and (inq or len(ln) > 1)); continue
        if ln == CARD_LINE: out.append(SAVE_LINE); continue
        out.append(re.sub(r"[ \t]{2,}", " ", _EMOJI.sub("", ln)).strip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n")

# iPhone tapbacks that arrive as text over SMS (and some RCS): Liked "..." etc.
REACTIONS = {"liked": ("\U0001F44D", "liked"), "loved": ("\u2764\ufe0f", "loved"), "disliked": ("\U0001F44E", "disliked"),
             "laughed at": ("\U0001F602", "laughed at"), "emphasized": ("\u203c\ufe0f", "emphasized"),
             "emphasised": ("\u203c\ufe0f", "emphasized"), "questioned": ("\u2753", "questioned")}
_Q = "[\"\u201c\u201d\u2018\u2019']"
REACTION_RE = re.compile(rf"^\s*(liked|loved|disliked|laughed at|emphasi[sz]ed|questioned)\s+{_Q}(.*){_Q}\s*$", re.I | re.S)
REACTED_RE = re.compile(rf"^\s*reacted\s+(\S+)\s+to\s+{_Q}(.*){_Q}\s*$", re.I | re.S)
REMOVED_RE = re.compile(rf"^\s*removed\s+(a|an|the)?\s*\S*.*?\s+from\s+{_Q}.*{_Q}\s*$", re.I | re.S)

def parse_reaction(t):
    """('remove', None, None) | (emoji, word, quoted) | None. Never a member's own words."""
    if REMOVED_RE.match(t or ""): return ("remove", None, None)
    m = REACTION_RE.match(t or "")
    if m: e, w = REACTIONS[m.group(1).lower()]; return (e, w, m.group(2))
    m = REACTED_RE.match(t or "")
    if m: return (m.group(1), "reacted to", m.group(2))
    return None

def reaction(name, emoji, word, where, plain_=False):
    """One short line: 'Sarah \u2764\ufe0f Maple St' (iMessage) or 'Sarah loved Maple St' (SMS/RCS)."""
    mid = word   # 'Sarah loved Maple St' on every platform (no emoji in any text)
    w = shorten(where, MAX - len(f"{name} {mid} ")) if where else None
    return text([[f"{name} {mid} {w}" if w else fit(f"{name} {mid} a listing", f"{name} {mid} one")]])


# ---------- Make it better (bug or idea -> the Listing Scout team, only on a clear yes; never auto-queued) ----------
def feedback_ask(words):
    """'Send this to the Listing Scout team?' split to fit 30 characters."""
    return text([["Got it:"], quote(words), ["Send it to the Scout team?"]])

def feedback_sent():
    return text([["Thanks, I passed it on."], ["The team reviews each one."]])

def feedback_dropped():
    return text([["Okay, I won't send it."]])

def feedback_fixed(words):
    """'You asked, it's fixed': drafted only, sent by hand after the owner approves and the fix ships."""
    return text([["You asked, it's fixed:"], quote(words), ["Thanks for telling me."]])

# ---- email alert watch (owner only) ----
def email_zero_note(site):
    """An alert email came in but no homes could be read from it. The file is kept for review."""
    return text([[fit(f"A {site} email came in.", "An alert email came in.")], ["I couldn't read homes from it."],
                 ["I saved it so we can fix that."], ["You may want to check the app."]])

def routine_stale_note(mins):
    return text([["Alert emails stopped syncing."], [fit(f"Last check was {mins} min ago." if mins < 120 else f"Last check was {mins // 60} hours ago.", "The last check was a while ago.")],
                 ["Other sources are still fine."]])

def site_quiet_note(site):
    return text([[fit(f"No {site} emails in 2 days.", "One site went quiet for 2 days.")],
                 ["Its alert may be switched off."], [fit(f"Worth a look in {site}.", "Worth a look in that app.")]])

# Apply for me (src/apply.py). The bot does the filling in the Grok Bot app; texts stay short and calm.
def apply_ack(where):
    w = shorten(where, 17)
    return text([[f"Applying to {w}." if w else "Got it, let's apply."], ["I'll start the application."], ["Open the Grok Bot app next."],
                 [APPLY_YES_LINE]])

def apply_need_profile():
    return text([["Apply needs your own profile."], ["Set it up in the Grok Bot app."]])

def apply_no_place():
    return text([["Which place do you mean?"], ["Try apply 1 or apply 2."]])

def apply_expired(where):
    w = shorten(where, 11)
    return text([[f"I didn't apply to {w}." if w else "I didn't apply that time."], ["That request timed out."],
                 ["Text apply again anytime."]])

def member_paused(name, on):
    return text([[f"{name} {'resumed' if on else 'paused'} their texts."]])


def link_fix(where, url):
    """A wrong link went out: one short correction (v1.2.7)."""
    head = f"Fix for {where}"
    return text([[head if len(head) <= MAX else "A link fix"], ["The link I sent was wrong."], Group(["Here is the right one:", url])])
