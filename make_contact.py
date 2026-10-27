#!/usr/bin/env python3
"""Make a 'Listing Scout' contact card (.vcf) for each recipient's assigned Photon line.
The Photon line number is looked up from the API at run time (it is not a secret).
Personal numbers are never written to the card or to files.
Usage: python3 make_contact.py [NAME ...]   -> out/Listing-Scout-<Name>.vcf
Needs env PHOTON_API_KEY (Project secret); Project ID from CRITERIA.yaml or PHOTON_PROJECT_ID."""
import os, sys, base64, json, urllib.request, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style
HERE = os.path.dirname(os.path.abspath(__file__))
C = yaml.safe_load(open(os.path.join(HERE, "CRITERIA.yaml")))
PID = os.environ.get("PHOTON_PROJECT_ID") or C["photon"]["project_id"]
KEY = os.environ.get("PHOTON_API_KEY") or sys.exit("Missing env PHOTON_API_KEY.")

def users():
    req = urllib.request.Request(f"https://spectrum.photon.codes/projects/{PID}/users/", headers={
        "User-Agent": "listing-scout/1.0",
        "Authorization": "Basic " + base64.b64encode(f"{PID}:{KEY}".encode()).decode()})
    return json.load(urllib.request.urlopen(req, timeout=30))["data"]["users"]

def vcard(line, photo=None):
    v = ["BEGIN:VCARD", "VERSION:3.0", "N:Scout;Listing;;;", "FN:Listing Scout", "ORG:Listing Scout",
         f"TEL;TYPE=CELL,IPHONE:{line}", "NOTE:" + style.VCARD_NOTE]
    if photo:
        b = base64.b64encode(open(photo, "rb").read()).decode()
        v.append("PHOTO;ENCODING=b;TYPE=PNG:" + "\r\n ".join(b[i:i+74] for i in range(0, len(b), 74)))
    v.append("END:VCARD")
    return "\r\n".join(v) + "\r\n"

want = set(a.lower() for a in sys.argv[1:])
U = users(); os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
photo = os.path.join(HERE, "assets", "avatar.png"); photo = photo if os.path.exists(photo) else None
for r in C["recipients"]:
    first = r["name"].replace("'s", "s").replace(" ", "-")
    if want and first.lower() not in want and r["name"].lower() not in want: continue
    u = next((u for u in U if r.get("phone_last4") and (u.get("phoneNumber") or "").endswith(r["phone_last4"])), None)
    if not u or not u.get("assignedPhoneNumber"):
        print(f"skip {r['name']}: not on the Photon Users page yet"); continue
    fn = os.path.join(HERE, "out", f"Listing-Scout-{first}.vcf")
    open(fn, "w").write(vcard(u["assignedPhoneNumber"], photo))
    print(f"{fn}  (line ending {u['assignedPhoneNumber'][-4:]}{', with photo' if photo else ''})")
