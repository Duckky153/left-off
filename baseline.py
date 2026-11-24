"""The yardstick with no AI at all: the same queue, contact rules, channel and time, routing by code alone (the word
lists and code's own answer-line match), and a fixed sentence for each kind of answer filled in from the record.

It answers a question whenever code finds the line that answers it, so the comparison with the AI is fair: where the
two differ is in catching money questions with no money word in them, and in how the reply reads.

Written and saved before any AI run; re-run on the locked word lists at the lock.
"""
import re

import followup_core as core


def first_sentence(view):
    lines = dict(view["lines"])
    label = view.get("answer_label") or view.get("true_label")
    value = lines.get(label, "")
    if label == "LISTED FEATURES":
        feat = view.get("answer")
        return f"yes, the listing includes {feat.lower()}." if feat else None
    if label == "STATUS":
        return "that car has sold." if value.startswith("sold") else "the car you saved is still for sale."
    if label == "SEATS":
        return f"it has {value}."
    if label == "NEW MATCHES":
        return f"{value.replace('cars match', 'cars match your search')}." if not value.startswith("no ") else "your search is still saved."
    if label == "STEPS LEFT":
        steps = [x for x in value.split("; ") if x]
        if not steps:
            return None
        return "the step left is to " + " and ".join(s[0].lower() + s[1:] for s in steps) + "."
    if label == "OFFER ENDS":
        return f"that offer {value}." if value.startswith("ended") else f"your offer is good through {value}."
    if label == "BRING":
        items = value.split("; ")
        return "please bring " + (", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else items[0]) + "."
    if label == "PRE-QUALIFIED":
        return "you finished pre-qualifying."
    return None


def draft_for(view):
    s1 = first_sentence(view)
    if not s1:
        return None
    return "{first_name}, " + s1  # the next step is added by code as a link, for both readers


class Yardstick:
    """The AI parts replaced by code: routing by the word lists and code's answer match, drafts by fixed sentences."""
    name = "no AI"

    def router(self, rec, view):
        return {"answered": core.code_answer_line(view, rec["message"]["text"]) is not None}

    def draft(self, rec, view):
        return draft_for(view)

    def check(self, rec, view, draft):
        return {}
