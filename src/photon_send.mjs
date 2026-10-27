// Photon (Stable / Spectrum) delivery helper. Credentials from env only:
//   PHOTON_PROJECT_ID, PHOTON_API_KEY (= Project secret from Photon's Configure page)
// Usage:
//   node src/photon_send.mjs check  <+1phone>             # connects + resolves the user; sends NOTHING
//   node src/photon_send.mjs send   <+1phone> <textfile> --send   # sends the file's text as one iMessage DM
//   node src/photon_send.mjs channel <+1phone>            # read-only: iMessage availability (Photon SDK); prints "channel: imessage|sms|rcs|unknown"
//   add  --card <file.vcf>  to send a contact card right after the text (spectrum-ts contact(): vCard as a file attachment)
import { readFileSync } from "node:fs";
import { Spectrum, contact } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";

const [mode, phone, file] = process.argv.slice(2);
const really = process.argv.includes("--send");
const ci = process.argv.indexOf("--card"); const card = ci > 0 ? process.argv[ci + 1] : null;
const need = (n) => { const v = process.env[n]; if (!v) { console.error(`Missing env ${n}`); process.exit(2); } return v; };
if (!["check", "send", "channel"].includes(mode) || !/^\+\d{10,15}$/.test(phone || "")) {
  console.error("usage: node src/photon_send.mjs check|send +15551234567 [textfile] [--send]"); process.exit(2);
}
const mask = (p) => "***" + p.slice(-4);
const app = await Spectrum({
  projectId: need("PHOTON_PROJECT_ID"),
  projectSecret: need("PHOTON_API_KEY"),
  providers: [imessage.config()],
});
const im = imessage(app);
if (mode === "channel") {
  // @photon-ai/advanced-imessage client behind spectrum-ts (not part of spectrum-ts's public API, so every step is guarded).
  // Any failure prints "channel: unknown"; notify.py then assumes iMessage, logs a warning and never blocks sending.
  let out = "unknown", why = "";
  try {
    const rt = app.__internal?.platforms?.get?.("imessage");
    const entries = Array.isArray(rt?.client) ? rt.client : [];
    const c = entries.map((e) => e?.client).find((x) => x?.addresses?.isIMessageAvailable);
    if (!c) why = "SDK address check not reachable";
    else if (await c.addresses.isIMessageAvailable(phone)) out = "imessage";
    else {
      let svcs = [];
      try { svcs = ((await c.addresses.get(phone))?.services || []).map((s) => String(s?.service ?? s).toUpperCase()); } catch {}
      out = svcs.some((s) => s.includes("RCS")) ? "rcs" : "sms";
    }
  } catch (e) { why = String(e?.message || e).split(process.env.PHOTON_API_KEY || "\u0000").join("[secret]").replace(/\+?\d{7,}/g, (m) => "***" + m.slice(-4)).slice(0, 160); }
  console.log(`channel: ${out}`);
  if (why) console.error(`channel check for ${mask(phone)}: ${why}`);
  await app.stop?.(); setTimeout(() => process.exit(0), 500);
} else try {
  const user = await im.user(phone);
  console.log(`resolved user ${mask(phone)}: ok (${user?.id ? "id present" : "no id"})`);
  if (mode === "send") {
    const text = readFileSync(file, "utf8").trim();
    if (!really) { console.log(`[DRY RUN] would send ${text.length} chars${card ? " + card" : ""} to ${mask(phone)}`); }
    else {
      const dm = await im.space.create(user);
      await dm.send(text);
      console.log(`sent to ${mask(phone)} (accepted by Photon; delivery not confirmed)`);
      if (card) {
        await dm.send(contact(readFileSync(card, "utf8")));
        console.log(`card sent to ${mask(phone)} (accepted by Photon; delivery not confirmed)`);
      }
    }
  }
} catch (e) {
  const secret = process.env.PHOTON_API_KEY || "\u0000";
  const clean = (x) => String(x ?? "").split(secret).join("[secret]").replace(/\+?\d{7,}/g, (m) => "***" + m.slice(-4));
  let cur = e, depth = 0;
  while (cur && depth < 5) {
    console.error(`FAILED${depth ? " (cause " + depth + ")" : ""} for ${mask(phone)}: ${clean(cur.name)} code=${clean(cur.code)} ${clean(cur.message)}`);
    if (cur.details) console.error("  details: " + clean(cur.details));
    if (cur.metadata?.toJSON) console.error("  metadata: " + clean(JSON.stringify(cur.metadata.toJSON())));
    if (cur.stack) console.error(clean(cur.stack.split("\n").slice(1, 8).join("\n")));
    cur = cur.cause; depth++;
  }
  process.exitCode = 1;
} finally {
  await app.stop?.(); setTimeout(() => process.exit(process.exitCode || 0), 500);
}
