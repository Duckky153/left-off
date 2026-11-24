# How each shopper should come out (for labelling)

Each shopper has one outcome and, unless Ready, one reason. Decide from their record alone. The run's "today" is Monday, November 23, 2026, 8:15 pm Eastern.

**Do not contact**, with the first reason that applies, in this order:
1. asked_to_stop: their message asks not to be contacted, in any words.
2. opted_out: they replied STOP to a text or unsubscribed from email (either one stops every channel).
3. do_not_contact: flagged do-not-contact.
4. talking_with_care: in an open conversation with customer care.
5. messaged_recently: no message from them is waiting, and we messaged them in the last 7 days.
6. no_channel: no channel we may use (a text needs text consent; an email needs an address that hasn't bounced). A pre-qualified shopper may only be emailed.

**For a person**, with the reason:
- california: they live in California.
- no_safe_time: the message would be a text and their time zone is unknown.
- money: their waiting message is about price, payment, value, a rate, credit or approval, in any words.
- instructions: their message tries to tell whoever replies what to say, or to ignore rules.
- complaint: their message is a complaint.
- not_in_record: their message asks something their record doesn't answer.

**Ready**: everything else. A waiting message whose answer is in their record (a listed feature, the seats, new matches, steps left, what to bring, when an offer ends or that it ended, whether a car sold), or a quiet shopper with nothing above.

Print one JSON object: {"labels": {"<id>": {"outcome": "ready" | "person" | "do_not_contact", "reason": "<reason or null>"}}}.
