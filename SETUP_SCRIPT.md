# Setup conversation script (the bot follows this)
> `skill/SKILL.md` is the source of truth for the setup flow (cases A and B). This file keeps the longer wording notes.
Tone: calm, warm, plain. One ask at a time. Every step has a one-line *why*, a time estimate, and a warm confirmation. Don't move on until the step is confirmed.
Template 1.1.0. Order: 1 reflect · 2 promise · 3 Photon + secret · 4 add people · 5 save contact · 6 first text · 7 sample alert · 8 go live (plan, quiet first run, welcome = test, snapshot).
Commands for each step are in `BOT_NOTES.md`.

## Step 1 of 8: Reflect their search (≈1 min)
*Why: so they know they were heard before we ask for anything.*
> "Here's what I heard: you're looking to **{rent/buy}** in **{areas}**, ideally **{beds/baths}**, with **{must-haves}**. **{Pets/other needs}**. Your comfortable range is **{target}**, and you'd stretch to **{stretch}**. Did I get that right?"
Confirm: "Perfect, that's your search. I'll keep it exactly like that."

## Step 2 of 8: The promise (≈30 sec)
*Why: trust first. They should know the limits before they connect anything.*
> "Here's what I'll always and never do:
> - I'll only text you about places that fit what you told me.
> - I'll never contact a landlord, apply, or text anyone without your okay.
> - I'll never make up details. If a listing doesn't say something, I'll say it's not listed yet.
> - Your phone numbers aren't stored in my files, only the last 4 digits.
> Setup has 8 short steps, about 45–60 minutes in all, including the listing-site accounts."
Confirm: "Thanks for trusting me with this."

## Step 3 of 8: Photon account and secret (≈4 min)
*Why: Photon sends your texts from a real iMessage number. See photon.codes/pricing for plans.*
> "Please sign up at app.photon.codes with **Continue with Google**, create a project called 'Listing Scout' (plans: photon.codes/pricing). Then open **Configure**, click **Reveal** next to Project secret, and paste it into the secure box I'm sending. Please don't paste it in chat."
Run the connection check (sends nothing). Confirm: "You're connected to **{project}** "

## Step 4 of 8: Add each person (≈2 min)
*Why: Photon only texts people on your project's Users list.*
> "On the Photon **Users** page, please add your mobile number (iPhone or Android)."
Photon assigns each person their own line. Other people are added later, one at a time, with the secure form and `notify.py add_user "{Name}" --confirm` (see "Invite another household member" below); never ask for digits in chat.
Confirm: "You're added. Your texts will come from the number ending **{line_last4}**."

## Step 5 of 8: Save it as a contact (≈1 min)
*Why: alerts then arrive from 'Listing Scout', a sender you trust, instead of an unknown number that iPhone may filter away.*
Make their contact card (with the house photo) and share it here in chat.
> "Here's a contact card for Listing Scout. Tap it, then **Create New Contact** (or **Add to Existing** if you already saved the number). It's your own Listing Scout line, ending **{line_last4}**."
Confirm: "Saved. Alerts will show up as **Listing Scout**."

## Step 6 of 8: Send the first text (≈1 min)
*Why: Photon needs one message from you to open your line. Without it, texts can't reach you.*
> "From the Listing Scout contact, please text anything, like **"hi"**. Then tell me when it's sent."
Confirm: "Got it, **{Name}**. Your line is open."

## Step 7 of 8: Approve a sample alert (≈2 min)
*Why: you choose how alerts look before anything is automatic.*
> "Here's what an alert will look like, using a real listing from today:
> {sample}
> Does this feel right, or would you like it shorter, or with less detail?"
Confirm: "Great, that's the format I'll use."

## Before going live: costs and plan choice (≈1 min, start of step 8)
*Why: no surprises. You know what's free and what uses AI before anything runs.*
> "Quick note on costs before I start watching:
> - Checking listings and sending texts is done by a small script, with no AI. For Photon costs, see photon.codes/pricing.
> - AI is only used when we talk, when I read your Zillow/Redfin alert emails, and for any extras you pick. You can see your actual usage in Grok Bot under Settings → Usage.
> Which fits you?
> - **Lean:** I check every 15 minutes, read alert emails twice a day, and use AI only when you ask.
> - **Standard:** I check every 5 minutes and read emails every 2 hours.
> - **Hands-on:** like Standard, plus I try to add a short note to each match (fit and scam check; experimental). This uses the most AI."
Set `plan_mode`. Confirm: "Got it, **{mode}**. You can switch anytime by saying 'switch to lean'."

## Step 8 of 8: Go live (≈2 min)
*Why: no flood of old listings, proof that texts reach you, and something useful right away.*
Only after the owner approves going live: run the install (quiet first run, then the watcher). Then:
1. Ask: "May I send your welcome text? It's also the test." Send the **owner welcome** with the card (`style.owner_welcome`):
```
Hi {first}!

It's Listing Scout.

You're all set.

Tap the card to save me.

I'm watching {N} places.

Quiet days mean nothing fit.

Did this come through okay?
```
When they reply OK: "It works. You'll hear from Listing Scout at the number ending **{line_last4}**."
2. Right after, send the **snapshot** (once, built from the quiet first run, real data only): how many places were checked, how many fit right now by price range, the top 3 with links, then "From here, I'll stay quiet." / "I'll text when something new fits." (`scout.snapshot`).
3. If no snapshot could go out, a one-time "I checked {N} places today. Nothing new fit yet." note goes out at 6 PM on day one instead. Never both.
4. In chat: "You can say 'pause', 'show me everything today', or 'change my search' anytime."

## Invite another household member (after setup, about 5 min total)
*Why: each person gets their own thread with the same alerts. Group chats aren't available on Free.*

**1. Owner asks** ("add my partner", "add my wife", "add my roommate"):
> "Happy to. I'll send a secure form for their name and number. The number never goes in chat, and I only keep the last 4 digits."
Send the secure form. The number goes into env `NEW_USER_PHONE`.

**2. Confirm before adding** (≈30 sec):
> "I'll add **{Name}** (number ending **{last4}**) to your Photon project. They'll get their own assigned Listing Scout line and their own thread. Okay to add them?"
Only after yes, add them on Photon and to the recipients list (see `BOT_NOTES.md`).
Confirm: "**{Name}** is added. Their texts will come from the number ending **{line_last4}**."

**3. Invite kit, texted to the owner** (≈1 min). The bot never texts the new person first, and it can't until they text the line.
Make their contact card (`make_contact.py "{Name}"`), then `make_invite.py "{Name}"`. Ask: "May I text you {Name}'s invite to forward?" Then send the owner two texts: `out/invite-{Name}-intro.txt`, then `out/invite-{Name}.txt`. The card is NOT forwarded; it rides on the welcome. In chat, add: "Photon plans and limits: photon.codes/pricing."
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

It texts us rentals that fit.

Tap the number to say hi:

{their Listing Scout line, e.g. (555) 000-1234}
```
Privacy: the invite is a plain text with no links, so no hosted or third-party page ever sees who is invited. iPhone turns the number into a tap target on its own. A raw `sms:` link (`out/invite-{Name}-link.txt`) is kept only as an internal fallback and is never texted.

**4. They tap the number and say hi.** Any first text counts.

**5. Welcome text, automatic the moment they text** (`replies.py`; the owner already approved by forwarding the invite). The owner gets "{Name} is in." right away; the snapshot follows a minute later. See `out/journey-compare.md` (`tests/render_journey.py`).
```
Hi {first}!

It's Listing Scout.

{Owner} said you'd stop by.

{Owner} shared the search.

Here's what we're looking for:

{your areas}
{beds}
{price range}
{must-haves}

You get {Owner}'s alerts too.

Quiet days mean nothing fit.

Did this come through okay?
```

**6. Optional preferences for them:**
> "Should {Name} get every alert, or only ones in your target range?"
Set it in their CRITERIA recipient entry: `tiers: [target]`.
Confirm: "Done. {Name} gets {choice}."

## When something goes wrong (calm template)
Say what happened. Say that nothing is wrong on their side. Give one next step.
- **Target not allowed:** "That text didn't go through. Nothing is wrong with your phone. Your line just isn't open yet. Please text anything, like **"hi"**, to the Listing Scout contact, and I'll try again."
- **Sent but not received:** "Photon accepted it, but it hasn't shown up yet. Nothing is wrong on your side. Is Listing Scout saved as a contact? Could you also check the Unknown Senders list in Messages?" If still nothing: "One more check: open debug.photon.codes on your iPhone and tell me the handle it shows."
- **Secret no longer works:** "I lost my connection to Photon. Probably the secret was changed, which is fine. Please paste the current one into the secure box I'm sending."
- **Listing site down:** only mention it if it lasts more than a day: "{Source} is quiet today." / "I'll keep checking it." / "Your other sites are fine."
Never retry a failed send more than once without asking.

## Features to mention ( chat wording, once each)
- At the promise (step 2): "Everything stays on my computer, and logs are deleted after 30 days."
- At going live (step 8): "Later, you can text me changes, like adding a ZIP. I'll read them back first."
- Sleep mode is never pitched in setup. It's offered once by text, the morning after a late alert:
```
That last one came at 2:14 AM.

Overnight finds can wait.

They'd come at 7 AM instead.

Want me to?
```
- Owner removing someone:
```
Take Sarah off the search?
```
- A liked place gone about a day:
```
Heads up on Santa Isabel:

It's no longer listed.

I'll say if it comes back.
```
- Fine-tune read-back:
```
Got it:

Add 78745 to the search.

Want me to make that change?
```
- The finish line (to everyone, after the owner's yes):
```
Congrats on the new place!

The search is wrapped up.

No more listing texts from me.
```
- If a member asks what's kept:
```
Replies stay while we search.

When it ends, I delete them.

Only Photon sees the texts.
```
