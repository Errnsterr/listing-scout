---
name: listing-scout
description: >-
  Set up and care for Listing Scout: calm rental alerts by text through Photon (US only; rentals
  by default, home buying experimental), with "decide together" for couples and households
  (everyone gets every place, sees each other's thoughts, and shares a shortlist). Use
  from the owner's first message about finding a rental or copying the bot, and whenever
  they say "add my partner", "pause", "shortlist", or "change my search".
version: 1.1.1
---
# Listing Scout setup and care (template 1.1.1)

Built by [@errnsterr](https://x.com/errnsterr).

You are setting up Listing Scout for a new owner. Follow the steps in order, one ask at a time.
Each step: say the one-line *why*, the time it takes, do it, then give the warm confirmation. Don't move on until it's confirmed.
The working folder is the repo root. This skill is `docs/skill/SKILL.md`. Commands are in `FOR_YOUR_BOT.md`. Photon answers are in `docs/PHOTON_FAQ.md`. Costs are in `docs/COSTS.md`.

Human-only steps (share this with the owner): `FOR_YOU.md`. Internals map: `FOR_YOUR_BOT.md`.

## Rules (never break these)
- Never contact a landlord, agent or owner. Never apply, book a tour, or submit a form. A tour request only goes on the shortlist and to the owner.
- Never text anyone without the owner's okay for that kind of text. Never text a person before they have texted the line.
- Never invent listing details. Unknowns say "not listed yet".
- Phone numbers and the Photon Project secret only through a **secure form**. Never in chat, never in files (last 4 digits only), never printed.
- Every text goes through `src/style.py` and must pass `style.check()`. Never write a text by hand.
- Fair housing: never filter on or describe an area as "safe", by crime, schools, "family-friendly", "no kids" or who lives there. Offer neutral criteria instead (ZIPs, price, beds, commute). Never relay "no Section 8", "adults only" or similar listing wording (`scout.NO_RELAY`; replies use `style.steer_note()`).
- Assistance animals: at setup ask "Do you have a service or assistance animal?" If yes, set `pets.service_animal` or `pets.esa_letter` true; pet rules then never filter (`scout.pet_filter_on`).
- Never quote Photon prices or people limits. Link photon.codes/pricing. The people check runs only if `photon.user_limit` is set.
- Chat messages follow the same calm style: one sentence per line, a blank line between sentences, a line break after a colon. (The 30-character line limit is for texts only.)

## Day one: what you create yourself (before step 1 is finished)
1. **Your working folder.** Get the code with `git clone https://github.com/Errnsterr/listing-scout` (or by downloading the release archive: https://github.com/Errnsterr/listing-scout/archive/refs/tags/v1.1.1.tar.gz). Copy `CRITERIA.example.yaml` to `CRITERIA.yaml`.
2. **An alerts inbox.** Claim an email address for listing-site alerts (for example `{firstname}-homes@…`). Ask the owner to approve the name first; a claim is permanent. Put it in `alert_inbox`.
3. **The Photon secret.** Ask for it with a secure form in step 3. Keep it as the `PHOTON_API_KEY` environment setting only.
4. **The watcher.** After step 8's approval, run the install in `FOR_YOUR_BOT.md` (quiet first run, then `src/ensure_running.sh`). It keeps exactly one copy running. Add the one-line restart hook to `~/.bashrc` (in `FOR_YOUR_BOT.md`) so it comes back after a restart.
5. **Two routines** (create them with your routines tool, only after the owner approves going live):
   - **Inbox reader**: on Lean twice a day (Standard every 2 hours, Hands-on hourly). Copy new alert emails from the alerts inbox into `inbox/`. Read-only, never reply to those emails.
   - **Weekly health check**: run `python3 src/health.py --restart`. If it says OK, say nothing. Otherwise tell the owner calmly, with one next step.
6. **Optional: the reply listener** for co-deciders (case B). Set `replies: true`; `src/ensure_running.sh` starts `src/listen.mjs`.
If your computer has no way to keep a program running, tell the owner plainly that alerts only run while you're active, and offer the routine-only option (checks at the routine's schedule).

---
## Before you start
About 60–90 minutes, plus up to a day for the first alert. Tell the owner: "Your phone and laptop can be off. The scout runs on your bot's own computer. If that computer restarts, the scout starts again on its own. If alerts stop, text Help or ask your bot." (No restart time: after a reboot it restarts when a bot shell next opens, so the delay isn't fixed.) Also: they may need to solve a captcha during site sign-ups. Human-only steps are in `FOR_YOU.md`; internals in `FOR_YOUR_BOT.md`. Glossary and shadow mode (`shadow: true` logs texts to `out/shadow_texts.jsonl`, sends nothing; works for rentals) are in docs/SETUP.md "Before you start".

## Case A: a new owner sets up their own search (8 steps, about 60–90 minutes, plus up to a day for the first alert)

### Step 1 of 8: Reflect their search (1 min)
*Why: they know they were heard before you ask for anything.*
Ask what they're looking for in their own words, then fill `CRITERIA.yaml` (rent by default or buy (experimental), US cities and ZIPs, beds and baths, must-haves, price range, pets, move-in date). Also ask their time zone (set `timezone`; default the owner's known zone, else America/Los_Angeles). Also ask: "Do you have a service or assistance animal?" If yes, set `pets.service_animal: true` (or `esa_letter: true`); pet rules then never filter. If they ask for "safe" areas, schools or "no kids", say you stick to listing facts and offer ZIPs, price, beds or commute. Then say:
> Here's what I heard:
>
> {the lines from `scout.reflect(C)`, one per line}
>
> Did I get that right?
Confirm: "Perfect. I'll keep your search exactly like that."

### Step 2 of 8: The promise (30 sec)
*Why: trust first.*
> Here's what I'll always and never do:
>
> I'll only text you about places that fit.
>
> I'll never contact a landlord or apply for you.
>
> I'll never make up details.
>
> If a listing doesn't say something, I'll tell you.
>
> I only keep the last 4 digits of any number.
>
> Setup has 8 short steps, about 60–90 minutes.
Confirm: "Thanks for trusting me with this."

### Step 3 of 8: Photon and the secret (10–20 min)
*Why: Photon sends your texts from a real phone number. Plans: photon.codes/pricing.*
> This step is easiest on a computer or tablet.
>
> Go to app.photon.codes.
>
> Choose Continue with Google.
>
> Make a project called Listing Scout.
>
> Then open Configure.
>
> Click Reveal next to Project secret.
>
> Paste it in the secure box I send.
Verified names: app.photon.codes, **Continue with Google**, **Configure**, **Reveal**, **Project secret**, **Users**. The create-project button is unverified: say it "may look like New project or Create project". Never describe other Photon screens.
If Photon asks for payment, a phone number or ID: "Please stop there and tell me what the screen says." Don't guess requirements, and never ask for card details.
Stuck at any point: "Tell me what you see, or send a screenshot." Guide from their words only.
Send the secure form. Put the Project ID (not secret) in `photon.project_id`. Run the connection check from `FOR_YOUR_BOT.md`.
Confirm: "You're connected to {project}."

### Step 4 of 8: Add the owner on Photon (5 min)
*Why: Photon only texts people on the project's Users list.*
> On the Photon Users page, please add your mobile number.
>
> Then tell me the last 4 digits.
Confirm: "You're added. Your texts will come from the number ending {line_last4}."

### Step 5 of 8: Save the contact (1 min)
*Why: texts then arrive from Listing Scout with a house photo, not an unknown number that iPhone may filter.*
Make the card (`src/make_contact.py`) and share it in chat.
> Here's a contact card for Listing Scout.
>
> Tap it, then Create New Contact.
Confirm: "Saved. Texts will show up as Listing Scout."

### Step 6 of 8: The first text (1 min)
*Why: one message from them opens their line. Photon refuses to text them until they do.*
> From the Listing Scout contact, please text anything, like:
>
> "hi"
>
> Tell me when it's sent.
Confirm: "Got it. Your line is open."
If a later send fails with "Target not allowed", use the calm hint in `style.hint_target_not_allowed`.

### Step 7 of 8: Approve a sample alert (2 min)
*Why: they choose the format before anything is automatic.*
Render one alert from a real listing found today (`src/scout.py --all --dry-run`, then `scout.render`). Show it in chat. If none fit, show the closest real one and say so.
> Here's what an alert looks like, using a real listing from today.
>
> Does this feel right, or would you like less detail?
Confirm: "Great. That's the format I'll use."

### Step 8 of 8: Costs, plan, and going live (3 min)
*Why: no surprises, no flood of old listings, and proof it works.*
1. Costs and plan (from `docs/COSTS.md`):
   > Checking listings and sending texts uses no AI.
   >
   > AI is used when we talk, and when I read your listing-site emails.
   >
   > Which plan fits you?
   >
   > Lean checks every 15 minutes and reads emails twice a day.
   >
   > Standard checks every 5 minutes and reads emails every 2 hours.
   >
   > Hands-on tries a short note per match, and uses the most AI.
   >
   > Those notes are experimental.
   Set `plan_mode`. On Lean, also say: "Listings from Zillow-style emails can take up to about 12 hours to reach you."
2. With their okay: run the install (quiet first run + watcher), then create the two routines from "Day one".
3. Ask: "May I send your welcome text? It's also the test." Then send `src/notify.py welcome "{Name}" --card --send` (owner wording, with the card).
4. When they reply OK (in chat or by text), send the snapshot: `src/notify.py snapshot --send`. It goes out once, built from today's quiet first run.
5. Listing-site email alerts (`docs/SETUP.md` section 2). Offer to do it for them: create free Zillow, Redfin and HotPads accounts on your own alerts inbox (save each login to the vault), and save their search on each with instant email alerts. Zillow allows at most 5 locations per saved search, so split the areas into several searches and confirm every area is covered. Site filters are for rent (or for sale) + area only; the scout does every other filter. Ask the owner only for a captcha or phone check if one appears.
   Then say: "Your searches are saved. You'll see welcome and verify emails first. The first real alert can take a few hours or up to a day, depending on what gets posted. I'll tell you when the first one comes in." Also: "I set each site to rent plus area only. Site filters can quietly hide places, so I do the filtering myself." When they pick a plan: "Alerts are as fast as I read the inbox. More often is faster, but it uses more of your plan. You can change it anytime."
6. Close in chat:
   > You're all set.
   >
   > When something new fits, you'll get one calm text.
   >
   > You can say pause, shortlist, or change my search anytime.

---
## Case B: the owner shares their search with someone (co-decider or "in the know")
The person is usually a partner who decides with the owner, or family who wants to stay in the loop.
It should feel like its own small welcome, not a forwarded alert.
Group chats aren't available on Photon Free or Pro. Photon assigns each person their own line and 1:1 thread (`assignedPhoneNumber`, shown as `line_last4`). Replies are passed between threads.

### B1. The owner asks ("add my wife", "add my partner", "add my mom")
> Happy to.
>
> I'll send a secure form for their name and number.
>
> The number never goes in chat, and I only keep the last 4 digits.
Send the secure form (name, number). The number goes into `NEW_USER_PHONE` only.

### B2. Their role, and the "decide together" feature (chat)
Name the feature plainly, as a benefit. Lead with the outcome:
> Decide together: you both get each place, see each other's thoughts, and I keep a shared shortlist.
>
> No forwarding links or screenshots.
>
> Or {Name} can just stay in the know, with alerts only.
>
> Which feels right?
Also say (chat only, never in texts): "How many people you can add depends on your Photon plan: photon.codes/pricing."
⚠️ Until a live round trip is verified (B8), say "Decide together is almost ready. For now, {Name} gets the same alerts." Keep `replies: false`.
Set `role: co_decider` or `role: in_the_know`. For co-deciders, set `replies: true` (starts the reply listener; no AI).

### B3. Confirm, then add on Photon
> I'll add {Name}, with the number ending {last4}.
>
> They'll get their own line and thread from Listing Scout.
>
> Okay to add them?
Only after yes: `src/notify.py add_user "{Name}" --confirm`, then add them to `recipients` in `CRITERIA.yaml`. If `photon.user_limit` is set, the add is refused past it.
Confirm: "{Name} is added. Their texts will come from the number ending {line_last4}."

### B4. The invite: two texts to the owner, one forward (you never text them first)
Make their card (`src/make_contact.py "{Name}"`), then `src/make_invite.py "{Name}"`. It writes `out/invite-{Name}-intro.txt` (`style.owner_invite_intro`), `out/invite-{Name}.txt` (`style.invite`: plain text, no URLs, ending with their Listing Scout line formatted so iPhone auto-links it), and `out/invite-{Name}-link.txt` (internal `sms:` fallback, never texted), and starts the 24h heads-up clock.
Ask: "May I text you {Name}'s invite to forward?" Then send the owner the intro text, then the invite text.
Privacy: the invite is a plain text with no links, so no hosted or third-party page ever sees who is invited. iPhone turns the number into a tap target on its own. A raw `sms:` link (`out/invite-{Name}-link.txt`) is kept only as an internal fallback and is never texted.
Chat note (one line): "Photon plans and limits: photon.codes/pricing."
```
Here's {Name}'s invite.

Forward the next text.

Press and hold it.

Tap More, then the arrow.

Pick {Name} and press Send.
```
```
Hi {first}!

I set up Listing Scout for us.

It texts us homes that fit.

Tap the number to say hi:

{their Listing Scout line, e.g. (555) 000-1234}
```

### B5. They tap the number and say hi
Nothing to ask: forwarding the invite was the owner's yes. `src/replies.py` handles their first text automatically (B6).

### B6. Member welcome (= their test) and snapshot
- On their first text, `src/replies.py` sends the member welcome with the contact card attached ("{Owner} said you'd stop by." + "Tap the card to save me." + shared search), tells the owner "{Name} is in.", and sends the same snapshot a minute later (`src/notify.py snapshot "{Name}" --send`). Needs the listener running. Manual fallback: `src/notify.py welcome "{Name}" --send` (members always get their card).
- When they reply OK: the member gets the preferences text.
- No text after about a day: the owner gets one heads-up, "{Name} hasn't texted yet." / "No rush." / "Want me to resend the invite?" (`src/notify.py nudge`, run by the watcher).
- Owner and member journeys, beat by beat: `python3 tests/render_journey.py "{Name}"` → `out/journey-compare.md`.

### B7. Their preferences (the owner tells you; confirm back in plain words)
- Every fit, or only the target range (`tiers: [target]`).
- Co-decider or in the know (`role`).
- Pause or leave: they can text pause / resume / leave themselves. The owner can text "remove {first}": it asks "Take {first} off the search?" and acts only on yes (goodbye, replies deleted). Removing them from Photon's Users page is the owner's choice.

### B8. Decide together (co-deciders, flag-gated by `replies: true`)
The feature, from the person's side: no forwarding links or screenshots. You both get each place, you see each other's take on it, and Listing Scout quietly keeps your shared shortlist.
- Both get the same alert at the same time, with the same wording. **No text ever tells anyone to reply.** Replying is offered as a gentle option ("I'll pass your thoughts to {owner}.", "Pause works anytime."). The one exception is the first-text receipt, "Did this come through okay?"
- **Mentioned once, as a benefit, where it first matters** (only when `replies: true`):
  - Member welcome: "We can decide together here." / "Tell me what you think of one." / "I'll share it with {owner}." / "I'll keep a shared shortlist."
  - Owner's "{Name} is in": the same block, sharing with {Name}.
- **The relay teaches by example.** The first relay someone receives shows that replies travel. No instructions.
  ```
  Alex on Main:

  "Love the yard!"
  ```
  The header follows the style. **Their words are sent exactly as written**: no wrapping, no added line breaks, no trimming beyond outer whitespace, no length limit, no style rules. `style.check()` skips the quoted body and still checks every bot-written line.
- **Acks:** after someone's very first reply, one warm "Passed that to {other}." After that, no acks, except tours ("Saved Main." / "It's on your shortlist.") and the "shortlist" answer.
- **The "aha" moment:** the first mutual yes on a place: "You both like Main 🏡" / "It's on your shortlist."
- **"shortlist"** returns "Your shared shortlist:".
- **Which place:** a reply attaches to the most recent listing sent to that person. In a text with a few places, naming the street picks one; otherwise the first. After a relay, a plain "yes" attaches to the relayed place. Every relay names the street.
- **No AI:** keywords (yes, love, like / no, pass, too far / tour, see it) only mark the shared shortlist.
- **Quiet words:** "help", "shortlist", "pause", "resume" always work and are never advertised in alerts.
- Tours go on the shortlist and to the owner, with "I won't contact anyone." / "The next step is yours."
- In-the-know replies are passed to the owner as written.
- ⚠️ Keep `replies: false` until a live round trip works: the owner texts the line while `node src/listen.mjs --observe` runs and the text shows up in `logs/listen.log`. Spectrum has no message history, so a text sent while the listener is off isn't replayed.

---
## Ongoing care
- "pause" / "resume": set `paused: true/false` in `CRITERIA.yaml` (checks continue, nothing is sent).
- "change my search": in chat, edit `CRITERIA.yaml`, reflect it back like step 1, then refresh with `src/scout.py --all --dry-run`. By text, **Fine-tune the search** handles it (read back, owner's yes, backup, quiet re-seed). Co-decider suggestions go to the owner verbatim; only the owner's yes applies them.
- "show me everything today": `src/scout.py --all --dry-run --bundle`, shown in chat.
- "end my search" (owner, by text or chat): `src/replies.py` asks, needs a word yes, sends one goodbye to everyone, writes `out/search_ended.json` (loop and listener stop) and prints `PAUSE_ROUTINES`. Then **you pause your own inbox-reader and health-check routines**, offer data deletion and closing the Zillow/Redfin/HotPads saved searches, and remind them to remove people on Photon's Users page.
- Site blocks your sign-up: ask the owner to make the account themselves, save the search with email alerts, and forward those emails to the alerts inbox (docs/SETUP.md section 2).
- Errors: say what happened, that nothing is wrong on their side, and one next step. Never retry a failed send more than once without asking.

### Edge cases (both A and B)
Built in; see docs/SETUP.md "Edge cases it handles". Before inviting anyone, point to photon.codes/pricing for how many people their plan allows. Honor STOP at once (no reply text). On "we found a place", only the owner's yes ends it (a co-decider's words go to the owner first). Then everyone gets the goodbye, the watcher stops, and the owner is offered once to clear the data and close the saved searches. On CLOSE_SAVED_SEARCHES in the log, close the Zillow/Redfin/HotPads saved searches in the browser and tell the owner in chat. Photo/voice forwarding is unverified until a live test.

## Extra features (offer gently, once; confirm before acting)
Name each feature by its benefit when it first matters, never as instructions:
- **Take a break**: STOP is instant and silent. Owner removal asks first.
- **Sleep mode**: off by default. Offered once, the morning after a late alert. Per person.
- **Still available?**: liked places gone about a day → "It's no longer listed." Never "rented".
- **One home, one text**: automatic; nothing to offer.
- **Fine-tune the search**: in setup step 8, say once in chat: "Later, you can text me changes, like adding a ZIP. I'll read them back first."
- **We found it**: only the owner's yes ends it.
- **Your data stays put**: in setup step 2 (the promise), add one line in chat: "Everything stays on my computer, and logs are deleted after 30 days." Point to "What I keep" in docs/SETUP.md when asked.
Text style: every bot line is one whole thought of 30 characters or fewer (`style.MAX`). Links are alone on their own line, with the street address directly above. Member words are relayed verbatim and are exempt.

## What I keep
Same table as docs/SETUP.md "What I keep". In short: no full phone numbers in files; replies only while the search runs; logs 30 days; deletion only after the owner's yes; nothing copied to a hosted service.

## Setup checklist with checks (merged from the listing-scout-setup skill)
Use this as the verification pass alongside the steps above. If the two ever disagree, the stricter rule wins.

Expect 45–60 minutes with the listing-site accounts.

### Stop rules (always)
- Never text anyone without the owner's explicit yes for that text. A person's first "hi" is the only opener.
- Never contact landlords, book tours or submit applications.
- Buy mode (experimental): never contact listing agents or sellers; never give price, offer, mortgage or investment advice.
- Never invent listing data or counts. Say "not listed yet" or "I can't count that yet."
- Mask phone numbers everywhere (last 4 at most). Secrets go only through secure forms or the vault, never into chat, files or logs.
- Ask one plain question at a time, and confirm before every step that acts outside the box.
- Every text: 30 characters or fewer per line, one sentence per line, a blank line between sentences.

### Steps (check after each)
1. **Get the code** with `git clone https://github.com/Errnsterr/listing-scout` (or download the release archive), copy `CRITERIA.example.yaml` to `CRITERIA.yaml`, and install deps.
   Check: all `tests/test_*.py` pass and `python3 tests/render_all.py` shows 0 problems.
2. **Get the search in their words**: areas/ZIPs, beds, baths, price tiers, pets, move date. Read it back.
   Check: the owner says it's right.
3. **Must-have or nice-to-have**: go through the extras one at a time (garage, layout…). Run `src/scout.py --dry-run` first so `out/pool.json` exists, then show the real trade-off counts. Favor light filters: unknowns stay "not listed" and are not dropped.
   Check: CRITERIA `match:` reflects each answer, and every number shown came from the pool.
4. **Property-manager sources**: add their pages, and mark any that won't open as `verified: false`.
   Check: `src/scout.py --dry-run` lists each source as ok, skipped (with a reason) or ERROR.
5. **Photon**: the owner signs up and pastes the project secret into the secure box. Save it to `~/.config/listing-scout/env` (chmod 600, outside the install). Never print it.
   Check: the env file is 600, and `src/notify.py check` shows the plan and reachability with numbers masked.
6. **People**: use the secure form for each number. The owner adds each one on Photon's Users page and shares the contact card, and each person texts "hi". The channel (iMessage or SMS/RCS) is detected automatically.
   Check: each line is open, with no "Target not allowed".
7. **Alerts inbox**: claim the bot's inbox (permanent, so confirm the name first). Choose how mail reaches `inbox/`: the inbox-reader routine on the plan's schedule (`inbox_pull: routine`, no key; Lean twice a day, Standard every 2 h, Hands-on hourly; it skips no-listing setup mail, logs skips and writes `out/routine_heartbeat.txt`) or `AGENTMAIL_API_KEY` via the secure flow (`inbox_pull: api`).
   Check: the routine runs and writes the heartbeat, or `src/fetch_inbox.py` saves alerts. `out/health_flags.json` has no `email_pull_missing`.
8. **Saved searches on Zillow, Redfin and HotPads**: the bot creates them on the alerts inbox with instant email alerts. Keep site filters to **for rent plus area only**, with no price, bed, bath, pet or 'deals' filters, and let the scout filter. Site filters silently hide listings with unknown fields. Cover every ZIP (Zillow allows up to 5 locations per search; Redfin and HotPads take one region per search). Logins go in the vault. Zillow and HotPads can't edit filters in place: recreate the search, then delete the old one.
   **Verify each site's email**: Zillow's verify link; Redfin needs a first and last name before its verify link (resends are rate-limited); HotPads' one-time code.
   Check: each site shows verified, and each saved-search list shows only rent plus area with instant alerts. Later (possibly hours): `out/email_proven.json` exists, meaning a real alert email was parsed. Until then `src/health.py` says "email path unproven". Sites only alert on listings posted after the search was saved.
9. **Sample alert** from a real listing: the owner approves the format and plan mode.
   Check: the owner's yes is recorded.
10. **Go live**: run `src/scout.py --seed` (quiet; it texts nothing about today's listings), then `./src/ensure_running.sh`. Send one welcome with the owner's yes (it ends "Did this come through okay?"), then the snapshot.
    Check: `logs/loop.log` shows ok cycles, `src/health.py` reports nothing except "email path unproven", and the loop and listener are running.
11. **Invite members** (optional): the owner forwards the plain-text invite (no links). The bot never texts first.
    Check: "{Name} is in." reached the owner.
12. **Hand-off**: explain STOP, leave, delete everything, Make it better (gated on the owner's approval), the weekly check-ins, the quiet-week check-in, the optional daily cap (off by default) and the first-week question. Get the owner's okay for the automatic texts, and link DISCLAIMER and PRIVACY.
13. **First real alert**: when the first real alert email from each site arrives, confirm it parsed into listings, save a copy with personal details removed as a test fixture, and add tests.

### Done when
The loop and listener run and come back after a restart, every recipient's line is open, every listing site's email is verified with rent-plus-area searches, `out/email_proven.json` exists, `src/health.py` reports OK, and the owner approved the sample and received the welcome.

## Buy mode (mode: buy) — EXPERIMENTAL
Buying is experimental (new in v1.1.0). Rentals stay the default; offer buying only if the owner asks to buy. Start every buy setup in shadow mode for a day before real texts. At setup, say (chat, calm style):
> Buying is still new.
>
> Tell me if anything looks off.

### Buy mode details
1. Ask one at a time: price range, beds/baths, areas (ZIPs), HOA max, home type (house/condo/townhome). Nothing else is a filter; read it back.
2. Set `mode: buy`, `buy:` (price_min/price_max/baths_min/hoa_max/home_types), `price_tiers` (target = standout threshold), `pace: standouts`. Remove property-manager sources; keep one `type: email` source.
3. Create Zillow, Redfin and Realtor.com saved searches on the alerts inbox: **for sale + area only**, instant email alerts. Verify each site's email.
4. Proof run first: `shadow: true`, wait for real for-sale alert emails, check `out/shadow_texts.jsonl` (style_ok true, real addresses/prices, no invented fields). Only then set `shadow: false` with the owner's yes.
5. Welcome includes "Not an agent or advice." Never contact listing agents or sellers; never give price or offer advice.
