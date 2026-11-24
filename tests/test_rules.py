#!/usr/bin/env python3
"""The rules, each with a case that passes and a case that is stopped. Tests, not scores.

    python3 tests/test_rules.py
"""
import copy
import datetime as dt
import json
import pathlib
import re
import sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import baseline  # noqa: E402
import followup_core as core  # noqa: E402
import views  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def recs(name):
    return json.loads((ROOT / "sample" / name).read_text())["shoppers"]


SCORED, PRACTICE = recs("shoppers.json"), recs("practice.json")
ALL = SCORED + PRACTICE


def utc(y, mo, d, h, mi, zone):
    return dt.datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(zone)).astimezone(dt.timezone.utc)


# ------------------------------------------------------------------ time
check("9:00 am local is inside the hours", core.allowed_at(utc(2026, 11, 24, 9, 0, "America/Chicago"), ["America/Chicago"]))
check("7:59 pm local is inside the hours", core.allowed_at(utc(2026, 11, 24, 19, 59, "America/Chicago"), ["America/Chicago"]))
check("8:00 pm local is outside the hours", not core.allowed_at(utc(2026, 11, 24, 20, 0, "America/Chicago"), ["America/Chicago"]))
check("8:59 am local is outside the hours", not core.allowed_at(utc(2026, 11, 24, 8, 59, "America/Chicago"), ["America/Chicago"]))
check("Sunday is not a sending day", not core.allowed_at(utc(2026, 11, 29, 11, 0, "America/Chicago"), ["America/Chicago"]))
check("Thanksgiving is not a sending day", not core.allowed_at(utc(2026, 11, 26, 11, 0, "America/Chicago"), ["America/Chicago"]))
s = core.next_slot(utc(2026, 11, 25, 19, 50, "America/Chicago"), ["America/Chicago"])
check("a slot asked for on Wednesday evening skips Thanksgiving to Friday 9:00 am", s.astimezone(ZoneInfo("America/Chicago")).strftime("%a %H:%M") == "Fri 09:00", str(s))
s = core.next_slot(utc(2026, 11, 28, 19, 50, "America/Chicago"), ["America/Chicago"])
check("a slot asked for on Saturday evening skips Sunday to Monday 9:00 am", s.astimezone(ZoneInfo("America/Chicago")).strftime("%a %H:%M") == "Mon 09:00", str(s))
s = core.next_slot(utc(2026, 11, 24, 8, 0, "America/Los_Angeles"), ["America/Los_Angeles", "America/New_York"])
check("two time zones: the slot fits both (9:00 am Pacific, not 6:00 am)", s.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%H:%M") == "09:00", str(s))
s = core.next_slot(utc(2026, 11, 24, 17, 30, "America/New_York"), ["America/New_York", "America/Los_Angeles"])
check("two time zones: at 5:30 pm Eastern a Pacific number is still allowed", s is not None and s.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M") == "17:30", str(s))
r = copy.deepcopy(next(x for x in SCORED if x["stop"] == "saved_car" and x.get("tz") == "America/Chicago" and x["channels"]["text"]))
r["area_code"] = "212"
check("a phone area code in another zone adds that zone", core.zones_of(r) == ["America/Chicago", "America/New_York"], str(core.zones_of(r)))

# ------------------------------------------------------------------ contact rules
base = copy.deepcopy(next(x for x in SCORED if x["stop"] == "saved_car" and not x.get("message") and x["channels"]["email"] and x["channels"]["text"]
                          and not x["channels"]["text_opted_out"] and not x["channels"]["email_unsubscribed"] and x.get("state") != "CA"
                          and not x.get("last_message_from_us")))
check("a plain quiet shopper may be contacted", core.contact_rule(base, "quiet") is None, core.contact_rule(base, "quiet"))
r = copy.deepcopy(base); r["channels"]["text_opted_out"] = True
check("an opt-out on text stops email too", core.contact_rule(r, "quiet") == "opted_out")
r = copy.deepcopy(base); r["channels"]["email_unsubscribed"] = True
check("an email unsubscribe stops texts too", core.contact_rule(r, "quiet") == "opted_out")
r = copy.deepcopy(base); r["do_not_contact"] = True
check("a do-not-contact flag stops everything", core.contact_rule(r, "quiet") == "do_not_contact")
r = copy.deepcopy(base); r["last_message_from_us"] = "2026-11-19T11:00:00-06:00"
check("messaged 4 days ago: no nudge", core.contact_rule(r, "quiet") == "messaged_recently")
r = copy.deepcopy(base); r["last_message_from_us"] = "2026-11-13T11:00:00-06:00"
check("messaged 10 days ago: a nudge is allowed", core.contact_rule(r, "quiet") is None)
r = copy.deepcopy(base); r["channels"]["email"] = False
check("no email: a saved-car nudge falls back to text", core.pick_channel(r, "quiet") == "text")
r = copy.deepcopy(base); r["channels"]["text"] = False
check("no text consent: never a text", core.pick_channel(r, "quiet") == "email")
pq = copy.deepcopy(next(x for x in ALL if x["stop"] == "prequalified"))
pq["channels"].update(email=False, text=True)
check("pre-qualified with no email: no channel (never a text)", core.pick_channel(pq, "quiet") is None)

# ------------------------------------------------------------------ what the writer sees
leak = []
for rec in ALL:
    for kind in ("waiting", "quiet"):
        if kind == "waiting" and not rec.get("message"):
            continue
        v = views.build(rec, kind, core.WORDING)
        text = "\n".join(views.writer_lines(v, "text")).lower()
        ws = set(core.words_of(text))
        for bad in [rec["first_name"].lower(), "his", "her", "he", "she", "him"]:
            if bad in ws:
                leak.append(f"{rec['id']}: {bad}")
        if "$" in text:
            leak.append(f"{rec['id']}: $")
        for k in ("price", "price_lowered", "payment_estimate", "amount"):
            for blob in (rec.get("car") or {}, rec.get("prequal") or {}, rec.get("offer") or {}):
                val = blob.get(k)
                if isinstance(val, (int, float)) and val and f"{val:,}" in text:
                    leak.append(f"{rec['id']}: {k}")
check("no name, pronoun or money field ever reaches the writer", not leak, str(leak[:5]))
check("no record holds age, sex or a similar field", not [r["id"] for r in ALL if any(k in r for k in ("age", "sex", "gender", "race", "religion", "marital"))])
check("no sample file names the company this was made for",
      not any("carvana" in f.read_text().lower() for f in [*(ROOT / "sample").glob("*.json"), *(ROOT / "cases").glob("*.json")]))

# ------------------------------------------------------------------ checks on a draft
rec = next(x for x in SCORED if x["stop"] == "saved_car" and (x.get("car") or {}).get("features") and not x["car"].get("sold_at"))
v = views.build(rec, "quiet", core.WORDING)
good = baseline.draft_for(v)
check("a plain draft passes every code check", core.code_checks(good, v, rec) == [], str(core.code_checks(good, v, rec)))
for bad, what in (("{first_name}, it is $500 less now. You can take another look at your car whenever you're ready.", "money"),
                  ("{first_name}, the car you saved is still listed. Take another look today.", "pressure"),
                  ("{first_name}, the car you saved is still listed. We'll call you tomorrow.", "promise"),
                  ("{first_name}, the car you saved is still listed and has a warranty. You can take another look at your car whenever you're ready.", "not in the record"),
                  ("{first_name}, the car you saved is still listed with 3 keys. You can take another look at your car whenever you're ready.", "a number not in the record"),
                  ("{first_name}, the car you saved is ready for you to take another look.", "not in the record"),
                  ("{first_name}, the car you saved is still listed. You can take another look. It is lovely.", "shape"),
                  ("{first_name}, you stopped at the saved car. You can take another look at your car whenever you're ready.", "system words"),
                  ("{first_name}, the Ferrari you saved is still listed. You can take another look at your car whenever you're ready.", "a name not in the record")):
    names = [f for f, _ in core.code_checks(bad, v, rec)]
    check(f"a draft with {what} is held", what in names, str(names))

import jev_check  # noqa: E402
th = {"asks_to_stop_max": 0.2, "instructs_writer_max": 0.5, "complaint_max": 0.5, "about_money_max": 0.2}
check("the strongest reading sets the reason: a money ask that sounds a little like orders is a money question",
      jev_check.reasons_from({"asks_to_stop": [0.01, 0.01], "instructs_writer": [0.55, 0.6], "complaint": [0.07, 0.07], "about_money": [0.94, 0.95]}, th).get("reason") == "money")
check("a request to stop comes before any other reading",
      jev_check.reasons_from({"asks_to_stop": [0.9, 0.9], "instructs_writer": [0.73, 0.73], "complaint": [0.75, 0.75], "about_money": [0.02, 0.02]}, th).get("asks_to_stop") is True)
check("a reading under its limit sets no reason",
      "reason" not in jev_check.reasons_from({"asks_to_stop": [0.01, 0.01], "instructs_writer": [0.31, 0.31], "complaint": [0.32, 0.32], "about_money": [0.03, 0.03]}, th))
sell = next(x for x in ALL if x["stop"] == "sell_offer" and x.get("offer") and not x["offer"].get("ended"))
sv = views.build(sell, "quiet", core.WORDING)
check("a tie in code's word match is no find, not the first line listed", core.code_answer_line(sv, "what do i need when i come sell my car") is None,
      str(core.code_answer_line(sv, "what do i need when i come sell my car")))
check("'now' meaning 'currently' is not pressure", "pressure" not in [f for f, _ in core.code_checks("{first_name}, three new SUVs now match your search.", v, rec)])
check("'act now' is pressure", "pressure" in [f for f, _ in core.code_checks("{first_name}, the car you saved is still for sale, act now.", v, rec)])
check("an email subject names the topic, not 'your question'", views.subject_for(rec, "quiet", core.WORDING, v).startswith("The "), views.subject_for(rec, "quiet", core.WORDING, v))

check("'Can I stop by Saturday?' is not a request to stop", not core.found("Can I stop by Saturday to see it in person?", core.PATTERNS["message_stop"]))
check("'STOP' on its own is a request to stop", bool(core.found("STOP", core.PATTERNS["message_stop"])))
check("'please stop texting me' is a request to stop", bool(core.found("please stop texting me", core.PATTERNS["message_stop"])))
check("'Has the 60k mile service been done?' is not a money question", not core.found("Has the 60k mile service been done?", core.PATTERNS["message_money"]))
check("'can you do 21k?' is a money question", bool(core.found("can you do 21k?", core.PATTERNS["message_money"])))
check("'Is the Carfax report clean?' is not a complaint", not core.found("Is the Carfax report clean on this one?", core.PATTERNS["message_complaint"]))
unk = dict(rec, area_code="999", channels=dict(rec.get("channels", {}), text=True))
check("a phone area code the table doesn't know means no time zone, so no time is picked", core.zones_of(unk) == [])

class OneRead:
    """A stand-in second check that answers yes from LISTED FEATURES, whatever the question."""
    name = "stand-in"
    def __init__(self): self.drafted = False
    def router(self, rec, view): return {"answered": True, "answer_line": "LISTED FEATURES"}
    def draft(self, rec, view): self.drafted = True; return "{first_name}, yes, it has that."
    def check(self, rec, view, draft): return {}
fq = next(x for x in SCORED if x["stop"] == "saved_car" and x.get("message") and (x.get("car") or {}).get("features") and not x["car"].get("sold_at") and x.get("state") != "CA")
fq = dict(fq, message=dict(fq["message"], text="Does it have a heated steering wheel?"))
one = OneRead()
_, res = core.decide([fq], one)
check("a question about a feature the listing doesn't name is never answered", res and res[0]["outcome"] != "ready" and not one.drafted, str(res and res[0].get("reason")))

hv = {"lines": [("LISTED FEATURES", "Heated front seats; Power moonroof")]}
check("'heated rear seats' doesn't match a listing of heated front seats", core.feature_asked(hv, "Does it have heated rear seats?") is None)
check("'are the front seats cooled or just heated?' doesn't match a listing of heated front seats", core.feature_asked(hv, "Are the front seats cooled or just heated?") is None)
check("'does it have heated front seats?' matches heated front seats", (core.feature_asked(hv, "Does it have heated front seats?") or (None,))[0] == "Heated front seats")
check("'does the moonroof open?' matches a listed power moonroof", (core.feature_asked(hv, "Does the moonroof open?") or (None,))[0] == "Power moonroof")

ok_start = "{first_name}, the car you saved is still listed. Once you're set, take another look."
check("a sentence's first word is never read as a name", "a name not in the record" not in [f for f, _ in core.code_checks(ok_start, v, rec)])

# ------------------------------------------------------------------ nothing sends
code = {p.name: p.read_text() for p in ROOT.glob("*.py")}
hosts = {n: sorted(set(re.findall(r"https?://([A-Za-z0-9.:-]+)", t))) for n, t in code.items()}
hosts = {n: h for n, h in hosts.items() if h}
check("the only addresses any code calls are the local model and the second check",
      hosts == {"write.py": ["127.0.0.1:11434"], "jev_check.py": ["api.typesafe.ai"]}, str(hosts))
check("no code can send email or texts", not any(w in t for t in code.values() for w in ("smtplib", "twilio", "sendgrid", "mailgun", "send_message(")))
check("the deciding code never opens the answer key", not any(w in code[f] for f in ("followup_core.py", "views.py", "write.py", "jev_check.py", "baseline.py")
                                                              for w in ("cases/", '"cases"', "'cases'")))

# ------------------------------------------------------------------ words the tool shows
pub = core.PATTERNS["draft_pressure"]
shown = list(core.WORDING["reasons"].values()) + list(core.WORDING["next_step"].values()) + list(core.WORDING["email_subject"].values())
check("no reason, step or subject uses a pressure word", not [t for t in shown if core.found(t, pub)], str([t for t in shown if core.found(t, pub)]))

print(f"\n{'all passed' if not FAILS else str(len(FAILS)) + ' failed'}")
sys.exit(1 if FAILS else 0)
