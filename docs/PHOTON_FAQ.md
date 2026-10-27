# Listing Scout: Photon FAQ (texting)

For you: short answers. **For the bot:** how to spot the situation, what to check, and what to say.

Setup order: 1 reflect · 2 promise · 3 Photon + secret · 4 add people · 5 save contact · 6 first text · 7 sample alert · 8 go live (welcome = test, then snapshot). Exact wording is in `docs/SETUP.md`. For errors: say what happened, that nothing is wrong on their side, and the one next step.

Answers marked (confirmed) were checked on Photon's site, in its docs, or in our own test on 2026-10-26. Anything marked Unverified has not been checked yet.

---

## Pre-flight checklist (the bot runs this before any send)

1. `PHOTON_API_KEY` is set (the Project secret). Never print it.
2. The Project ID is set (`photon.project_id` in CRITERIA.yaml, or `PHOTON_PROJECT_ID`).
3. `python3 src/notify.py check` passes. This sends nothing. It should show the project name, the plan, and "reachable" for each person.
4. Every recipient in CRITERIA.yaml (`phone_last4`) is on the Photon Users list.
5. Each recipient saved the Listing Scout contact and texted it anything, like **"hi"** (setup steps 5 and 6).
6. The person approved this kind of message (the welcome/test, or a sample alert). The quiet first run happens once, as part of the install.
7. Alerts aren't paused (CRITERIA.yaml `paused: true` means skip).
8. Bundling is on: no more than one text per hour, with extras grouped into one text.
9. Run the send command with `--send`. Read the result. Never retry more than once without asking.

---

### What is Photon? What does it cost?

Photon is the service that sends our alerts as iMessages from a real phone number. (confirmed)

- Plans, prices and how many people each allows change over time. Check photon.codes/pricing before you pick.

**For the bot:** check the plan with `src/notify.py check`, which shows the plan. Never quote prices or limits; link photon.codes/pricing.

### How do I sign up?

Go to app.photon.codes and choose **Continue with Google**. (confirmed)

Unverified: whether a brand-new account is asked for a phone number or ID.

**For the bot:** if the user gets stuck at a verification step, ask what the screen says. Don't guess at requirements.

### Where is the Project secret? Is there an API key?

- In your project, open **Configure** and click **Reveal** next to **Project secret**. (confirmed)
- There are no separate API keys. The Project ID plus the Project secret are the login. (confirmed)
- Paste the secret **only into the bot's secure box**, never in chat.
- If you **rotate** (regenerate) the secret, the bot stops sending until you give it the new one. Photon's docs confirm the secret can be rotated. (confirmed)

### For the bot

- **Spot it:** API calls return 401/403 errors, or the SDK reports an authentication failure that isn't "Target not allowed".
- **Do:** send a secure secret request, then save the value as env var `PHOTON_API_KEY`.
- **Never:** echo the secret, log it, or write it to a file.

### Is the Project ID private?

No. It's safe to share, and it's stored in CRITERIA.yaml. (confirmed)

### How do I add people?

- Open the **Users** page and add each person's mobile number (iPhone or Android). Your plan sets how many (photon.codes/pricing).
- Each person gets a **Photon number**, the number their texts will come from. It's shown on the Users page. Next: save it as a contact (step 5) and send the first text (step 6).

### For the bot

- **Spot it:** `src/notify.py` prints "skip NAME: not a Photon project user yet".
- **For the bot:** add people with the secure form (number into `NEW_USER_PHONE`) and `src/notify.py add_user "NAME" --confirm`, never by asking for digits in chat.
- **Then:** update `phone_last4` in CRITERIA.yaml.

### Why does each person have to text their Photon number once?

On Free and Pro, Photon only lets the shared number text people who are registered on the project. In our test, it also needed one text from the person. (confirmed) **Confirmed fix:** sends failed with "Target not allowed for this project" until the person texted the line once.

After that, the test went through.

### For the bot

- **Spot it:** the error text contains "Target not allowed for this project". `src/notify.py` prints a hint.
- **Tell the user:** "That text didn't go through. Nothing is wrong with your phone. Your line just isn't open yet. Please text anything, like **"hi"**, to the Listing Scout contact (number ending XXXX), and I'll try again."
- **Still failing after that?** See "Nothing arrived" below for the handle check.

### Why save it as a contact?

So alerts arrive from **Listing Scout**, a name you know, instead of a strange number. iPhone can move messages from unknown senders into a separate list you might not check. Saving the contact also makes it easy to send your first text. Unverified: We haven't tested whether saving the contact alone changes filtering, but it's Apple's normal behavior for known contacts.

Photon's own guidance also recommends sharing a contact card early.

### For the bot

- Run `python3 src/make_contact.py {Name}`. It looks up their Photon number live and writes `out/Listing-Scout-{Name}.vcf`. It adds a photo if `src/assets/avatar.png` exists.

  Personal numbers are never written to the card.

- Send them the card. Ask them to tap it and choose **Create New Contact**.
- If alerts land in Unknown Senders, ask whether the contact is saved.

### What should my first text say?

Anything works, like **"hi"**. Send it from the Listing Scout contact. This opens your line, and the bot can't text you until it's sent.

(confirmed) (a first text is required, confirmed 2026-10-26)

### For the bot

- Ask for this before any text (step 6). The welcome/test comes in step 8.
- If a send fails with "Target not allowed", the first text hasn't arrived yet. Use the calm wording above.
- Any text works; suggest "hi" to keep it simple.

### I used Photon before. Do I still need to do that?

Yes. **Photon assigns each person their own line** in this project, so a number from another project doesn't count. (confirmed)

**For the bot:** always give the number ending from this project's Users list (`line_last4` in `src/notify.py` output).

### Can we get alerts in one group chat?

Not on Free or Pro. Each person gets their own one-on-one thread with the same alert. Group chats need Business.

(confirmed)

**For the bot:** if asked, explain this and offer separate threads. Don't upgrade the plan without approval, because it costs money.

### How does the test work?

The welcome text is the test. It ends with "Did this come through okay?" You reply OK. (confirmed) (tested 2026-10-26)

**For the bot:** only send it after the person approves it. "Sent" means Photon accepted it, not that it arrived, so wait for their OK.

### The bot says "sent" but nothing arrived

Check, in order:

1. iMessage is on: Settings, then Apps, then Messages.
2. The **Unknown Senders** or filtered messages list in Messages.
3. Your iMessage may be using a different handle, like an email. Open **debug.photon.codes** on your iPhone; it tells you the exact handle. Add that handle on the Users page.

   (confirmed) (Photon's troubleshooting docs)

**For the bot:** ask these one at a time. Don't resend more than once without the user's OK.

### Can it send regular texts (SMS/RCS), and does it work for Android?

(confirmed) **Tested once.** Each person's line is checked automatically before sending (iMessage vs SMS/RCS) and remembered. Non-iMessage lines get the plain-text path: no emoji, no contact card, Android forwarding steps. If the check can't tell, it falls back to iMessage.

A live test with iMessage off on an iPhone arrived as RCS. US SMS-only carriers may still need 10DLC registration.

**For the bot:** nothing to set by hand; `channel:` in CRITERIA is only an override.

### What happens with tapbacks?

A tapback ("Liked …", "Loved …") is never relayed as if someone typed it. It goes to the others as a short note, like "Sarah loved Maple St"

### How do I change who gets alerts?

- **Add someone:** say "add my partner". The bot sends a secure form, confirms, adds them, and texts you their invite to forward. They text their line once.
- **Remove someone:** delete them on the Users page, or ask the bot to remove them from the list.

**For the bot:** edit `recipients` in CRITERIA.yaml. Removing someone from the Photon Users page is the user's decision; don't do it on your own.

### How do I add my partner or someone else in my home?

Say "add my partner" (or wife, roommate…). The bot sends a secure form for their name and number. You confirm, and the bot adds them on Photon.

They get their own assigned Listing Scout line and their own thread. The bot texts you a plain invite to forward to them. They tap the number in it and text anything, like "hi".

The bot then sends them a welcome text with the contact card. (confirmed) for the steps that match yours. Unverified: Adding a person through the API (`add_user`) hasn't been run yet.

### For the bot

- Collect the number only through the secure form, into env `NEW_USER_PHONE`.
- Run `src/notify.py add_user "Name" --confirm` only after the owner says yes.
- Never text them before they text the line. Photon rejects it anyway ("Target not allowed").
- Ask the owner before sending the welcome text.
- Check the total fits your plan (photon.codes/pricing). Set `photon.user_limit` to have the bot check it.
- Templates are in `docs/SETUP.md`, including the setup conversation script.

### Can they get fewer texts than me?

Yes. Their CRITERIA entry can say `tiers: [target]` (only places in your target range).

**For the bot:** ask the owner which one they prefer. Confirm the choice back in plain words.

### What does this cost me?

For Photon costs, see photon.codes/pricing. Listing checks use no AI. AI is used only for conversations, reading alert emails, and the extras you choose.

See `docs/COSTS.md`, and check Grok Bot Settings → Usage for your actual spend.

**For the bot:** never quote token or dollar figures for AI. Point to Usage settings.

### How do I pause alerts?

Tell the bot "pause alerts", and "resume" when ready. While paused, listings are still tracked, and nothing is texted.

**For the bot:** set `paused: true` in CRITERIA.yaml, or pause the routine. When resuming, ask whether they want a catch-up summary or only new listings from now on.

### What about privacy?

- Phone numbers are **not stored** in our files, only the last 4 digits. The full number is looked up from Photon at send time.
- The Project secret lives only in a protected setting (an environment variable), never in files or chat.
- Photon sees the messages it delivers. That's how texting services work.
- Replies are kept only while the search runs, logs for 30 days, and nothing is deleted without the owner's yes. Full details: "What I keep" in SETUP.md.

**For the bot:** mask numbers in every output: show only the last 4 digits. Never print the secret.

### Can the bot text me the contact card?

Yes, once your line is open. (confirmed) Photon's `spectrum-ts` can send a contact card as an attachment (tested 2026-10-26). Before your first text, the bot can't text you at all, so the first card comes here in chat.

**For the bot:** card sends are attached to the welcome, for the owner and for household members.

A member's invite is a plain text with no links. The bot texts the owner a short intro, then the invite itself, ending in the Listing Scout line number:

- "Here's {Name}'s invite."
- "Forward the next text to {Name}."
- "Press and hold it."
- "Tap More, then the arrow."
- "Pick {Name} and press Send."

The name is dropped from any line it would push past 30 characters. The owner forwards it, and the new person taps the number and texts anything, like "hi".

Never text them first.

### Can someone stop the texts?

Yes. Texting STOP stops them at once, with no reply from the bot. "START" turns them back on.

The owner can also ask the bot to remove someone; it asks first.

**For the bot:** Unverified: Carrier rules for STOP and confirmation texts (CTIA, TCPA) depend on Photon's sender type. They're unverified. Don't state them as facts.

### Can alerts wait until morning?

Yes, with Sleep mode. It's off by default, so alerts stay fast. Each person can turn it on for themselves.

Overnight finds then arrive as one text at 7 AM.

### How do we report a bug or suggest a feature?

Just text it, like "bug, the link didn't open" or "idea: a map view". The bot asks "Send it to the Scout team?" and sends only on a clear yes: your exact words, the bot version, and what kind of text you last got. Nothing is fixed or queued automatically; the owner reviews every item first.

### Can I text my SSN, ID or pay stubs to apply?

No. Never text them. Texts go through Photon, and Photon sees what it delivers. For **Apply for me**, your bot asks for your SSN and date of birth in a use-once private form in the Grok Bot app, and you attach ID or pay stubs there too.

(confirmed)

**For the bot:** if someone texts an SSN-shaped number or a document, don't repeat it, don't save it, and ask them to use the Grok Bot app instead. Unverified: Whether Photon forwards photos reliably is unverified; `src/replies.py --media-failed` already covers the case where it can't.
