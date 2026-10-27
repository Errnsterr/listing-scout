# Listing Scout setup guide (`listing-scout`)
**Features:** calm alerts that fit your list · a "what's out there right now" snapshot on day one · **Decide together**: invite a partner, you both get each place, see each other's thoughts, and Listing Scout keeps a shared shortlist (no forwarding links or screenshots). Texts go through Photon; check its plans at photon.codes/pricing.
Template version **1.1.0** (see `VERSION`). To update, run `git pull` in this folder (or download the new release archive) and keep your own `CRITERIA.yaml`, `state.json`, `outbox.json`, `logs/` and `out/`.
Texts you new places that fit your list. Property-manager pages are checked every 5–15 minutes; Zillow, Redfin and HotPads alerts arrive when the bot next reads its inbox (see COSTS.md). **US only. Rentals (the default), and buying (experimental, new in v1.1.0).** No coding needed by you; your bot does the technical parts.

**Please read:** [Disclaimer](DISCLAIMER.md) · [Privacy](PRIVACY.md) · [Before you publish](PUBLISH_CHECKLIST.md)

## What I'll always and never do
- **Always:** text you only about places that fit what you told me, and label anything a listing doesn't say as "not listed yet".
- **Never:** contact a landlord, apply, or text anyone without your okay. Never make up details.
- **Your numbers:** only the last 4 digits are kept in files. Your Photon secret stays in a protected setting, never in chat.
The bot's exact setup wording is in `SETUP_SCRIPT.md`. Photon questions are answered in `PHOTON_FAQ.md`. Commands and technical details for the bot are in `BOT_NOTES.md`.

## Before you start
- About 60–90 minutes with your bot, plus up to a day for the first real alert.
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

## 1. Setting up for someone new (checklist)
1. [ ] Get the code with `git clone https://github.com/Errnsterr/listing-scout`, or by downloading the release archive. Copy `CRITERIA.example.yaml` to `CRITERIA.yaml`.
2. [ ] Fill in: rent (default) or buy (experimental), cities + ZIPs (US), bedrooms, baths, price tiers, pets, move date. Then sort each extra (garage, ground floor…) into must-have or nice-to-have, one question at a time (see "Criteria hygiene").
3. [ ] Names for each person (iMessage vs SMS/RCS is detected automatically per line). Phone numbers are collected by a **secure form**, never typed in chat.
4. [ ] Add property-manager pages (AppFolio pages look like `https://NAME.appfolio.com/listings`). Mark any you could not open as `verified: false`.
5. [ ] Email alerts (section 2: the bot can create the site accounts for you) and texting (section 3).
6. [ ] Approve a sample alert (section 4). Then the bot checks every 15 minutes on Lean, or every 5 on Standard and Hands-on.

## 2. Email alerts from listing sites (the bot can do this for you)
Your alerts address: **your bot's alerts inbox** (the bot claims it on day one and tells you the address; it's `alert_inbox` in CRITERIA.yaml). Sites block bots, so we let them email us instead.
**Easiest: let the bot set them up.** Most people never use Zillow's or Redfin's alert features, so the bot offers to create free **Zillow, Redfin and HotPads** accounts on its own alerts inbox and save your search on each with **instant** email alerts. Your own accounts (if any) are untouched. Logins go into your vault; any sign-up code arrives in the bot's inbox. If a site asks for a captcha or phone check, the bot asks you for that one step.

**If a site blocks the bot's sign-up:** make the account yourself on that site, save your search with instant (or daily) email alerts, and set the site to email your own address. Then forward those alert emails to the bot's alerts inbox (most email apps have an "auto-forward" or "filter → forward" setting; forwarding each email by hand works too). The bot reads forwarded alerts the same way.
- **Zillow allows at most 5 locations per saved search**, so the bot splits your areas across as many searches as needed (for example 8 ZIPs = two searches) and checks that every area is covered.
- **Redfin's rental search takes one region per saved search**, so 8 ZIPs = 8 Redfin searches. HotPads takes one area per search too.
- **Site filters: for rent (or for sale) plus area only.** In our testing, site filters quietly hid places that fit: a pet filter dropped homes that allowed pets, and Redfin's 'deals' option dropped regular listings. Listing Scout does the filtering for you, and keeps anything a listing doesn't say.
**Alert speed is how often the inbox is read.** A site emails right away, but the text goes out only when Listing Scout next reads its inbox. Reading more often is faster and uses more of your Grok Bot plan.
**Timing, up front:** with `AGENTMAIL_API_KEY` set (secure flow only), `fetch_inbox.py` pulls new Zillow/Redfin/HotPads alert emails into `inbox/` at the top of every loop cycle (dedupes by message id, skips verification/welcome/code emails), so they reach you within one cycle. Without the key, a bot routine copies them on your plan's schedule (Lean twice a day, so up to ~12 hours; Standard every 2 hours; Hands-on hourly). A faster routine (for example every 10 minutes) works too, but each run uses some Grok Bot usage. Property-manager listings are checked every 15 minutes on Lean, or every 5 on Standard and Hands-on.
**Doing it yourself instead** (same settings): on each site, sign in with an account that uses the alerts address (Zillow emails alerts only to the account's own email), search, set the filters above, **Save search**, and pick **Instantly** / **Instant**.
**Also supported (same idea):** Craigslist (saved search email alerts; timing not guaranteed instant), Realtor.com, Zumper, Rent.com.
**Best early source:** ask a local real-estate agent to set an **MLS auto-email** to the alerts address.
**Facebook Marketplace / local groups:** login-only, so check by hand; the bot doesn't log in there.
**Verify each site's email (required, or alerts never arrive):**
- **Zillow:** open "Please verify your email address" in the alerts inbox and follow the link.
- **Redfin:** add a first and last name on the account first (a neutral name like "Listing Scout" works), then open "Please verify your email". If the link expired, request a new one (Redfin rate-limits resends).
- **HotPads:** sign-in is a one-time code sent to the alerts inbox.
**First real alert check:** setup isn't done until one real alert email from a site has been parsed (`out/email_proven.json` appears). Until then the watchdog reports "email path unproven".
**What to expect:** each site first sends welcome and verify emails. Those aren't alerts. The first real alert usually comes when a new place is posted, which can take a few hours or up to a day. Quiet is normal.
**How alert emails reach the bot (pick one):**
- **Grok Bot inbox + routine** (no key needed): the bot's own inbox, copied into `inbox/` by a bot routine on your plan's schedule (or faster if you choose, at more usage). Set `inbox_pull: routine`.
- **AGENTMAIL_API_KEY** (secure flow only): `fetch_inbox.py` pulls at the top of every loop cycle. Set `inbox_pull: api`.
- Neither set up: the bot tells you once (health check), never fails silently.

## Buying a home (mode: buy) — EXPERIMENTAL
> **Experimental (new in v1.1.0):** start every buy setup in shadow mode (`shadow: true`) for about a day, check the would-be texts, then turn on real texts with the owner's yes. At setup the bot says:
>
> "Buying is still new."
>
> "Tell me if anything looks off."
- **Setup asks only five things:** price range, beds/baths, areas, HOA max, and home type (house, condo, townhome). Everything else (sq ft, lot, year built, days on market, open houses) is shown as a detail, never a filter. Unknowns are kept and shown as "not listed yet".
- **Sources:** Zillow, Redfin and Realtor.com for-sale alert emails, with each site search set to **for sale + area only** (no price, bed or other site filters; the scout filters). No property-manager pages.
- **Alerts:** new homes, price cuts ("Now $725,000 (was $749,000)") and back on the market. Coming soon and open-house times show when the email has them. No "/mo" on prices; HOA shows as "HOA $350/mo", "No HOA" or "HOA: not listed yet".
- **Pending or sold:** never a new alert. If someone shortlisted that home, only they get one calm note: "Update on {street}:" / "It's now pending."
- **Pace (default):** standouts (a match within your target price) are texted right away; the rest come in one evening roundup after 6 PM. Say "text me everything right away" or "just the evening roundup" to change it (asks first).
- **Guardrails:** the welcome adds "Not an agent or advice." The bot never contacts listing agents or sellers.
- **Proof run:** set `shadow: true` to parse real alert emails and log would-be texts to `out/shadow_texts.jsonl` without sending.
- **Not advice:** never price, offer, mortgage or investment advice.

## 3. Setup, in order (about 60–90 minutes, 8 steps, plus up to a day for the first alert)
More questions? See `PHOTON_FAQ.md`. The bot's exact wording is in `SETUP_SCRIPT.md`.

1. **Step 1 of 8: Your search, in your words** (2 min). *Why: you see that the bot understood you.* The bot also asks your time zone (`timezone`; default America/Los_Angeles). It repeats your search back; you correct anything.
2. **Step 2 of 8: The promise** (30 sec). *Why: you know the limits first.* See "What I'll always and never do" above.
3. **Step 3 of 8: Photon account and secret** (10–20 min). *Why: Photon sends your texts from a real phone number.*
   - Easiest on a computer or tablet browser. Go to **app.photon.codes** and choose **Continue with Google**.
   - Make a project and name it **Listing Scout**. (The button may look like "New project" or "Create project".)
   - Open **Configure**, then click **Reveal** next to **Project secret**. Paste it only into the bot's **secure box**, never in chat. The Project ID isn't secret.
   - Plans: see photon.codes/pricing. **If Photon asks for payment, a phone number or ID:** stop there and tell the bot what the screen says. Don't enter a card unless you've chosen a paid plan yourself.
   - **Stuck? Tell the bot what you see** (the words on the screen, or a screenshot). It will guide you from there and never guesses at buttons.
   - The secret is saved to `~/.config/listing-scout/env` (private, outside this folder, never printed), so a restart keeps it.
   - ✓ "You're connected to Listing Scout."
4. **Step 4 of 8: Add each person** (5 min). *Why: Photon only texts people on its Users list.*
   - On Photon's **Users** page, add each person's mobile number (iPhone or Android). Your plan sets how many (photon.codes/pricing). Each person gets their own thread; no group chats.
   - iPhone gets iMessage. Android gets regular texts (SMS/RCS), tested once so far.
   - ✓ "You're added. Your texts will come from the number ending {last 4}."
5. **Step 5 of 8: Save it as a contact** (1 min). *Why: alerts then come from "Listing Scout", with a little house photo, not an unknown number that iPhone may filter.*
   - The bot gives you a contact card here in chat. Tap it, then **Create New Contact**.
   - ✓ "Saved. Alerts will show up as Listing Scout."
6. **Step 6 of 8: Send the first text** (1 min). *Why: one message from you opens your line.*
   - From that contact, text anything, like **"hi"**.
   - Required: Photon refuses to text you until you do. Photon assigns each person their own line, so do this even if you've used Photon before.
   - ✓ "Got it. Your line is open."
7. **Step 7 of 8: Approve a sample alert** (2 min). *Why: you choose the format before anything is automatic.* It uses a real listing from today. Examples: `SAMPLE_MESSAGE.txt`.
8. **Step 8 of 8: Costs, plan, and going live** (3 min). *Why: no flood of old listings, and proof it works.*
   - You pick a plan (Lean, Standard or Hands-on; see `COSTS.md`).
   - The bot runs `scout.py --dry-run` (so the trade-off counts are real), then a quiet seed `scout.py --seed` (notes everything listed today; texts nothing about those), then starts watching with `./ensure_running.sh`.
   - You get **one welcome text** with the contact card. It's also the test: it ends with "Did this come through okay?"
   - Then one **"Here's what's out there right now"** text: how many places it checked, how many fit right now, and the top 3 with links.
   - After that, you only hear from it when something new fits.

## Costs and plan modes
Checking listings and texting use no AI. See `COSTS.md` for the cost table and the Lean / Standard / Hands-on plans. Nothing starts until you approve going live.

## Inviting another household member (one forward for you, one text for them)
1. Tell the bot "add my partner" (or a roommate or family member). It sends a **secure form** for their name and number; the number is never typed in chat, and only the last 4 digits are kept.
2. The bot asks you to confirm, then adds them (`notify.py add_user "{Name}" --confirm`). Photon **assigns each person their own Listing Scout line** (the number their texts come from) and their own 1:1 thread. No group chats. How many people you can add depends on your Photon plan (photon.codes/pricing).
3. With your okay, the bot texts **you** two messages on your Listing Scout thread:
```
Here's {Name}'s invite.

Forward the next text.

Press and hold it.

Tap More, then the arrow.

Pick {Name} and press Send.
```
   then the invite itself. Press and hold the invite, tap **More**, then the arrow (Forward), pick them, and press **Send**. The bot never texts them first, and it can't until they text the line.
4. They get this, with no links at all:
```
Hi {first}!

I set up Listing Scout for us.

It texts us homes that fit.

Tap the number to say hi:

{their Listing Scout line, e.g. (555) 000-1234}
```
   They tap the number and say hi. No card to save first.
   Privacy: the invite is a plain text with no links, so no hosted or third-party page ever sees who is invited. iPhone turns the number into a tap target on its own. A raw `sms:` link (`out/invite-{Name}-link.txt`) is kept only as an internal fallback and is never texted.
5. The moment their text arrives, the bot sends their welcome with the **contact card** attached, you get "{Name} is in.", and a minute later they get the same "what's out there right now" snapshot you got. If they haven't texted after about a day, you get one gentle heads-up.
6. They get alerts in the format you approved. Optional: only target-range alerts (`tiers: [target]`) in their CRITERIA entry. Tier words: `target`, `stretch`, `usual` (= above your usual range).
**Welcome text** (sent automatically when they text in; rendered from `style.member_welcome`):
```
Hi {first}!

It's Listing Scout.

{Owner} said you'd stop by.

{Owner} shared the search.

Here's what we're looking for:

{your areas}
{beds}
{price range}
{nice-to-haves or must-haves}

You get {Owner}'s alerts too.

Quiet days mean nothing fit.

Always see a place first.

Not listed yet is normal.

A home may show up twice.

Spot a bug, just let me know.

Did this come through okay?
```

## If something goes wrong
Nothing is broken on your side; there's always one simple next step.
- **"Target not allowed for this project"**
  - That person's line isn't open yet. Have them text anything, like **"hi"**, to the Listing Scout contact, then try again.
  - Still failing? Their iMessage may be registered under a different number or an email. Open **debug.photon.codes** on their iPhone. It tells them which handle they send from. Add that handle on the Users page.
- **The test says it sent but nothing arrived**: check that iMessage is on (Settings, then Apps, then Messages), and make sure Listing Scout is saved as a contact (Step 5), and check the Unknown Senders list.
- **Someone on Android or with iMessage off?** Each line is checked automatically; non-iMessage lines get plain text. Tested once: it arrived as RCS.


## 4. Going live
1. The bot shows you a sample alert built from a real listing today.
2. You approve wording + how many texts/day is OK.
3. Step 8's quiet first run saves everything currently listed as "seen" (no flood). After that only **new** listings, **price drops**, and **relists** (gone 3+ days, then back) are texted.
4. A small script (no AI) checks every 15 minutes on Lean, or every 5 on Standard and Hands-on. It restarts itself after the bot's computer restarts, and a weekly health check makes sure it's still running.
   The first alert goes out right away; anything else in the next hour is held and sent as one numbered text.

## Text style (applies to every text anyone receives)
All texts (alerts, bundles, price drops, welcome, invite note, error hints, relays) go through **one formatter, `style.py`**:
- One sentence per line, and **every full sentence is followed by a blank line**. Exceptions stay grouped: alert facts (beds/baths/type, area, price; garage/available/pets), numbered steps with their intro line, and an address with its link right under it.
- Every line is **one whole thought of 30 characters or fewer**, so it never wraps mid-thought on an iPhone. Nothing is ever wrapped; long sentences are rewritten shorter, and names drop out of a line when they would push it past 30. Exempt: links, a street address directly above its link, and a member's own quoted words.
- After a colon, leave a blank line: an intro line ending in ':' gets a blank line before what follows, and text after an inline colon goes below a blank line, on the next line ('2. Text it:' / 'Hi Listing Scout, I'm in.'). For now, alert fact labels ('Pets: …', 'Garage: …') stay on one line.
- Links always sit alone on their own line.
- Same headlines ("New place that fits 🏡", "A price came down 📉", "Back on the market", "Two new places today 🏡"), and the same close: "No rush." / "I'll keep watching."
- Nothing is sent if it fails the style check.
All rendered examples are in `SAMPLE_MESSAGE.txt`.

## What each text looks like (calm style, the template default)
Short blocks separated by a blank line, short lines, no capitals for emphasis, no stars or tags.
1. Headline: "New place that fits 🏡" / "A price came down 📉" / "Back on the market" / "Two new places today 🏡"
2. Beds, baths, type · area + ZIP · "$3,895/mo" · "In your target range" (each on its own line)
   (the ranges come from your CRITERIA price tiers: target range, stretch range, top of your stretch range, above your usual range)
   Price drop: "Now $3,895/mo (was $4,095)".
3. Garage · available date · pets. Anything the listing doesn't say goes last: "Pets: not listed yet". The bot never guesses.
   Pets lines appear only if you have pets.
   Nice-to-haves (garage, layout) always show as a detail: "Has a garage", "No garage" or "Garage: not listed yet". Never guessed.
4. Optional plain-words context, only with 8+ similar listings seen: "A bit above nearby 2-beds."
   One gentle safety line when something looks off, e.g. "It's far below similar places." or "See it before paying anything."
5. The street address on its own line, directly above its link, so the address labels the link. The link sits alone on the next line (plus a showing link when the manager has one).
6. "No rush. I'll keep watching."
Several matches within the same hour arrive as one numbered text, each with its address and link. Examples: `SAMPLE_MESSAGE.txt`.
Only "fits" listings are texted. **Light filters (default):** in your area, beds_min+ and baths_min+ (unknown kept), price up to your stretch (unknown kept), and pets not explicitly disallowed. Garage and layout are nice-to-haves shown in the alert unless you make them must-haves.

## Extra features (all confirm-first, no AI)
- **Take a break.** Anyone can text STOP and it's instant and silent (no reply; the owner gets one quiet note). "start" turns texts back on. The owner can also say "remove {Name}". I ask "Take {Name} off the search?" and act only on a clear yes. Then they get one goodbye, their replies and likes are deleted, and they're never texted again. Removing them from Photon's Users page stays your choice.
- **Sleep mode.** Off by default, because a 2 AM listing can be gone by 9. After the first late-night alert, I offer it once the next morning ("Want me to?"). If you say yes, finds between 10 PM and 7 AM (`quiet_hours` in CRITERIA) wait and arrive as one bundle at 7 AM. Price drops wait too. Each person chooses for themselves ("sleep mode" / "sleep mode off").
- **Still available?** Only for places someone liked or asked to tour, and only after they've been gone from every feed for about a day (to ride out feed blips). The text says "It's no longer listed." It never says "rented", because we can't know that. If it comes back, it alerts again as usual.
- **One home, one text.** If the same address shows up later from another source (say, a Zillow email hours after the property manager's page), it's attached quietly. It only alerts again if the new price is lower. If an address is missing or unclear, it alerts as usual rather than guess a match.
- **Fine-tune the search.** Text a change in plain words: "add 78745", "go up to 4,500", "stretch to 5.5k", "3 beds is fine". I read it back as one line and ask "Want me to make that change?" Only your yes applies it. Then I back up `CRITERIA.yaml` to `out/`, update it, and re-seed quietly so places already out there don't flood in. If I'm not sure what you meant, I ask; I never guess. A co-decider's suggestion comes to you word for word, and only your yes applies it.
- **We found it.** Only the owner's yes ends the search. If a co-decider says it, their words come to you first. After your yes, everyone gets "Congrats on the new place!", the watcher stops, and I offer once to clear the search data and close the Zillow/Redfin/HotPads saved searches. That happens only on your yes, and then the reply listener stops too.
- **Your data stays put.** See "What I keep" below.

## Make it better (bug or idea, gated)
- Anyone can text a bug or idea in plain words: "bug, the link didn't open", "idea: ...", "suggestion ...", "something's broken". Only clear openers count; anything unsure is handled as a normal reply and relayed.
- The bot asks first: "Send it to the Scout team?" Only a clear yes sends it. A no drops it ("Okay, I won't send it."), and any other text lets the question lapse.
- What is sent: only the person's exact words, the bot VERSION, and the kind of last text they got (alert or welcome). No phone numbers, names, addresses or criteria.
- Where it goes: every item is saved to out/feedback.jsonl with status pending_review. feedback_email is blank by default in CRITERIA.example.yaml, so nothing is emailed. The owner sets their own address to receive items; replies.py then prints a FEEDBACK_EMAIL line and the bot emails it there.
- GATE: nothing is ever auto-queued or built. Items stay pending_review until the owner explicitly approves. `python3 review_feedback.py` lists pending items; `--approve ID` / `--decline ID` only mark them; `--fixed ID` (after an approved fix ships) prints a draft "You asked, it's fixed" text that is never sent automatically.
- The welcome mentions it once: "Spot a bug, just let me know."

## Criteria hygiene (must-have vs nice-to-have, confirm-first)
- Setup asks one plain question per extra: "Is a garage a must-have? / Or just nice to have?"
- Before saving, it shows the real trade-off from current listings (`features.tradeoff()` on `out/pool.json`): "As a must-have, about N fit. / As a nice-to-have, about M." If it can't count, it says "I can't count that one yet." Numbers are never invented.
- Unknown details are kept by default and shown as "<Thing>: not listed yet".
- Weekly near-miss check-in (part of Fine-tune the search): "N places missed only on <thing>. / To see places like these: / <the exact change, e.g. Set your stretch to $5,200.> / Want me to make that change?" A clear yes applies one backed-up CRITERIA change; anything else changes nothing.
- Volume nudge: no matches in 7 days suggests loosening one thing; more than ~5 a day suggests tightening one (e.g. "Make a garage a must-have."). Confirm-first, at most one check-in a week, nothing on day one. Turn it off with `checkins: false` in CRITERIA.yaml (default `checkins: true`).
- **Check-in off switch (per person):** anyone can text "no check-ins" to stop the quiet-week pulse, first-week ask and near-miss check-ins for themselves; alerts keep coming. "check-ins on" turns them back on.

## STOP and deleting data
- Members learn this in their welcome: "Text STOP anytime to stop." "help" adds "Leave takes you off." / "STOP turns texts off."
- **"what can you do"** gets a short, honest list (alerts, replies, shortlist, pause, STOP; owners also hear "Ask me to change the search.").
- STOP, cancel, unsubscribe, end, quit are handled before anything else: no reply, the person is marked stopped, any waiting question is dropped and nothing is applied.
- **"end my search"** (owner only): the bot asks "End your search for good?" and needs a word yes. Then everyone on the search gets one goodbye, the loop and reply listener stop, the bot pauses its own routines, and it offers to delete the data and close the site searches. Last step for you: remove people on Photon's **Users** page (and cancel a paid Photon plan, if you have one).
- Delete everything and clearing search data need a word yes ("yes", "yes please", "do it", "go ahead"); "k" or 👍 doesn't count.

## Tapbacks and channels
- Tapbacks (Liked, Loved, Laughed at…) are never relayed as typed words; they're passed on as a short note, like "Sarah ❤️ Maple St."
- Each person's line is checked automatically (iMessage vs SMS/RCS). Non-iMessage lines get the plain-text version: no emoji, no contact card, Android forwarding steps. If the check can't tell, it falls back to iMessage. Tested: a plain-text test reached an iPhone with iMessage off as RCS.

## Alert extras (calm, never invented)
- **Via line:** each alert says where it came from: "Via Redfin" or the manager's name (`show_source: false` hides it).
- **The listing's own apply or agent link (when the email has one):** alerts show "Apply link from the listing:" followed by the link. Only links the email labels that way ("Apply now") are used. Tracker links are unwrapped only when the real address is inside them, tokens are dropped, and opaque links are skipped. The bot never opens these links, applies or contacts anyone. Real Zillow and Redfin alerts seen so far had no such link, so expect it rarely.
- **Posted about N min ago (best-effort):** only when the source gives a real posting time; otherwise no line. Not yet seen on a live alert email.
- **Quiet-week pulse:** after 7 days with no alert texts, one note: "Quiet week, still watching." / "I checked N places." (real count) / "Nothing new fit yet." / "Say no check-ins to skip." Then nothing until another quiet week.
- **Daily cap (off by default):** say "max 3 texts a day" and the bot asks first; extras wait for one evening text after 6 PM. "No daily cap" turns it off (also confirm-first).
- **First-week ask:** once, about day 4, the owner gets "A few days in." / "Anything bugging you so far?" / "Say no check-ins to skip." A real answer goes into Make it better (it still asks before sending anything).

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
- Never tell people to reply. Replying is offered as a gentle option, never a command ("I'll pass your thoughts to {owner}.", "Pause works anytime."). Decide together is mentioned once, as a benefit, in the welcomes. The only "Reply ..." line is the first-text receipt, "Did this come through okay?"
- A relayed reply is the person's own words, exactly as written. Only the header ("Alex on Main:") follows the style.
- Anything unknown says "X: not listed yet", and goes last.
- Keep every line to 30 characters or fewer (an iPhone wraps at about 30). Rewrite shorter; never wrap.

## Edge cases it handles
- Same home on two sites at two prices: one alert, lower price first, "Also $X/mo on Site".
- Gone, then back cheaper (even under a new listing id, same address): one "Back, and lower 📉" alert.
- Missing rent, beds, or address: "not listed yet". Never guessed.
- Scam signals (far below similar places, money before a tour): one gentle caution line, never more.
- A busy day (10+ fits): the best 5, then "And N more fit today."
- Two people reply at once: relayed in the order they arrived.
- A reply with no street right after a newer alert: it asks which place, once.
- Photo or voice reply: forwarded as is if Photon allows it; if not, the other person hears "I can't pass a photo along yet." (unverified live)
- STOP: honored at once, no reply (the carrier sends its own); the owner gets a gentle note. "start" turns texts back on. ⚠️ Carrier/CTIA rules for STOP depend on Photon's sender type and are unverified.
- "leave": "Sarah left the search." to the owner; their replies are deleted and they're never texted again. A new number means adding them again.
- Owner says "remove Sarah": asks first; on yes, a goodbye, their replies deleted, never texted again.
- Per-person tiers (`tiers:` on a recipient); one shared shortlist.
- If you set `photon.user_limit`, adding someone past it is refused before anything changes.
- A source or Photon hiccup: quiet retries; the owner hears only if a source is down for over a day.
- Box restart: the watcher comes back by itself; seen listings are saved, so no repeat alerts.
- "We found a place": the owner confirms, everyone gets a warm goodbye, the watcher stops, and the owner is offered (once) a data clear-out plus closing the saved searches.
