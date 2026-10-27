# Listing Scout: privacy

Short version: your search stays on your own bot's computer. There are no hosted pages.

## What's stored

| What | Where | How long |
|---|---|---|
| Your search settings (areas, beds, price, pets…) | `CRITERIA.yaml` (+ backups in `out/` after each change) | Until you delete them |
| Members' names and phone numbers | `CRITERIA.yaml` holds only the last 4 digits; full numbers live in Photon's Users page | Until a person is removed or leaves |
| Replies, likes and passes (words as written) | `out/shortlist.json`, `out/members.json` | While the search runs |
| Listings already seen | `state.json` | While the search runs |
| Message and run logs (phone numbers masked) | `logs/` | 30 days, then deleted automatically |
| Application profile (job, income, past homes and references, move date, occupants, pets, vehicles, emergency contact name) | `~/.config/listing-scout/apply_profile.json`, readable only by the bot (chmod 600), never printed in full or texted | Until you ask to delete it |
| Apply requests and plans (place, status, field names only) | `out/apply_requests.json`, `out/apply_plans/` | While the search runs |
| Feedback ("Make it better") | `out/feedback.jsonl` | Until the owner reviews it |

## Never stored

- Your Social Security number, date of birth, driver's license number and bank numbers. You type them into a use-once private form for each application. The bot fills them in and doesn't keep them.
- Photo ID and pay stub files. You attach them in the Grok Bot app when an application asks.
- Your name, address, phone, email, card and site logins stay in the Grok Bot vault, not in Listing Scout files.

## Where

- Only on the owner's own bot computer. Nothing is published to a website.
- Secrets (like the Photon key) live only in the environment or the vault, never in files.

## What's shared

- **Photon** delivers the texts, so it sees phone numbers and message text. The bot's "what do you keep" reply says so: "Only Photon sees the texts."
- **Feedback** that someone confirms with a clear yes includes only their exact words, the bot version and the kind of last text. No names, numbers or addresses. Email is off unless the owner sets `feedback_email`.
- **Applications** go only to the listing's own apply page, and only after your yes for that place. The bot never emails or calls landlords.
- Nothing else leaves the bot. Listing sites email alerts to the bot's own inbox; the bot doesn't log in as you.

## Deleting

- Anyone: text "leave". Their replies are deleted and they're never texted again. STOP pauses texts instantly.
- Owner: "remove {Name}" removes one person (asks first).
- Owner: "delete everything". The bot asks "Delete all the search data?" and only a word yes ("yes", "do it") deletes replies, the shortlist, queues and logs. STOP flags are kept so an opt-out is still honored.
- At the finish line, the bot offers to clear everything.
- Removing someone from Photon's Users page is a separate step the owner takes in Photon.

## The author's role

- The author (errnsterr) never receives, sees or stores your data. Everything stays on your own bot and the services you connect.
- When you approve an application, what you submit goes to that landlord's or portal's site and is covered by their privacy policy, not this one.
- Photon, Grok Bot and listing sites handle data under their own terms. The author doesn't control them.
