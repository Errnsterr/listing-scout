#!/usr/bin/env python3
"""Make it better: review what people sent. GATE: nothing is ever auto-queued or built.
  python3 src/review_feedback.py                 # list items still pending_review
  python3 src/review_feedback.py --all           # list everything
  python3 src/review_feedback.py --approve ID    # only after the owner explicitly says yes; marks it approved (builds nothing)
  python3 src/review_feedback.py --decline ID
  python3 src/review_feedback.py --fixed ID      # after an approved fix ships; prints the draft 'You asked, it's fixed' text
The draft is never sent from here. Send it by hand, to the person who asked, only with the owner's okay."""
import os, sys, json, time
_SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(_SRC) if os.path.basename(_SRC) == "src" else _SRC
sys.path.insert(0, _SRC)
import features, style

def save(items):
    with open(features.FEEDBACK, "w") as f:
        for i in items: f.write(json.dumps(i) + "\n")

def draft_fixed(item):
    """Draft only. Refuses unless the item was approved and marked fixed."""
    if item.get("status") != "fixed": raise ValueError("not approved and fixed yet")
    return style.feedback_fixed(item["words"])

def main(a=sys.argv[1:]):
    items = features.feedback_items()
    if not a or a == ["--all"]:
        show = items if a else [i for i in items if i.get("status") == "pending_review"]
        if not show: print("Nothing pending review." if not a else "No feedback yet."); return
        for i in show: print(f"{i['id']}  [{i['status']}]  v{i['version']}  after: {i['last_text']}\n    \"{i['words']}\"")
        return
    op, iid = a[0], (a[1] if len(a) > 1 else "")
    it = next((i for i in items if i["id"] == iid), None)
    if not it: sys.exit(f"no item {iid}")
    need = {"--approve": "pending_review", "--decline": "pending_review", "--fixed": "approved"}.get(op) or sys.exit(__doc__)
    if it["status"] != need: sys.exit(f"{iid} is {it['status']}; {op} needs {need}")
    it["status"] = {"--approve": "approved", "--decline": "declined", "--fixed": "fixed"}[op]; it[it["status"] + "_ts"] = time.strftime("%F %T %Z")
    save(items); print(f"{iid} -> {it['status']}")
    if op == "--fixed": print("DRAFT (not sent; send by hand with the owner's okay):\n" + draft_fixed(it))

if __name__ == "__main__": main()
