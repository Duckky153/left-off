"""The facts the writer may see, built by code from one shopper's record.

Never in a view: the shopper's name (the writer writes {first_name}; code fills it in after every check), pronouns
(the shopper's own car is "YOUR CAR"), any money field (price, price drop, payment estimate, offer amount, rates,
credit), any contact detail, consent flag or date the message doesn't need, or a message that was held.
"""
import datetime as dt

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
NEVER = ("price", "price_lowered", "payment_estimate", "amount", "rate", "apr", "credit", "first_name", "last_initial", "phone",
         "email", "age", "sex", "gender", "pronoun")


def day(s):
    d = dt.date.fromisoformat(s[:10])
    return f"{MONTHS[d.month - 1]} {d.day}"


def car_line(car):
    return f"{car['year']} {car['make']} {car['model']} {car['trim']}, {car['color']}, {car['miles']:,} miles"


def build(rec, kind, wording):
    stop, lines = rec["stop"], []
    car = rec.get("car")
    ns = wording["next_step"]
    true_label, next_step = None, ns.get(stop)
    if stop in ("saved_car", "purchase") or (stop == "prequalified" and car):
        lines.append(("CAR", car_line(car)))
        if stop == "saved_car":
            if car.get("sold_at"):
                lines.append(("STATUS", f"sold on {day(car['sold_at'])}"))
                next_step = ns["saved_car_sold"]
            else:
                lines.append(("STATUS", f"still for sale, with {car['miles']:,} miles"))
            true_label = "STATUS"
        if car.get("features"):
            lines.append(("LISTED FEATURES", "; ".join(car["features"])))
        if car.get("seats"):
            lines.append(("SEATS", f"{car['seats']} seats"))
        if car.get("drivetrain"):
            lines.append(("DRIVETRAIN", car["drivetrain"]))
    if stop == "saved_search":
        s = rec["search"]
        lines.append(("SEARCH", s["desc"]))
        n = s.get("new_matches", 0)
        lines.append(("NEW MATCHES", f"{n} new cars match" + (f", all with {s['match_feature']}" if s.get("match_feature") and n else "") if n else "no new matches"))
        true_label = "NEW MATCHES"
        if not n:
            next_step = ns["saved_search_none"]
    if stop == "prequalified":
        lines.append(("PRE-QUALIFIED", f"you finished pre-qualifying on {day(rec['prequal']['done_at'])}"))
        true_label = "PRE-QUALIFIED"
    true_text = None
    if stop == "purchase":
        lines.append(("STEPS LEFT", "; ".join(rec["purchase"]["steps_left"])))
        true_label = "STEPS LEFT"
        steps = [x[:1].lower() + x[1:] for x in rec["purchase"]["steps_left"]]
        if steps:
            true_text = "you still need to " + (", ".join(steps[:-1]) + " and " + steps[-1] if len(steps) > 1 else steps[0])
    if stop in ("trade_in_offer", "sell_offer"):
        o = rec["offer"]
        lines.append(("YOUR CAR", car_line(o["car"])))
        lines.append(("OFFER", "a trade-in offer on your car" if stop == "trade_in_offer" else "an offer to buy your car"))
        what = "your trade-in offer" if stop == "trade_in_offer" else "the offer for your car"
        if o.get("ended"):
            lines.append(("OFFER ENDS", f"ended on {day(o['ends_at'])}"))
            next_step = ns[f"{stop}_ended"]
            true_text = f"{what} ended on {day(o['ends_at'])}"
        else:
            lines.append(("OFFER ENDS", day(o["ends_at"])))
            true_text = f"{what} ends {day(o['ends_at'])}"
        true_label = "OFFER ENDS"
        if o.get("bring"):
            lines.append(("BRING", "; ".join(o["bring"])))
    view = {"lines": lines, "true_label": true_label, "true_text": true_text, "next_step": next_step if kind == "quiet" else next_step,
            "answer": None, "answer_label": None, "question": None}
    if kind == "waiting":
        view["question"] = rec["message"]["text"]
    return view


def with_answer(view, label, part=None):
    """The question's answer line. For a feature question, the answer is the one feature asked about."""
    v = dict(view)
    v["answer_label"] = label
    v["answer"] = part or dict(view["lines"])[label]
    return v


def writer_lines(view, channel, next_step=True):
    """The exact text the writer gets, in order. From prompt v6 the writer doesn't see the next step: code adds it as a link."""
    out = [f"CHANNEL: {channel}"] + ([f"NEXT STEP: {view['next_step']}"] if next_step else [])
    out += [f"{label}: {value}" for label, value in view["lines"]]
    if view.get("answer"):
        out.append(f"QUESTION: {view['question']}")
        out.append(f"ANSWER (from {view['answer_label']}): {view['answer']}")
    elif view.get("true_label"):
        out.append(f"TRUE THING (from {view['true_label']}): {view.get('true_text') or dict(view['lines'])[view['true_label']]}")
    return out


def as_text(view):
    lines = [f"NEXT STEP: {view['next_step']}"] + [f"{label}: {value}" for label, value in view["lines"]]
    if view.get("question"):
        lines.append(f"QUESTION: {view['question']}")
    if view.get("answer"):
        lines.append(f"ANSWER: {view['answer']}")
    return "\n".join(lines)


def numbered(view):
    """The facts with line numbers, as the second check sees them (F01, F02 ...)."""
    rows = [("NEXT STEP", view["next_step"])] + list(view["lines"])
    if view.get("answer"):
        rows.append(("ANSWER", view["answer"]))
    return [(f"F{i:02d}", f"{label}: {value}") for i, (label, value) in enumerate(rows, 1)]


def subject_for(rec, kind, wording, view=None):
    """An email subject that names the topic: what the reply answers, or what the nudge is about."""
    car = rec.get("car") or (rec.get("offer") or {}).get("car") or {}
    fill = {"make": car.get("make", ""), "model": car.get("model", ""), "feature": (view or {}).get("answer") or ""}
    label = (view or {}).get("answer_label")
    pattern = wording["reply_subject"].get(label) if kind == "waiting" and label else wording["email_subject"].get(rec["stop"])
    if not pattern or ("{make}" in pattern and not car):
        pattern = wording["email_subject"]["reply"] if kind == "waiting" else "Your next step"
    out = pattern.format(**fill)
    return out[:1].upper() + out[1:]


def assemble(draft, rec, channel, kind, rules, wording, view_next_step="", view=None):
    body = draft.replace("{first_name}", rec["first_name"])
    lines = rules["channel_lines"]
    cta = view_next_step[:1].upper() + view_next_step[1:] if view_next_step else ""
    if channel == "text":
        t = lines["text"]
        return {"channel": "text", "text": f"{t['prefix']}{body} {cta}: {t['link']} {t['suffix']}", "cta": cta}
    subject = subject_for(rec, kind, wording, view)
    footer = [x for x in lines["email"]["footer"] if kind != "waiting" or "advertisement" not in x.lower()]  # a reply to their own question isn't an ad
    return {"channel": "email", "subject": subject, "body": body, "cta": cta, "footer": footer}
