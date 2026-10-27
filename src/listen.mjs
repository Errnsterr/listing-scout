// Listing Scout reply listener (no AI). Keeps one stream open to Photon and hands each inbound
// text to replies.py, which updates the shared shortlist and relays one calm line to the other person.
//   node src/listen.mjs --observe   # connect and log that messages arrive (masked); sends nothing
//   node src/listen.mjs             # live: replies.py may send relay texts (only to people on the recipients list)
// Needs PHOTON_API_KEY (+ project id). Started by ensure_running.sh only when CRITERIA.yaml has replies: on.
import { spawnSync } from "node:child_process";
import { Spectrum } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SRC = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(SRC);
const observe = process.argv.includes("--observe");
let pid = process.env.PHOTON_PROJECT_ID;
if (!pid) { const m = readFileSync(join(ROOT, "CRITERIA.yaml"), "utf8").match(/project_id:\s*"([^"]+)"/); pid = m && m[1]; }
const mask = (s) => String(s ?? "").replace(/\+?\d{7,}/g, (m) => "***" + m.slice(-4));
const app = await Spectrum({ projectId: pid, projectSecret: process.env.PHOTON_API_KEY, providers: [imessage.config()] });
console.log(new Date().toISOString(), "listening", observe ? "(observe only)" : "(live)");
for await (const [space, message] of app.messages) {
  if (message.direction !== "inbound") continue;
  const ctype = message.content?.type || "text";
  const text = ctype === "text" ? message.content.text : "";
  const kind = ctype === "text" ? "text" : (/voice|audio/.test(ctype) ? "voice" : "photo");
  const from = message.sender?.id || "";
  console.log(new Date().toISOString(), "inbound from", mask(from), kind === "text" ? `(${text.length} chars)` : `(${kind})`);
  if (observe || (kind === "text" && !text)) continue;
  const r = spawnSync("python3", [join(SRC, "replies.py"), "--send"], { cwd: ROOT, input: JSON.stringify({ from, text, kind }), encoding: "utf8", timeout: 120000 });
  console.log(mask(r.stdout).trim(), mask(r.stderr).trim());
  if (/^LISTENER_STOP$/m.test(r.stdout || "")) { console.log(new Date().toISOString(), "search wrapped up; listener stopping"); process.exit(0); }   // We found it
  const fw = (r.stdout.match(/^FORWARD_MEDIA (.+)$/m) || [])[1];   // photo/voice: forward the same content, as is (UNVERIFIED live)
  if (fw) for (const phone of JSON.parse(fw)) {
    try { const dm = await imessage(app).space.create(await imessage(app).user(phone)); await dm.send(message.content); }
    catch (e) {
      console.log("media forward failed for", mask(phone), String(e).slice(0, 120));
      spawnSync("python3", [join(SRC, "replies.py"), "--send", "--media-failed", phone], { cwd: ROOT, encoding: "utf8", timeout: 60000 });
    }
  }
}
