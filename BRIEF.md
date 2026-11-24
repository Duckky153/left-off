# Left Off: the brief

Written 2026-11-23, before any code. Every shopper, car and message in this project is made up.

## The moment

People who stop partway through buying or selling a car online. They saved a car or a search, pre-qualified for financing, started a purchase, or got a trade-in or sell offer, and then went quiet. There are two kinds:

- someone who wrote back with a question that is still waiting for an answer;
- someone who simply went quiet for a few days.

For each one, Left Off picks one next step, a channel and a time, and drafts one short message from that shopper's own record. Anything about money, anything the record doesn't say, and any complaint goes to a person with a time to reply by. It sends nothing.

## What Carvana already has

Seen on carvana.com on 2026-11-23 (one car's page, the search page, the sell page):

- an AI-written summary on a car's page, marked "This content is AI-generated and some details may not be 100% accurate";
- a question box under it, "Looking for specific vehicle info?", with suggested questions about that car;
- Save Search, and a heart to save a car;
- dated price notes on a car's page;
- Get Pre-Qualified: "No credit impact, view real payments while shopping";
- the sell offer: "GET A REAL OFFER IN 2 MINUTES";
- Value Tracker.

The Product Management Apex posting names "Proprietary CRM and AI tools managing chat, email, SMS, and voice" and asks the role to "embed Sebastian into unified, conversational journeys". How Carvana follows up with shoppers who stop is not public. This is how I would approach one moment of that journey, on made-up data.

## Why people stop at each point

Published research on car shoppers in general, not Carvana's data:

| Where they stopped | What research says | So the message |
|---|---|---|
| Saved a car or a search | Buyers spend about 95 days in the market, 92 for used cars (Cox Automotive, 15th Annual Car Buyer Journey, 2024 study). "71% of vehicle buyers went into the process with an open mind, unsure of what vehicle they would buy" (Cox Automotive, Car Buyer Journey press release, 2026-01-13). | says one true thing about what they saved (still listed, sold, new matches) and doesn't push |
| Pre-qualified | Focus groups "generally viewed the process of automobile budgeting and financing as confusing and stressful" (CFPB, Consumer Voices on Automobile Financing, June 2016). | never names a number; a person takes any money question |
| Started a purchase | New-car buyers named "Signing paperwork (23%)" among the most frustrating parts (Cox Automotive, 2024 Car Buyer Journey: New Vehicle Buyers). | names the one step that is left |
| Trade-in or sell offer | "Among buyers who traded in a vehicle, 28% say their trade-in value was less than expected" (J.D. Power 2025 U.S. Sales Satisfaction Index, reprinted by MOTOR, November 2025). | never argues or restates the amount; a person explains it |
| A waiting question | Firms that tried to reach a new lead within an hour "were nearly seven times as likely to qualify the lead" as those that waited an hour longer (Harvard Business Review, "The Short Life of Online Sales Leads", March 2011). | answers within the hour when the record can |

## Requirements

Each is checked by a test or a score (see the README's "How it was tested").

1. Every message uses only facts in that shopper's record.
2. No message names a price, payment, down payment, loan length, finance charge, rate or APR, or says approved, pre-approved or guaranteed.
3. A message about money or credit, a complaint, an instruction to the writer, or a question the record doesn't answer goes to a person with a reply-by time, and the AI never sees it.
4. Nobody is contacted who asked to stop, opted out on any channel, is flagged do-not-contact, is already talking with customer care, was messaged in the last 7 days (for a nudge), or has no channel they agreed to.
5. A text goes only to someone who agreed to texts, and every text ends "Reply STOP to opt out." Every email names the sender and has a postal address and an unsubscribe line; a nudge also says it is an advertisement.
6. Messages are suggested only from 9:00 am up to 8:00 pm in the shopper's time zone, Monday to Saturday, not on federal holidays. An unknown time zone goes to a person.
7. A waiting question gets the next quarter-hour slot inside those hours. A quiet shopper gets 10:00 am on the next sending day. One message per stalled moment.
8. A shopper who pre-qualified is written to by email only. A nudge may say only that they finished pre-qualifying; a question about approval goes to a person.
9. A California shopper's message goes to a person, who adds what California requires.
10. It sends nothing. There is no code that sends, texts, emails or posts.
11. A draft is one sentence, 25 words or fewer; a whole text is 320 characters or fewer.
12. No record holds age, sex or any similar field, and neither a shopper's name nor a pronoun reaches the AI.

## What it does not do

It doesn't send, schedule or approve anything; answer questions about price, payments, credit or value; suggest other cars for sale; or decide who gets a message by anything but where they are in the journey.

## Questions for practice

Written before the practice run. Their answers were not known when written.

1. Does the second check catch money questions that the word list misses?
2. Does the writer answer the question in at least 9 of 10 practice drafts that have one?
3. How many good drafts does the second check hold by mistake?
4. Does a larger open model read better than the small one without breaking a rule?

What to change if one fails is decided after the result, and logged in `DECISIONS.md` and `prompts/CHANGELOG.md`.
