"""Left Off: the deciding code.

For each shopper the queue picks, in this order (the first step that stops a shopper decides):
  1. the queue (queries/stalled.sql): a waiting message (unanswered, last 24 hours) or a quiet stall (3 to 30 days)
  2. contact rules (rules.json, in order)
  3. channel and time
  4. a waiting message is read before any draft: code word lists, then the second check's saved answers
  5. the facts the writer may see (views.py)
  6. the draft (saved; written by the local model in write.py)
  7. checks on the draft: code, then the second check's saved answers
  8. the lines each channel needs
Outcome: ready (for a person to approve and send), person (with a reason and a reply-by time) or do_not_contact.

Nothing here sends anything, and nothing here makes a network call. The second check's answers and the drafts are
read from saved files, so the whole month can be decided again with no key and no model.
"""
import datetime as dt
import json
import pathlib
import re
import sqlite3
from zoneinfo import ZoneInfo

import views

HERE = pathlib.Path(__file__).resolve().parent
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load_json(name):
    return json.loads((HERE / name).read_text())


RULES = load_json("rules.json")
PATTERNS = load_json("patterns.json")
WORDING = load_json("wording.json")


# ------------------------------------------------------------------ words

def words_of(text):
    return re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", (text or "").lower().replace("’", "'"))


def found(text, spec, allowed=()):
    """The words, phrases and symbols of one list that appear in the text, whole words only."""
    low = (text or "").lower().replace("’", "'")
    ws = set(words_of(low))
    hits = [w for w in spec.get("words", []) if w in ws and w not in allowed]
    for p in spec.get("phrases", []):
        if re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", low):
            hits.append(p)
    hits += [s for s in spec.get("symbols", []) if s in low]
    if spec.get("whole_message") and re.sub(r"[^a-z ]", "", low).strip() in spec["whole_message"]:
        hits.append(low.strip())
    if spec.get("number_with_k") and re.search(r"\b\d+\s?k\b(?!\s*-?\s*mile)", low):
        hits.append("a number with k")
    return hits


def money_kind(text):
    low = words_of(text)
    if any(w in low for w in ("approve", "approved", "approval", "preapproved", "pre-approved", "qualify")):
        return "approval"
    if any(w in low for w in ("rate", "rates", "apr", "interest")):
        return "rate"
    if any(w in low for w in ("payment", "payments", "monthly", "down")):
        return "payment"
    return "money"


# ------------------------------------------------------------------ time

def run_clock():
    return dt.datetime.fromisoformat(RULES["run_clock"])


def parse_time(s):
    t = dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def zones_of(rec):
    """The time zones a message must fit: the address's, and the phone area code's when it differs."""
    zones = []
    if rec.get("tz"):
        zones.append(rec["tz"])
    code = str(rec.get("area_code") or "")
    area = RULES["timezone_by_area_code"].get(code)
    if code and not area and rec.get("channels", {}).get("text"):
        return []  # a phone area code the table doesn't know: its time zone is unknown, so no time is safe to pick
    if area and area not in zones and rec.get("channels", {}).get("text"):
        zones.append(area)
    return zones


def allowed_at(t_utc, zones):
    h = RULES["sending_hours"]
    start = dt.time.fromisoformat(h["start"])
    end = dt.time.fromisoformat(h["end_before"])
    for z in zones:
        loc = t_utc.astimezone(ZoneInfo(z))
        if DAYS[loc.weekday()] not in h["days"] or loc.date().isoformat() in h["holidays"]:
            return False
        if not (start <= loc.time() < end):
            return False
    return True


def next_slot(after_utc, zones, not_before_local=None):
    """The first quarter-hour at or after `after_utc` that every zone allows (and, for a nudge, not before 10:00
    local on the next sending day)."""
    step = RULES["sending_hours"]["slot_minutes"]
    t = after_utc.replace(second=0, microsecond=0)
    t += dt.timedelta(minutes=(-t.minute) % step)
    for _ in range(14 * 24 * 60 // step):
        if allowed_at(t, zones) and (not_before_local is None or t >= not_before_local):
            return t
        t += dt.timedelta(minutes=step)
    return None


def nudge_slot(zones):
    """10:00 local on the next sending day after the run, in the first zone, fitting every zone."""
    clock = run_clock()
    z0 = ZoneInfo(zones[0])
    day = clock.astimezone(z0).date()
    h = RULES["sending_hours"]
    for _ in range(14):
        day += dt.timedelta(days=1)
        if DAYS[day.weekday()] in h["days"] and day.isoformat() not in h["holidays"]:
            ten = dt.datetime.combine(day, dt.time.fromisoformat(h["nudge_time"]), tzinfo=z0)
            return next_slot(ten.astimezone(dt.timezone.utc), zones, not_before_local=ten.astimezone(dt.timezone.utc))
    return None


def show_time(t_utc, zone):
    loc = t_utc.astimezone(ZoneInfo(zone))
    hour = loc.strftime("%I:%M %p").lstrip("0").lower().replace(" am", " am").replace(" pm", " pm")
    name = {"America/New_York": "Eastern", "America/Chicago": "Central", "America/Denver": "Mountain", "America/Phoenix": "Arizona",
            "America/Los_Angeles": "Pacific"}.get(zone, zone)
    return f"{DAYS[loc.weekday()]}, {loc.strftime('%b')} {loc.day}, {hour} {name}"


# ------------------------------------------------------------------ the queue

def queue(records):
    """Runs queries/stalled.sql over the records and returns {id: 'waiting' | 'quiet'}."""
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE shoppers (id TEXT PRIMARY KEY, stop TEXT, last_activity_at TEXT, message_at TEXT,
                   message_answered INTEGER, finished TEXT)""")
    for r in records:
        m = r.get("message") or {}
        con.execute("INSERT INTO shoppers VALUES (?,?,?,?,?,?)",
                    (r["id"], r["stop"], parse_time(r["last_activity_at"]).astimezone(dt.timezone.utc).isoformat(),
                     parse_time(m["at"]).astimezone(dt.timezone.utc).isoformat() if m.get("at") else None,
                     1 if m.get("answered") else 0, r.get("finished")))
    q = RULES["queue"]
    clock = run_clock().astimezone(dt.timezone.utc)
    params = {"since": (clock - dt.timedelta(hours=q["waiting_message_hours"])).isoformat(),
              "quiet_from": (clock - dt.timedelta(days=q["quiet_days_max"])).isoformat(),
              "quiet_to": (clock - dt.timedelta(days=q["quiet_days_min"])).isoformat()}
    sql = (HERE / "queries" / "stalled.sql").read_text()
    stops = ",".join(f"'{s}'" for s in q["stops"])
    rows = con.execute(sql.replace(":stops", stops), params).fetchall()
    return {rid: kind for rid, kind in rows}


# ------------------------------------------------------------------ contact rules and channel

def channels(rec):
    c = rec.get("channels", {})
    out = []
    if c.get("email") and not c.get("email_bounced") and not c.get("email_unsubscribed"):
        out.append("email")
    if c.get("text") and not c.get("text_opted_out"):
        out.append("text")
    return out


def contact_rule(rec, kind):
    """The first contact rule that stops this shopper, or None."""
    c = rec.get("channels", {})
    msg = (rec.get("message") or {}).get("text", "")
    for rule in RULES["contact_rules_in_order"]:
        if rule == "asked_to_stop" and kind == "waiting" and found(msg, PATTERNS["message_stop"]):
            return rule
        if rule == "opted_out" and (c.get("text_opted_out") or c.get("email_unsubscribed")):
            return rule
        if rule == "do_not_contact" and rec.get("do_not_contact"):
            return rule
        if rule == "talking_with_care" and rec.get("talking_with_care"):
            return rule
        if rule == "messaged_recently" and kind == "quiet" and rec.get("last_message_from_us"):
            days = (run_clock() - parse_time(rec["last_message_from_us"])).total_seconds() / 86400
            if days < RULES["messaged_recently_days"]:
                return rule
        if rule == "no_channel" and not channels(rec):
            return rule
    return None


def pick_channel(rec, kind):
    have = channels(rec)
    if rec["stop"] in RULES["channel"]["email_only_stops"]:
        return "email" if "email" in have else None
    if kind == "waiting":
        came = (rec.get("message") or {}).get("channel")
        return came if came in have else None
    want = RULES["channel"]["nudge_default"][rec["stop"]]
    if want in have:
        return want
    return next((c for c in have if c != want), None)


# ------------------------------------------------------------------ the answer line, by code

LINE_WORDS = {
    "STATUS": {"available", "still", "sold", "listed", "gone", "there"},
    "OFFER ENDS": {"long", "good", "until", "expire", "expires", "valid", "last", "ends", "end", "still", "deadline", "when", "run", "out", "date"},
    "STEPS LEFT": {"else", "need", "left", "finish", "next", "steps", "step", "missing", "remaining"},
    "BRING": {"bring", "need", "keys", "key", "title", "documents", "papers", "paperwork", "license"},
    "SEATS": {"seat", "seats", "seating", "passengers", "people", "row"},
    "NEW MATCHES": {"new", "matches", "match", "ones", "more", "any"},
}
DESCRIBES = {"CAR", "YOUR CAR", "OFFER", "SEARCH"}  # these lines say what the thing is; they never answer a question
STOP = set("a an the is it its this that does do did i my me you your can could would will of on in for to and or with any have has there what how".split())


def norm(words):
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words}


QUALIFIERS = {"front", "rear", "third", "second", "heated", "cooled", "ventilated", "wireless", "power", "panoramic", "manual", "automatic", "adaptive"}


def feature_asked(view, question, whole_only=False):
    """The listed feature a question asks about: every long word of it in the question, or (unless whole_only) at
    least half of them. Returns (feature, whole) or None."""
    q = norm(set(words_of(question)))
    feats = [f for f in dict(view["lines"]).get("LISTED FEATURES", "").split("; ") if f]
    for feat in feats:
        fw = norm({w for w in words_of(feat) if len(w) >= 3})
        if fw and fw <= q and not ((q & QUALIFIERS) - fw):  # "cooled" front seats is not "heated front seats"
            return feat, True
    if not whole_only:
        for feat in feats:
            fw = norm({w for w in words_of(feat) if len(w) >= 4})
            # a half match counts only when the question names no other version of the feature ("rear" seats against "front")
            if fw and len(fw & q) * 2 >= len(fw) and fw & q and not ((q & QUALIFIERS) - fw):
                return feat, False
    return None


def list_items_asked(view, label, question):
    """For a list line (what to bring, steps left), the items the question names, or None for the whole list."""
    if label not in ("BRING", "STEPS LEFT"):
        return None
    q = norm(set(words_of(question)) - STOP)
    items = [i for i in dict(view["lines"])[label].split("; ") if norm({w for w in words_of(i) if len(w) >= 3} - STOP) & q]
    return "; ".join(items) if items and len(items) < len(dict(view["lines"])[label].split("; ")) else None


def code_answer_line(view, question):
    """The view line that best answers the question, by code alone (word overlap and a few cue words per line), or None."""
    q = norm(set(words_of(question)) - STOP)
    best, best_score, tie = None, 0, False
    for label, value in view["lines"]:
        if label in DESCRIBES:
            continue
        if label == "LISTED FEATURES":
            hit = feature_asked(view, question)
            score = (2 * len({w for w in words_of(hit[0]) if len(w) >= 3}) + 2 if hit[1] else 3) if hit else 0
        else:
            vwords = norm({w for w in words_of(value) if len(w) >= 3 or w.isdigit()})
            score = len(q & vwords) * 2 + 2 * len(q & norm(LINE_WORDS.get(label, set())))
        if score > best_score:
            best, best_score, tie = label, score, False
        elif score == best_score and score:
            tie = True
    return best if best_score >= 2 and not tie else None


# ------------------------------------------------------------------ checks on a draft

def numbers_in(text):
    return re.findall(r"\d[\d,]*(?:\.\d+)?", text)


def code_checks(draft, view, rec):
    """Every check code runs on a draft. Returns a list of (check, words) that failed."""
    fails = []
    text = draft or ""
    vtext = views.as_text(view).lower()
    fill = text.replace("{first_name}", "")
    m = found(fill, PATTERNS["draft_money"], allowed=PATTERNS["draft_money"]["allowed"])
    if m:
        fails.append(("money", m))
    p = found(fill, PATTERNS["draft_pressure"])
    if p:
        fails.append(("pressure", p))
    pr = found(fill, PATTERNS["draft_promise"])
    if pr:
        fails.append(("promise", pr))
    sy = found(fill, PATTERNS["draft_system"])
    if sy:
        fails.append(("system words", sy))
    vwords = set(words_of(vtext))
    claims = [w for w in found(fill, PATTERNS["draft_claims"]) if not all(x in vwords for x in words_of(w))]
    if claims:
        fails.append(("not in the record", claims))
    vnums = {n.replace(",", "") for n in numbers_in(vtext)}
    nums = [n for n in numbers_in(fill) if n.replace(",", "") not in vnums]
    if nums:
        fails.append(("a number not in the record", nums))
    known = set(words_of(vtext))
    starts = {m.group(1) for m in re.finditer(r"(?:^|[.?!]\s+)([A-Z][a-zA-Z0-9-]*)", fill.strip(" ,"))}  # a sentence's first word isn't a name
    capitals = [w for w in re.findall(r"\b[A-Z][a-zA-Z0-9-]+\b", fill) if w not in starts and w.lower() not in known and w not in ("Reply", "Yes", "No", "The", "Your", "You", "It", "We", "A", "An", "Thanks", "Here", "There", "When", "If", "Take", "See", "Pick", "Finish", "Use", "Accept", "Get", "Set", "Look", "This", "That", "Its", "Both", "And")]
    if capitals:
        fails.append(("a name not in the record", capitals))
    sentences = [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]
    words = len(words_of(fill))
    d = RULES["draft"]
    if not d.get("min_sentences", d["sentences"]) <= len(sentences) <= d["sentences"] or words > d["max_words"] or not text.strip().startswith("{first_name},") or "!" in text:
        fails.append(("shape", [f"{len(sentences)} sentences, {words} words"]))
    return fails


# ------------------------------------------------------------------ one shopper

def decide_one(rec, kind, ai):
    """ai is the source of the AI parts: an object with router(rec, view), draft(rec, view), check(rec, view, draft)."""
    out = {"id": rec["id"], "kind": kind, "stop": rec["stop"], "outcome": None, "reason": None}
    rule = contact_rule(rec, kind)
    if rule:
        out.update(outcome="do_not_contact", reason=rule)
        return out
    chan = pick_channel(rec, kind)
    if chan is None:
        out.update(outcome="do_not_contact", reason="no_channel")
        return out
    out["channel"] = chan
    zones = zones_of(rec)
    clock = run_clock().astimezone(dt.timezone.utc)
    if not zones:
        out.update(outcome="person", reason="no_safe_time")
        return out
    slot = next_slot(clock, zones) if kind == "waiting" else nudge_slot(zones)
    out["send_at"] = slot.isoformat() if slot else None
    out["send_at_shown"] = show_time(slot, zones[0]) if slot else None
    reply_by = next_slot(slot + dt.timedelta(minutes=RULES["reply_by"]["after_slot_minutes"]), zones) if slot else None
    if rec.get("state") in RULES["hold_states"]:
        out.update(outcome="person", reason="california", reply_by=show_time(slot, zones[0]))
        return out
    view = views.build(rec, kind, WORDING)
    out["view"] = view
    if kind == "waiting":
        msg = rec["message"]["text"]
        code = None
        if found(msg, PATTERNS["message_instructions"]):
            code = "instructions"
        elif found(msg, PATTERNS["message_complaint"]):
            code = "complaint"
        elif found(msg, PATTERNS["message_money"]):
            code = "money"
        r = ai.router(rec, view) or {}
        if r.get("not_checked") and not code:
            out.update(outcome="person", reason="not_checked", reply_by=show_time(reply_by, zones[0]))
            return out
        if r.get("asks_to_stop"):
            out.update(outcome="do_not_contact", reason="asked_to_stop", caught_by="second check")
            return out
        reason = code or r.get("reason")
        if reason:
            out.update(outcome="person", reason=reason, caught_by="code" if code else "second check",
                       reply_by=show_time(slot if reason == "complaint" else reply_by, zones[0]))
            return out
        # which line answers the question. With the second check, its line when both its reads agree on one (in every disagreement
        # on a question with an answer, across six sets, its line was the right one). Without it (the yardstick, the code-only
        # comparison), code's word match. A line that only describes the thing, or isn't a fact line, never answers.
        cline, jline = code_answer_line(view, msg), r.get("answer_line")
        line = jline or cline
        if line in DESCRIBES or line not in dict(view["lines"]):
            line = None
        # a feature question is answered only when the listing names that feature: never "yes" to a feature it doesn't list
        if line == "LISTED FEATURES" and not feature_asked(view, msg):
            line = None
        if not line or not r.get("answered"):
            out.update(outcome="person", reason="not_in_record", caught_by="second check" if r.get("answered") is False else "code",
                       reply_by=show_time(reply_by, zones[0]))
            return out
        part = (feature_asked(view, msg) or (None,))[0] if line == "LISTED FEATURES" else list_items_asked(view, line, msg)
        view = views.with_answer(view, line, part)
        out["view"] = view
    draft = ai.draft(rec, view)
    out["draft"] = draft
    if draft is None:
        out.update(outcome="person", reason="draft_failed", failed=[("no draft", [])], reply_by=show_time(reply_by, zones[0]))
        return out
    fails = code_checks(draft, view, rec)
    j = ai.check(rec, view, draft) or {}
    if j.get("not_checked"):
        fails.append(("not checked", []))
    fails += [(f, w) for f, w in j.get("fails", [])]
    out["based_on"] = j.get("support")
    if fails:
        out.update(outcome="person", reason="draft_failed", failed=fails, reply_by=show_time(reply_by, zones[0]))
        return out
    msg = views.assemble(draft, rec, chan, kind, RULES, WORDING, view.get("next_step", ""), view)
    if chan == "text" and len(msg["text"]) > RULES["draft"]["text_max_chars"]:
        out.update(outcome="person", reason="draft_failed", failed=[("too long for a text", [str(len(msg["text"]))])],
                   reply_by=show_time(reply_by, zones[0]))
        return out
    out.update(outcome="ready", message=msg)
    return out


def decide(records, ai):
    picked = queue(records)
    by_id = {r["id"]: r for r in records}
    results = [decide_one(by_id[i], k, ai) for i, k in sorted(picked.items())]
    return picked, results


def counts(results):
    c = {"shoppers": len(results), "ready": 0, "person": 0, "do_not_contact": 0}
    for r in results:
        c[r["outcome"]] += 1
    return c
