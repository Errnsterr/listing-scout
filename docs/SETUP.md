# Listing Scout: setup guide

**Features:** calm alerts that fit your list · a "what's out there right now" snapshot on day one · **Decide together**: invite a partner, you both get each place, see each other's thoughts, and Listing Scout keeps a shared shortlist (no forwarding links or screenshots). Texts go through Photon; check its plans at photon.codes/pricing.

Template version **1.2.7** (see `VERSION`). To update, run `git pull` in this folder (or download the new release archive) and keep your own `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/` and `out/`.

Texts you new places that fit your list. Property-manager pages are checked about every 5 minutes; Zillow, Redfin and HotPads alerts arrive when the bot next reads its inbox (see docs/COSTS.md). **US only. Rentals (the default), and buying (experimental, new in v1.1.0).** No coding needed by you; your bot does the technical parts.

**Please read:** [Disclaimer](DISCLAIMER.md) · [Privacy](PRIVACY.md)

## What I'll always and never do

- **Always:** text you only about places that fit what you told me, and label anything a listing doesn't say as "not listed yet".
- **Never:** email or call a landlord, apply without your yes for that listing, or text anyone without your okay. Never make up details. Nothing goes out without your yes.
- **Your numbers:** only the last 4 digits are kept in files. Your Photon secret stays in a protected setting, never in chat.

The bot's exact setup wording is in "Setup conversation script" below. Photon questions are answered in `docs/PHOTON_FAQ.md`. Commands and technical details for the bot are in `FOR_YOUR_BOT.md`.

## Before you start

- About an hour with your bot, plus up to a day for the first real alert.
- An iPhone (iMessage) or any phone that gets texts.
- A Google account for Photon sign-up, and the cities/ZIPs, beds, price and move date you want.
- US only: rentals, or buying (experimental). You must be 18 or older.
- **Your phone and laptop can be off.** The scout runs on your bot's own computer. If that computer restarts, the scout starts again on its own. If alerts stop, text Help or ask your bot.
- **You may need to solve a captcha** ("I'm not a robot") when the bot signs up for Zillow, Redfin or HotPads.
- Your time zone (the bot asks). Quiet hours, Sleep mode and the evening roundup use it.

### Words used here

- **Secure form:** a private box the bot opens in chat. What you type there is never shown in chat or saved in notes.
- **Vault:** where the bot keeps passwords and keys it made or you gave it, encrypted, and never printed.
- **Routine:** a task the bot runs on a schedule by itself (for example, copying alert emails every few hours).
- **Inbox key:** an optional `AGENTMAIL_API_KEY` that lets the script pull alert emails directly, so they arrive faster.

### Try it without texting anyone (shadow mode)

Set `shadow: true` in `CRITERIA.yaml` (works for rentals and buying). Every text is written to `out/shadow_texts.jsonl` instead of being sent. Remove it to go live.

## Section 1: Setting up for someone new (checklist)

1. [ ] Get the code with `git clone https://github.com/Errnsterr/listing-scout`, or by downloading the release archive. Copy `CRITERIA.example.yaml` to `CRITERIA.yaml`.
2. [ ] Fill in: rent (default) or buy (experimental), cities + ZIPs (US), bedrooms, baths, price tiers, pets, move date. Then sort each extra (garage, ground floor…) into must-have or nice-to-have, one question at a time (see "Criteria hygiene").
3. [ ] Names for each person (iMessage vs SMS/RCS is detected automatically per line). Phone numbers are collected by a **secure form**, never typed in chat.
4. [ ] Add property-manager pages (AppFolio pages look like `https://NAME.appfolio.com/listings`). Mark any you could not open as `verified: false`.
5. [ ] Email alerts (section 2: the bot can create the site accounts for you) and texting (section 3).
6. [ ] Optional: application profile (Apply for me) and the apply-watch routine, with the owner's okay.
7. [ ] Approve a sample alert (section 4). Then the bot checks about every 5 minutes.

## Section 2: Email alerts from listing sites (the bot can do this for you)

Your alerts address: **your bot's alerts inbox** (the bot claims it on day one and tells you the address; it's `alert_inbox` in CRITERIA.yaml). Sites block bots, so we let them email us instead.

**Easiest: let the bot set them up.** Most people never use Zillow's or Redfin's alert features, so the bot offers to create free **Zillow, Redfin and HotPads** accounts on its own alerts inbox and save your search on each with **instant** email alerts. Your own accounts (if any) are untouched. Logins go into your vault; any sign-up code arrives in the bot's inbox.

If a site asks for a captcha or phone check, the bot asks you for that one step.

**If a site blocks the bot's sign-up:** make the account yourself on that site, save your search with instant (or daily) email alerts, and set the site to email your own address. Then forward those alert emails to the bot's alerts inbox (most email apps have an "auto-forward" or "filter → forward" setting; forwarding each email by hand works too). The bot reads forwarded alerts the same way.

- **Zillow allows at most 5 locations per saved search**, so the bot splits your areas across as many searches as needed (for example 8 ZIPs = two searches) and checks that every area is covered.
- **Redfin's rental search takes one region per saved search**, so 8 ZIPs = 8 Redfin searches. HotPads takes one area per search too.
- **Site filters: for rent (or for sale) plus area only.** In our testing, site filters quietly hid places that fit: a pet filter dropped homes that allowed pets, and Redfin's 'deals' option dropped regular listings. Listing Scout does the filtering for you, and keeps anything a listing doesn't say.

**Alert speed is how often the inbox is read.** A site emails right away, but the text goes out only when Listing Scout next reads its inbox. Reading more often is faster and uses more of your Grok Bot plan.

**Timing, up front:** with `AGENTMAIL_API_KEY` set (secure flow only), `src/fetch_inbox.py` pulls new Zillow, Redfin and HotPads alert emails into `inbox/` at the top of every loop cycle.

It dedupes by message id and skips verification, welcome and code emails, so alerts reach you within one cycle.

Without the key, a bot routine copies them on your plan's schedule: Lean twice a day (up to about 12 hours), Standard every 2 hours, Hands-on hourly. A faster routine (for example every 10 minutes) works too, but each run uses some Grok Bot usage.

Property-manager listings are checked about every 5 minutes, on every plan.

**Doing it yourself instead** (same settings): on each site, sign in with an account that uses the alerts address (Zillow emails alerts only to the account's own email), search, set the filters above, **Save search**, and pick **Instantly** / **Instant**.

**Also supported (same idea):** Craigslist (saved search email alerts; timing not guaranteed instant), Realtor.com, Zumper, Rent.com.

**Best early source:** ask a local real-estate agent to set an **MLS auto-email** to the alerts address.

**Facebook Marketplace / local groups:** login-only, so check by hand; the bot doesn't log in there.

### Verify each site's email (required, or alerts never arrive)

- **Zillow:** open "Please verify your email address" in the alerts inbox and follow the link.
- **Redfin:** add a first and last name on the account first (a neutral name like "Listing Scout" works), then open "Please verify your email". If the link expired, request a new one (Redfin rate-limits resends).
- **HotPads:** sign-in is a one-time code sent to the alerts inbox.

**First real alert check:** setup isn't done until one real alert email from a site has been parsed (`out/email_proven.json` appears). Until then the watchdog reports "email path unproven".

**What to expect:** each site first sends welcome and verify emails. Those aren't alerts. The first real alert usually comes when a new place is posted, which can take a few hours or up to a day.

Quiet is normal.

### How alert emails reach the bot (pick one)

- **Grok Bot inbox + routine** (no key needed): the bot's own inbox, copied into `inbox/` by a bot routine on your plan's schedule (or faster if you choose, at more usage). Set `inbox_pull: routine`.
- **AGENTMAIL_API_KEY** (secure flow only): `src/fetch_inbox.py` pulls at the top of every loop cycle. Set `inbox_pull: api`.
- Neither set up: the bot tells you once (health check), never fails silently.

## Buying a home (mode: buy) — EXPERIMENTAL

> **Experimental (new in v1.1.0):** start every buy setup in shadow mode (`shadow: true`) for about a day, check the would-be texts, then turn on real texts with the owner's yes. At setup the bot says:

>

> "Buying is still new."

>

> "Tell me if anything looks off."

- **Setup asks only five things:** price range, beds/baths, areas, HOA max, and home type (house, condo, townhome). Everything else (sq ft, lot, year built, days on market, open houses) is shown as a detail, never a filter. Unknowns are kept and shown as "not listed yet".
- **Sources:** Zillow, Redfin and Realtor.com for-sale alert emails, with each site search set to **for sale + area only** (no price, bed or other site filters; the scout filters). No property-manager pages.
- **Alerts:** new homes, price drops, headed "A price came down" ("Now $725,000 (was $749,000)") and back on the market. Coming soon and open-house times show when the email has them. No "/mo" on prices; HOA shows as "HOA $350/mo", "No HOA" or "HOA: not listed yet".
- **Pending or sold:** never a new alert. If someone shortlisted that home, only they get one calm note: "Heads up on {street}:" / "It's now pending."
- **Pace (default):** standouts (a match within your target price) are texted right away; the rest come in one evening roundup after 6 PM. Say "text me everything right away" or "just the evening roundup" to change it (asks first).
- **Guardrails:** the welcome adds "Not an agent or advice." The bot never contacts listing agents or sellers.
- **Proof run:** set `shadow: true` to parse real alert emails and log would-be texts to `out/shadow_texts.jsonl` without sending.
- **Not advice:** never price, offer, mortgage or investment advice.

## Section 3: Setup, in order (about an hour; first matches in about 10 minutes)

First conversation, in order:

1. Welcome (renting or buying?).
2. Four questions (where, beds and baths, comfortable and stretch budget, move date) with a fixed read-back.
3. Every current match, shown exactly like a text, scam-checked.
4. The recommended next step (texts and listing-site alerts).
5. Texts anytime, or hold late ones till morning.
6. Finer details one at a time, each skippable.
7. Chat-only reminders, stopping after two skips, and a "found a place" close.

Full wording: `docs/skill/SKILL.md`, "Getting started".

Texting setup (8 steps, plus up to a day for the first texted alert):

More questions? See `docs/PHOTON_FAQ.md`. The bot's exact wording is in "Setup conversation script" below.

1. **Step 1: Your search, in your words** (2 min). *Why: you see that the bot understood you.* The bot also asks your time zone (`timezone`; default America/Los_Angeles). It repeats your search back; you correct anything.
2. **Step 2: The promise** (30 sec). *Why: you know the limits first.* See "What I'll always and never do" above.
3. **Step 3: Photon account and secret** (10–20 min). *Why: Photon sends your texts from a real phone number.*
   - Easiest on a computer or tablet browser. Go to **app.photon.codes** and choose **Continue with Google**.
   - Make a project and name it **Listing Scout**. (The button may look like "New project" or "Create project".)
   - Open **Configure**, then click **Reveal** next to **Project secret**. Paste it only into the bot's **secure box**, never in chat. The Project ID isn't secret.
   - Plans: see photon.codes/pricing. **If Photon asks for payment, a phone number or ID:** stop there and tell the bot what the screen says. Don't enter a card unless you've chosen a paid plan yourself.
   - **Stuck? Tell the bot what you see** (the words on the screen, or a screenshot). It will guide you from there and never guesses at buttons.
   - The secret is saved to `~/.config/listing-scout/env` (private, outside this folder, never printed), so a restart keeps it.
   - Expected: "You're connected to Listing Scout."
4. **Step 4: Add each person** (5 min). *Why: Photon only texts people on its Users list.*
   - On Photon's **Users** page, add each person's mobile number (iPhone or Android). Your plan sets how many (photon.codes/pricing). Each person gets their own thread; no group chats.
   - iPhone gets iMessage. Android gets regular texts (SMS/RCS), tested once so far.
   - Expected: "You're added. Your texts will come from the number ending {last 4}."
5. **Step 5: Save it as a contact** (1 min). *Why: alerts then come from "Listing Scout", with a little house photo, not an unknown number that iPhone may filter.*
   - The bot gives you a contact card here in chat. Tap it, then **Create New Contact**.
   - Expected: "Saved. Alerts will show up as Listing Scout."
6. **Step 6: Send the first text** (1 min). *Why: one message from you opens your line.*
   - From that contact, text anything, like **"hi"**.
   - Required: Photon refuses to text you until you do. Photon assigns each person their own line, so do this even if you've used Photon before.
   - Expected: "Got it. Your line is open."
7. **Step 7: Approve a sample alert** (2 min). *Why: you choose the format before anything is automatic.* It uses a real listing from today. Examples: `docs/SAMPLE_MESSAGE.txt`.
8. **Step 8: Costs, plan, and going live** (3 min). *Why: no flood of old listings, and proof it works.*
   - You pick a plan (Lean, Standard or Hands-on; see `docs/COSTS.md`).
   - The bot runs `src/scout.py --dry-run` (so the trade-off counts are real), then a quiet seed `src/scout.py --seed` (notes everything listed today; texts nothing about those), then starts watching with `./src/ensure_running.sh`.
   - You get **one welcome text** with the contact card. It's also the test: it ends with "Did this come through okay?"
   - Then one **"Here's what's out there right now"** text: how many places it checked, how many fit right now, and every match, each as a numbered entry with its link.
   - After that, you only hear from it when something new fits.

## Costs and plan modes

Checking listings and texting use no AI. See `docs/COSTS.md` for the cost table and the Lean / Standard / Hands-on plans. Nothing starts until you approve going live.

## Inviting another household member (one forward for you, one text for them)

1. Tell the bot "add my partner" (or a roommate or family member). It sends a **secure form** for their name and number; the number is never typed in chat, and only the last 4 digits are kept.
2. The bot asks you to confirm, then adds them (`src/notify.py add_user "{Name}" --confirm`). Photon **assigns each person their own Listing Scout line** (the number their texts come from) and their own 1:1 thread. No group chats.

   How many people you can add depends on your Photon plan (photon.codes/pricing).

3. With your okay, the bot texts **you** two messages on your Listing Scout thread:

```text
Here's {Name}'s invite.

Forward the next text.

Press and hold it.

Tap More, then the arrow.

Pick {Name} and press Send.
```

then the invite itself. Press and hold the invite, tap **More**, then the arrow (Forward), pick them, and press **Send**. The bot never texts them first, and it can't until they text the line.

4. They get this, with no links at all:

```text
Hi {first}!

I set up Listing Scout for us.

It texts us homes that fit.

Tap the number to say hi:

{their Scout number}
```

They tap the number and say hi. No card to save first.

Privacy: the invite is a plain text with no links, so no hosted or third-party page ever sees who is invited. iPhone turns the number into a tap target on its own. A raw `sms:` link (`out/invite-{Name}-link.txt`) is kept only as an internal fallback and is never texted.

5. The moment their text arrives, the bot sends their welcome with the **contact card** attached, you get "{Name} is in.", and a minute later they get the same "what's out there right now" snapshot you got. If they haven't texted after about a day, you get one gentle heads-up.
6. They get alerts in the format you approved. Optional: only target-range alerts (`tiers: [target]`) in their CRITERIA entry. Tier words: `target`, `stretch`, `usual` (= above your usual range).

**Welcome text** (sent automatically when they text in; rendered from `style.member_welcome`):

```text
Hi {first}!

It's Listing Scout.

{Owner} said you'd stop by.

Tap the card to save me.

Here's what we're looking for:

{area}
{beds}
{budget}
{stretch}

You get {Owner}'s alerts too.

We can decide together here.

Tell me what you think of one.

I'll share it with {Owner}.

See it before paying anything.

Not listed yet is normal.

Each home shows up once.

By staying in, you're 18+.

Text STOP anytime to stop.

Did this come through okay?
```

## If something goes wrong

Nothing is broken on your side; there's always one simple next step.

- **"Target not allowed for this project"**
  - That person's line isn't open yet. Have them text anything, like **"hi"**, to the Listing Scout contact, then try again.
  - Still failing? Their iMessage may be registered under a different number or an email. Open **debug.photon.codes** on their iPhone.

    It tells them which handle they send from. Add that handle on the Users page.

- **The test says it sent but nothing arrived**: check that iMessage is on (Settings, then Apps, then Messages), and make sure Listing Scout is saved as a contact (Step 5), and check the Unknown Senders list.
- **Someone on Android or with iMessage off?** Each line is checked automatically; non-iMessage lines get plain text. Tested once: it arrived as RCS.

## Section 4: Going live

1. The bot shows you a sample alert built from a real listing today.
2. You approve wording + how many texts/day is OK.
3. Step 8's quiet first run saves everything currently listed as "seen" (no flood). After that only **new** listings, **price drops**, and **relists** (gone 3+ days, then back) are texted.
4. A small script (no AI) checks about every 5 minutes (`loop_minutes` in `CRITERIA.yaml`). It restarts itself after the bot's computer restarts, and a weekly health check makes sure it's still running. Each match is texted on the check that finds it; several found on one check go as one numbered text.

## Text style (applies to every text anyone receives)

All texts (alerts, bundles, price drops, welcome, invite note, error hints, relays) go through **one formatter, `src/style.py`**:

- One sentence per line, and **every full sentence is followed by a blank line**. Exceptions stay grouped: alert facts (beds/baths/type, area, price; garage/available/pets), numbered steps with their intro line, and an address with its link right under it.
- Every line is **one whole thought of 30 characters or fewer**, so it never wraps mid-thought on an iPhone. Nothing is ever wrapped; long sentences are rewritten shorter, and names drop out of a line when they would push it past 30. Exempt: links, a street address directly above its link, and a member's own quoted words.
- After a colon, leave a blank line: an intro line ending in ':' gets a blank line before what follows, and text after an inline colon goes below a blank line, on the next line ('2. Text it:' / 'Hi Listing Scout, I'm in.'). For now, alert fact labels ('Pets: …', 'Garage: …') stay on one line.
- Links always sit alone on their own line.
- Same headlines, no emoji in any text ("New place that fits", "A price came down", "Back on the market"; buying: "New home that fits", and "Two new homes today" for a buying roundup). Rentals are instant: several fits from one email go out as separate single texts, never "Two new places today", and the same close: "No rush." / "I'll keep watching."
- Nothing is sent if it fails the style check.

All rendered examples are in `docs/SAMPLE_MESSAGE.txt`.

## What each text looks like (calm style, the template default)

Short blocks separated by a blank line, short lines, no capitals for emphasis, no stars or tags.

1. Headline: "New place that fits" / "A price came down" / "Back on the market" (buying: "New home that fits" / "Two new homes today"). Rentals never get a "N new places today" bundle
2. Beds, baths, type · area + ZIP · "$3,895/mo" · "In your target range" (each on its own line) (the ranges come from your CRITERIA price tiers: target range, stretch range, top of your stretch range, above your usual range) Price drop: "Now $3,895/mo (was $4,095)". A building priced from its lowest unit: "From $2,295/mo".
3. Garage · available date · pets. Only rent, beds, baths and pets say "not listed yet" when missing (last in their block). Anything else shows only when the listing states it.

   The bot never guesses. Pets lines appear only if you have pets. Nice-to-haves (garage, layout) show only when the listing states them: "Has a garage", "No garage".

   Never guessed.

4. Optional plain-words context, only with 8+ similar listings seen: "A bit above nearby 2-beds." When something looks off: the reason (e.g. "It's far below similar places.") and always "See it before paying anything."
5. The street address on its own line, directly above its link, so the address labels the link. If the email names only a building, the street comes from the listing page's address; the building name shows only when no street exists anywhere. The link sits alone on the next line (plus a showing link when the manager has one).
6. "No rush. I'll keep watching."

Several matches within the same hour arrive as one numbered text, each with its address and link. Examples: `docs/SAMPLE_MESSAGE.txt`.

Only "fits" listings are texted. **Light filters (default):** in your area, beds_min+ and baths_min+ (unknown kept), price up to your stretch (unknown kept), and pets not explicitly disallowed. A place is left out only when something it states clearly misses. A building with several units fits if any unit could: "1 to 3 beds" passes a 2-bed search, and "from $2,295" passes when that lowest price is within your stretch. It shows as "From $2,295/mo" and "1-3 bed", with no target-range line, because other units may cost more. Garage and layout are nice-to-haves shown in the alert unless you make them must-haves.

## Extra features (all confirm-first, no AI)

- **Take a break.** Anyone can text STOP and it's instant and silent (no reply; the owner gets one quiet note). "START" turns texts back on. The owner can also say "remove {Name}".

  I ask "Take {Name} off the search?" and act only on a clear yes. Then they get one goodbye, their replies and likes are deleted, and they're never texted again. Removing them from Photon's Users page stays your choice.

- **Sleep mode.** Off by default, because a 2 AM listing can be gone by 9. After the first late-night alert, I offer it once the next morning ("Want me to?"). If you say yes, finds between 10 PM and 7 AM (`quiet_hours` in CRITERIA) wait and arrive as one bundle at 7 AM.

  Price drops wait too. Each person chooses for themselves ("sleep mode" / "sleep mode off").

- **Still available?** Only for places someone liked or asked to tour, and only after they've been gone from every feed for about a day (to ride out feed blips). The text says "It's no longer listed." It never says "rented", because we can't know that. If it comes back, it alerts again as usual.
- **One home, one text.** If the same address shows up later from another source (say, a Zillow email hours after the property manager's page), it's attached quietly. It only alerts again if the new price is lower. If an address is missing or unclear, it alerts as usual rather than guess a match.
- **Fine-tune the search.** Text a change in plain words: "add 78745", "go up to 4,500", "stretch to 5.5k", "3 beds is fine". I read it back as one line and ask "Want me to make that change?" Only your yes applies it. Then I back up `CRITERIA.yaml` to `out/`, update it, and re-seed quietly so places already out there don't flood in.

  If I'm not sure what you meant, I ask; I never guess. A co-decider's suggestion comes to you word for word, and only your yes applies it.

- **We found it.** Only the owner's yes ends the search. If a co-decider says it, their words come to you first. After your yes, everyone gets "Congrats on the new place!", the watcher stops, and I offer once to clear the search data and close the Zillow/Redfin/HotPads saved searches.

  That happens only on your yes, and then the reply listener stops too.

- **Your data stays put.** See "What I keep" below.

## Make it better (bug or idea, gated)

- Anyone can text a bug or idea in plain words: "bug, the link didn't open", "idea: ...", "suggestion ...", "something's broken". Only clear openers count; anything unsure is handled as a normal reply and relayed.
- The bot asks first: "Send it to the Scout team?" Only a clear yes sends it. A no drops it ("Okay, I won't send it."), and any other text lets the question lapse.
- What is sent: only the person's exact words, the bot VERSION, and the kind of last text they got (alert or welcome). No phone numbers, names, addresses or criteria.
- Where it goes: every item is saved to out/feedback.jsonl with status pending_review. feedback_email is blank by default in CRITERIA.example.yaml, so nothing is emailed. The owner sets their own address to receive items; src/replies.py then prints a FEEDBACK_EMAIL line and the bot emails it there.
- GATE: nothing is ever auto-queued or built. Items stay pending_review until the owner explicitly approves. `python3 src/review_feedback.py` lists pending items; `--approve ID` / `--decline ID` only mark them; `--fixed ID` (after an approved fix ships) prints a draft "You asked, it's fixed" text that is never sent automatically.
- The owner welcome mentions it once: "Spot a bug, just let me know." (Members' welcome drops it to fit the 18+ line.)

## Criteria hygiene (must-have vs nice-to-have, confirm-first)

- Setup asks one plain question per extra: "Is a garage a must-have? / Or just nice to have?"
- Before saving, it shows the real trade-off from current listings (`features.tradeoff()` on `out/pool.json`): "As a must-have, about N fit. / As a nice-to-have, about M." If it can't count, it says "I can't count that one yet." Numbers are never invented.
- Unknown details are kept by default. Missing rent, beds, baths or pets show as "<Thing>: not listed yet"; other facts show only when the listing states them.
- Weekly near-miss check-in (part of Fine-tune the search): "N places missed only on <thing>. / To see places like these: / <the exact change, e.g. Set your stretch to $5,200.> / Want me to make that change?" A clear yes applies one backed-up CRITERIA change; anything else changes nothing.
- Volume nudge: no matches in 7 days suggests loosening one thing; more than ~5 a day suggests tightening one (e.g. "Make a garage a must-have."). Confirm-first, at most one check-in a week, nothing on day one. Turn it off with `checkins: false` in CRITERIA.yaml (default `checkins: true`).
- **Check-in off switch (per person):** anyone can text "no check-ins" to stop the quiet-week pulse, first-week ask and near-miss check-ins for themselves; alerts keep coming. "check-ins on" turns them back on.

## STOP and deleting data

- Everyone learns this in their welcome: "By staying in, you're 18+." and "Text STOP anytime to stop." "help" and "what can you do" send the same command list.
- **Commands (one list, in help, "what can you do" and these docs):** "Text me your thoughts." / "Text shortlist for picks." / "Text apply to start one." (rentals, owner and co-deciders) / "Text a change to the search." (owner and co-deciders; a co-decider's idea goes to the owner) / "Text pause or resume anytime." / "Text leave to get off." / "Text end my search to end." (owner only) / "Text STOP anytime to stop." Texting START turns texts back on.
- STOP, cancel, unsubscribe, end, quit are handled before anything else: no reply, the person is marked stopped, any waiting question is dropped and nothing is applied.
- **"end my search"** (owner only): the bot asks "End your search for good?" and needs a word yes. Then everyone on the search gets one goodbye, the loop and reply listener stop, the bot pauses its own routines, and it offers to delete the data and close the site searches. Last step for you: remove people on Photon's **Users** page (and cancel a paid Photon plan, if you have one).
- Delete everything and clearing search data need a word yes ("yes", "yes please", "do it", "go ahead"); "k" or a thumbs-up doesn't count.

## Tapbacks and channels

- Tapbacks (Liked, Loved, Laughed at…) are never relayed as typed words; they're passed on as a short note, like "Sarah loved Maple St"
- Each person's line is checked automatically (iMessage vs SMS/RCS). Non-iMessage lines get the plain-text version: no emoji, no contact card, Android forwarding steps. If the check can't tell, it falls back to iMessage.

  Tested: a plain-text test reached an iPhone with iMessage off as RCS.

## Alert extras (calm, never invented)

- **Via line:** each alert says where it came from: "Via Redfin" or the manager's name (`show_source: false` hides it).
- **The listing's own apply or agent link (when the email has one):** alerts show "Apply link from the listing:" followed by the link. Only links the email labels that way ("Apply now") are used. Tracker links are unwrapped only when the real address is inside them, tokens are dropped, and opaque links are skipped.

  The bot never opens these links or contacts anyone. It opens an apply link only after a member texts "apply" (see Apply for me in `docs/skill/SKILL.md`), and never submits without their yes for that listing. Real Zillow and Redfin alerts seen so far had no such link, so expect it rarely.

- **Posted about N min ago (best-effort):** only when the source gives a real posting time; otherwise no line. Not yet seen on a live alert email.
- **Quiet-week pulse:** after 7 days with no alert texts, one note: "Quiet week, still watching." / "I checked {N} places." (real count) / "Nothing new fit yet." / "Text no check-ins to skip." Then nothing until another quiet week.
- **Daily cap (off by default):** say "max 3 texts a day" and the bot asks first; extras wait for one evening text after 6 PM. "No daily cap" turns it off (also confirm-first).
- **First-week ask:** once, about day 4, the owner gets "A few days in." / "Anything bugging you so far?" / "Text no check-ins to skip." A real answer goes into Make it better (it still asks before sending anything).

## What I keep

Everything stays on the bot's own computer. Nothing is copied to a hosted page. Photon (the texting service) sees phone numbers and message text so it can deliver them; feedback someone confirms is shared as described in PRIVACY.md.

| What | Where | How long |
|---|---|---|
| Phone numbers | Not in our files. Only the last 4 digits are in `CRITERIA.yaml`; full numbers are looked up from Photon at send time. | Until you remove the person |
| Who has joined, paused, stopped or left; Sleep mode | `out/members.json` | While the search runs |
| Replies and likes (your words, verbatim) | `out/shortlist.json` | While the search runs. Deleted when someone leaves or is removed, and at the finish line if you say yes |
| Listings seen and their prices | `state.json` | While the search runs |
| Message and run logs (numbers masked) | `logs/` | 30 days, then deleted automatically |
| Your search settings | `CRITERIA.yaml` (+ backups in `out/` after each change) | Until you delete them |

- If anyone asks, they get: "Replies stay while we search." / "When it ends, I delete them." / "Only Photon sees the texts."
- "delete everything" (owner only): I ask "Delete all the search data?" first. On yes, replies, shortlist, queues and logs are deleted. The joined/stopped flags stay so a STOP is still honored.
- Photon delivers the texts, so it sees them. That's how texting services work.

## Source status

The bot tests each property-manager page during setup and marks any that fail as `verified: false` in CRITERIA.yaml. Big portals (Zillow, Apartments.com, HotPads, Craigslist) block bots, so they come in by email alerts.

## Writing new text wording (for template authors)

Every text passes the style check, and the colon rule is strict: nothing may follow a colon on the same line, except fact labels (Pets:, Garage:, Rent:, Address:, Link:).

- Write headers as plain sentences: "This is a sample, not a new listing." (not "Test only: a sample").
- Or end the line with the colon, leave a blank line, and put the rest below ("2. Text it:" / blank / '"Hi Listing Scout, I'm in."').
- Never tell people to reply. Replying is offered as a gentle option, never a command ("I'll pass your thoughts to {owner}."). Commands are always written "Text ___" ("Text pause anytime.", "Text STOP anytime to stop.").

  Decide together is mentioned once, as a benefit, in the welcomes. The only "Reply ..." line is the first-text receipt, "Did this come through okay?"

- A relayed reply is the person's own words, exactly as written. Only the header ("Alex on Main:") follows the style.
- Missing rent, beds, baths or pets say "X: not listed yet", last. Other facts show only when stated.
- Keep every line to 30 characters or fewer (an iPhone wraps at about 30). Rewrite shorter; never wrap.

## Edge cases it handles

- Same home on two sites at two prices: one alert, lower price first, "Also $X/mo on Site".
- Gone, then back cheaper (even under a new listing id, same address): one "Back, and lower" alert.
- Missing rent or beds: "not listed yet". A missing address shows as "Address not shown". When a site gives only the street (HotPads often hides the number), it shows the street with "(no number listed)", for example "Royan Ln (no number listed)". Never guessed.
- Scam signals (far below similar places, money before a tour): one gentle caution line, never more.
- A roundup (2+ fits) shows every place that fits, nothing left out: each is "N. address", one line with price, beds and area, then its own link (no "not listed yet" lines). If one text would pass about 1,500 characters, it goes as consecutive texts labeled "Part 1 of 2" and so on; a place is never split across texts, numbers continue across parts, and replying with any number works.
- Two people reply at once: relayed in the order they arrived.
- A reply with no street right after a newer alert: it asks which place, once.
- Photo or voice reply: forwarded as is if Photon allows it; if not, the other person hears "I can't pass a photo on yet." / "Words come through fine." (unverified live)
- STOP: honored at once, no reply (the carrier sends its own); the owner gets a gentle note. "START" turns texts back on. Unverified: Carrier/CTIA rules for STOP depend on Photon's sender type and are unverified.
- "leave": "Sarah left the search." to the owner; their replies are deleted and they're never texted again. A new number means adding them again.
- Owner says "remove Sarah": asks first; on yes, a goodbye, their replies deleted, never texted again.
- Per-person tiers (`tiers:` on a recipient); one shared shortlist.
- If you set `photon.user_limit`, adding someone past it is refused before anything changes.
- A source or Photon hiccup: quiet retries; the owner hears only if a source is down for over a day.
- Box restart: the watcher comes back by itself; seen listings are saved, so no repeat alerts.
- "We found a place": the owner confirms, everyone gets a warm goodbye, the watcher stops, and the owner is offered (once) a data clear-out plus closing the saved searches.

---

## Setup conversation script (the bot follows this)

> `docs/skill/SKILL.md` is the source of truth for the setup flow (cases A and B). This file keeps the longer wording notes.

Tone: calm, warm, plain. One ask at a time. Every step has a one-line *why*, a time estimate, and a warm confirmation.

Don't move on until the step is confirmed.

Template 1.2.7. Runs after getting started's welcome, 4 questions, current matches and recommended next step. Order: 1 reflect · 2 promise · 3 Photon + secret · 4 add people · 5 save contact · 6 first text · 7 sample alert · 8 go live (plan, quiet first run, welcome = test, snapshot).

Commands for each step are in `FOR_YOUR_BOT.md`.

### Step 1: Reflect their search (≈1 min)

*Why: so they know they were heard before we ask for anything.*

> "So: {areas}, {N}+ beds, {N}+ bath, up to ${comfortable}, stretch ${stretch}, moving by {date}. Right?"

Confirm: "Perfect, that's your search. I'll keep it exactly like that."

### Step 2: The promise (≈30 sec)

*Why: trust first. They should know the limits before they connect anything.*

> "Here's what I'll always and never do:

> - I'll only text you about places that fit what you told me.

> - I'll never contact a landlord, or text anyone without your okay.

> - I'll apply only on the listing's own apply page, after your yes for that place.

> - I'll never make up details. If a listing doesn't say something, I'll say it's not listed yet.

> - Your phone numbers aren't stored in my files, only the last 4 digits.

> Texts take 8 short steps, including the listing-site accounts."

Confirm: "Thanks for trusting me with this."

### Step 3: Photon account and secret (≈4 min)

*Why: Photon sends your texts from a real iMessage number. See photon.codes/pricing for plans.*

> "Please sign up at app.photon.codes with **Continue with Google**, create a project called 'Listing Scout' (plans: photon.codes/pricing). Then open **Configure**, click **Reveal** next to Project secret, and paste it into the secure box I'm sending. Please don't paste it in chat."

Run the connection check (sends nothing). Confirm: "You're connected to **{project}** "

### Step 4: Add each person (≈2 min)

*Why: Photon only texts people on your project's Users list.*

> "On the Photon **Users** page, please add your mobile number (iPhone or Android)."

Photon assigns each person their own line. Other people are added later, one at a time, with the secure form and `src/notify.py add_user "{Name}" --confirm` (see "Invite another household member" below); never ask for digits in chat.

Confirm: "You're added. Your texts will come from the number ending **{line_last4}**."

### Step 5: Save it as a contact (≈1 min)

*Why: alerts then arrive from 'Listing Scout', a sender you trust, instead of an unknown number that iPhone may filter away.*

Make their contact card (with the house photo) and share it here in chat.

> "Here's a contact card for Listing Scout. Tap it, then **Create New Contact** (or **Add to Existing** if you already saved the number). It's your own Listing Scout line, ending **{line_last4}**."

Confirm: "Saved. Alerts will show up as **Listing Scout**."

### Step 6: Send the first text (≈1 min)

*Why: Photon needs one message from you to open your line. Without it, texts can't reach you.*

> "From the Listing Scout contact, please text anything, like **"hi"**. Then tell me when it's sent."

Confirm: "Got it, **{Name}**. Your line is open."

### Step 7: Approve a sample alert (≈2 min)

*Why: you choose how alerts look before anything is automatic.*

> "Here's what an alert will look like, using a real listing from today:

> {sample}

> Does this feel right, or would you like it shorter, or with less detail?"

Confirm: "Great, that's the format I'll use."

### Before going live: costs and plan choice (≈1 min, start of step 8)

*Why: no surprises. You know what's free and what uses AI before anything runs.*

> "Quick note on costs before I start watching:

> - Checking listings and sending texts is done by a small script, with no AI. For Photon costs, see photon.codes/pricing.

> - AI is only used when we talk, when I read your Zillow/Redfin alert emails, and for any extras you pick. You can see your actual usage in Grok Bot under Settings → Usage.

> Which fits you?

> - **Lean:** I check listings every 5 minutes, read alert emails twice a day, and use AI only when you ask.

> - **Standard:** like Lean, but I read emails every 2 hours.

> - **Hands-on:** like Standard, plus I try to add a short note to each match (fit and scam check; experimental). This uses the most AI."

Set `plan_mode`. Confirm: "Got it, **{mode}**. You can switch anytime by saying 'switch to lean'."

### Step 8: Go live (≈2 min)

*Why: no flood of old listings, proof that texts reach you, and something useful right away.*

Only after the owner approves going live: run the install (quiet first run, then the watcher). Then:

1. Ask: "May I send your welcome text? It's also the test." Send the **owner welcome** with the card (`style.owner_welcome`):

```text
Hi {first}!

It's Listing Scout.

Tap the card to save me.

I'm watching {N} places.

Quiet days mean nothing fit.

See it before paying anything.

Not listed yet is normal.

Each home shows up once.

Text apply on one you like.

By staying in, you're 18+.

Text STOP anytime to stop.

Spot a bug, just let me know.

Did this come through okay?
```

When they reply OK: "It works. You'll hear from Listing Scout at the number ending **{line_last4}**."

2. Right after, send the **snapshot** (once, built from the quiet first run, real data only): how many places were checked, how many fit right now by price range, every match as a numbered entry with its link, then "From here, I'll stay quiet." / "I'll text when something new fits." (`scout.snapshot`).
3. If no snapshot could go out, a one-time "I checked {N} places today. Nothing new fit yet." note goes out at 6 PM on day one instead. Never both.
4. In chat: "You can say 'pause', 'show me everything today', or 'change my search' anytime."
5. **Apply for me (optional, rentals).** Ask: "Want me to set up your application profile now?" On yes, ask the profile questions one at a time (job, income, past homes and references, move date, who lives with you, pets, cars) and save with `apply.save_profile()`. Never ask for SSN, date of birth or ID numbers here.
6. **Apply-watch routine (optional, owner's okay).** Ask: "Want me to check for apply texts every 5 minutes?" On yes, create "Listing Scout: apply requests" from `docs/routines/apply-watch.md`.

### Invite another household member (after setup, about 5 min total)

*Why: each person gets their own thread with the same alerts. Group chats aren't available on Free.*

**1. Owner asks** ("add my partner", "add my wife", "add my roommate"):

> "Happy to. I'll send a secure form for their name and number. The number never goes in chat, and I only keep the last 4 digits."

Send the secure form. The number goes into env `NEW_USER_PHONE`.

**2. Confirm before adding** (≈30 sec):

> "I'll add **{Name}** (number ending **{last4}**) to your Photon project. They'll get their own assigned Listing Scout line and their own thread. Okay to add them?"

Only after yes, add them on Photon and to the recipients list (see `FOR_YOUR_BOT.md`).

Confirm: "**{Name}** is added. Their texts will come from the number ending **{line_last4}**."

**3. Invite kit, texted to the owner** (≈1 min). The bot never texts the new person first, and it can't until they text the line.

Make their contact card (`src/make_contact.py "{Name}"`), then `src/make_invite.py "{Name}"`. Ask: "May I text you {Name}'s invite to forward?" Then send the owner two texts: `out/invite-{Name}-intro.txt`, then `out/invite-{Name}.txt`. The card is NOT forwarded; it rides on the welcome.

In chat, add: "Photon plans and limits: photon.codes/pricing."

```text
Here's {Name}'s invite.

Forward the next text.

Press and hold it.

Tap More, then the arrow.

Pick {Name} and press Send.
```

```text
Hi {first}!

I set up Listing Scout for us.

It texts us homes that fit.

Tap the number to say hi:

{their Scout number}
```

Privacy: the invite is a plain text with no links, so no hosted or third-party page ever sees who is invited. iPhone turns the number into a tap target on its own. A raw `sms:` link (`out/invite-{Name}-link.txt`) is kept only as an internal fallback and is never texted.

**4. They tap the number and say hi.** Any first text counts.

**5. Welcome text, automatic the moment they text** (`src/replies.py`; the owner already approved by forwarding the invite). The owner gets "{Name} is in." right away; the snapshot follows a minute later.

See `out/journey-compare.md` (`tests/render_journey.py`).

```text
Hi {first}!

It's Listing Scout.

{Owner} said you'd stop by.

Tap the card to save me.

Here's what we're looking for:

{area}
{beds}
{budget}
{stretch}

You get {Owner}'s alerts too.

We can decide together here.

Tell me what you think of one.

I'll share it with {Owner}.

See it before paying anything.

Not listed yet is normal.

Each home shows up once.

By staying in, you're 18+.

Text STOP anytime to stop.

Did this come through okay?
```

### Step 6: Optional preferences for them

> "Should {Name} get every alert, or only ones in your target range?"

Set it in their CRITERIA recipient entry: `tiers: [target]`.

Confirm: "Done. {Name} gets {choice}."

### When something goes wrong (calm template)

Say what happened. Say that nothing is wrong on their side. Give one next step.

- **Target not allowed:** "That text didn't go through. Nothing is wrong with your phone. Your line just isn't open yet. Please text anything, like **"hi"**, to the Listing Scout contact, and I'll try again."
- **Sent but not received:** "Photon accepted it, but it hasn't shown up yet. Nothing is wrong on your side. Is Listing Scout saved as a contact? Could you also check the Unknown Senders list in Messages?" If still nothing: "One more check: open debug.photon.codes on your iPhone and tell me the handle it shows."
- **Secret no longer works:** "I lost my connection to Photon. Probably the secret was changed, which is fine. Please paste the current one into the secure box I'm sending."
- **Listing site down:** only mention it if it lasts more than a day: "{Source} is quiet today." / "I'll keep checking it." / "Your other sites are fine."

Never retry a failed send more than once without asking.

### Features to mention ( chat wording, once each)

- At the promise (step 2): "Everything stays on my computer, and logs are deleted after 30 days."
- At going live (step 8): "Later, you can text me changes, like adding a ZIP. I'll read them back first."
- Sleep mode is never pitched in setup. It's offered once by text, the morning after a late alert:

```text
That last one came at 2:14 AM.

Overnight finds can wait.

They'd come at 7 AM instead.

Want me to?
```

- Owner removing someone:

```text
Take Sarah off the search?
```

- A liked place gone about a day:

```text
Heads up on Santa Isabel:

It's no longer listed.

I'll say if it comes back.
```

- Fine-tune read-back:

```text
Got it:

Add 78745 to the search.

Want me to make that change?
```

- The finish line (to everyone, after the owner's yes):

```text
Congrats on the new place!

The search is wrapped up.

No more listing texts from me.
```

- If a member asks what's kept:

```text
Replies stay while we search.

When it ends, I delete them.

Only Photon sees the texts.
```
