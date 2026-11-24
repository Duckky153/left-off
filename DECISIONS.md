# Left Off: decisions

Every decision that shaped the build, in order: what was decided, who decided it, and what caused it. Newest at the bottom.

| | Decision | Who decided | Why |
|---|---|---|---|
| D1 | The moment: shoppers who stop partway, two kinds (a waiting question, a quiet stall), one message each, nothing sent | The plan, approved by me on 2026-11-23 | It is one real moment of a car-buying journey, and it fits what I had seen in follow-up work |
| D2 | Who answers a waiting question: the AI drafts a reply within the hour, checked twice, and a person sends it; money, anything the record doesn't say and complaints go to a person | Me, 2026-11-23 | The shoppers who write in are the ones most ready to move, and most of their questions are answered by their own record |
| D3 | A question about payments, credit or price goes to a person with a reply-by time, and the AI never sees it | Me, 2026-11-23 | It is where one wrong word becomes a payment, a rate or a sense of approval; a person can see the shopper's real terms; and in planning a small model repeated a payment question back when one got through |
| D4 | The test holds back 1 in 5 quiet shoppers, at random; questions and purchases under way are never held back | Me, 2026-11-23 | Most quiet shoppers get the nudge while it is tested; 1 in 2 would finish sooner but hold back about 5,600 people instead of about 3,500 |
| D5 | The number that decides the test: shoppers who move one step on within 14 days, per 100 | The plan, approved by me | Measured where the nudge points, and it shows within two weeks |

## Changes made because a review of the plan found a problem

An AI reviewer read each version of the plan against the source files before any code. These changes are in the plan I approved.

| | What the review found | What changed |
|---|---|---|
| P1 | The first plan only picked up shoppers after 3 quiet days, so a question would wait days for an answer | Two kinds of shopper: a waiting question gets a reply within the hour; only quiet shoppers wait 3 days for a nudge |
| P2 | The no-AI comparison was a fixed template that could not answer any question, so the AI would win by default | The no-AI comparison answers questions too, from the same record, with code alone |
| P3 | The test held back answers as well as nudges, from shoppers who were already getting messages | The control is business as usual; only the nudge is held back; questions and purchases under way never are |
| P4 | The shopper's first name and a pronoun would reach the AI | The AI writes `{first_name}`, code fills it in after the checks, and every car is "your car" |
| P5 | A planned test case could not come out as written under the rules | Every one of the 40 cases is written down with the rule meant to produce it |

## Decisions from the planning tests

Before any build code, an AI helper tried four small open models on five made-up shoppers (`prompts/planning-tests/`):

| | What the test showed | What it decided |
|---|---|---|
| T1 | The smallest model, given a shopper's question "If I put more down can I get the monthly payment under $400?", wrote the payment question and "$400" back into its draft | The 4B model writes the drafts, not the smaller ones. Money questions were already planned to go to a person before any draft; this showed what happens if one ever slips through |
| T2 | When the next step was written about the shopper ("Come back to his offer."), the model copied it word for word | Code writes the next step to the shopper ("come back to your offer") |
| T3 | A one-sentence change to the prompt made the model drop the answer to a question | That change was rolled back; one change at a time from then on |
| T4 | Drafts like "you stopped at the offer" sound as if the shopper is being watched | The prompt's first sentence says one useful true thing instead of where they stopped |
| T5 | On the 12 practice shoppers who reach the draft step, a larger open model (7.6 billion parameters) skipped the required opening on most drafts, wrote one sentence where two were asked, invented a step ("Pick a drive option") and reworded dates; the small model (4 billion) followed the format on all 12 and stayed with the facts, with two small slips ("November 26" for "Nov 26"; "your pickup year") | The small model writes the drafts. Both runs are in `runs/` |

## The decision changed by the scored test

| | What the one scored run showed (prompt v2, second check lo-q3, frozen) | What changed |
|---|---|---|
| D6 | Safe but holding far too much: 0 of 14 wrongly marked ready, but only 6 of 19 shoppers who were fine came out ready, and 2 of 12 answerable questions were answered (the no-AI yardstick: 5 of 12, and 1 wrongly ready). The cause: code's word match had a veto over which line answers a question, and it picked a description line (the offer, the search) for 6 of the 12; the second check picked the right line in every one. Code's "did it answer" test also held correct answers worded differently ("no longer available" for "sold"; "two" for "2") | Code no longer picks an answer from a description line; when code finds no line, the second check's line stands if both its reads agree and it is sure; whether a draft answers the question is judged by the second check, on meaning. The safety checks on every draft are unchanged. Tested on a fresh set written afterwards by a different AI family, so the change is not tuned to the test it failed |

## Changes after the design reviews, and what tested them

Each change below was tried on the practice shoppers first, then read once on a fresh set written afterwards by a different AI family (OpenAI's model), with its answer key committed before the run. The numbers as tested are in `runs/scores-*-at-test.json`.

| | What showed it | What changed | Tested on |
|---|---|---|---|
| R1 | Design review 1: 11 of 13 drafts ended "whenever you are ready"; two were identical | Prompt v3: name the car, no readiness phrases | Fresh set 2: 0 of 8 wrongly ready, 4 of 9 kept, 3 of 6 answered |
| R2 | Design review 2: drafts still ended on stock next-step lines ("Take another look.") | The AI writes the fact only; code adds the next step as a link, like the store's one button (v5 copied the next step anyway; v6 stopped showing it to the writer) | Practice |
| R3 | Practice: plain offer dates read as promises ("your offer ends Nov 26", 0.17 to 0.46) | Second check lo-q5: the promise question no longer counts "something will happen at a certain time" | Practice |
| R4 | Practice: correct "yes, ..." answers read 0.75 to 0.83 for grounding, the same band as a made-up phrase | Second check lo-q6: a yes or no that answers the question counts as written when the rest of the sentence is | Fresh set 3 (prompt v6): 0 of 8 wrongly ready, 8 of 9 kept, 5 of 6 answered; the no-AI yardstick marked 2 ready that needed a person |
| R5 | Prompt v6 still ended "Write only the two sentences." under "Write one short sentence" | Prompt v7 fixes that line; code allows two sentences, still 25 words | Fresh set 4: 0 of 8 wrongly ready, 9 of 9 kept, 6 of 6 answered; yardstick 2 wrongly ready |
| R6 | Two AI graders, who saw only the grading rules, the facts and each draft, read all 18 ready drafts from v7 and agreed on every one: three said the car "is ready for you to pick a delivery time", which no record says | Code holds "ready" when the facts don't say it (it can only hold, never clear). The purchase link reads "See your purchase" | Re-scored: fresh set 4 keeps 8 of 9; the 40 on the page: 7 ready, 0 wrongly |
| R7 | Design review 3: money questions labelled "orders to the writer" (every "could you raise my offer" also read 0.24 to 0.37 as orders, and a fixed order picked that first) | The strongest reading over its limit sets the reason; a request to stop still comes first | Fresh sets 5 and 6: 16 of 16 holds for the right reason |
| R8 | Design review 3: Ben asked what to bring and was told "answer not found" beside Omar, whose same question was answered. Across six sets there were three disagreements on questions with an answer, and the second check's line was right in all three; code's word match had tied ("when", "need") and taken the first line listed | The second check's line stands when both its reads agree; without the second check (the yardstick), code's word match picks; a tie in code's match is no find | Fresh sets 5 and 6 |
| R9 | On all six sets, real complaints read 0.87 to 0.98 and real orders to the AI 0.97 to 0.99; every other message read 0.37 or lower, apart from requests to stop, which are decided first | Complaint and orders limits from 0.30 and 0.20 to 0.50. Money stays at 0.20: there true and false cases overlap more, and money goes to a person by my decision (D3) | Fresh sets 5 and 6 |
| R10 | The writer turned the bare step "Pick a delivery time" into "the car is ready for you to pick a delivery time" on three sets, and added a second sentence to an offer nudge | Code states purchase and offer facts as plain phrases ("you still need to pick a delivery time"), as it already did for pre-qualifying; one sentence again (the case for two came from prompt v6's stray last line); prompt v9 adds "never the word ready" (v8, which also asked for one extra detail, was tried on practice and dropped); a saved car's status carries its miles; email subjects name the topic | Fresh set 6. The writer still wrote "ready" once; code held it |
| R11 | Seven fresh reviewers of the finished build. An engineer showed that a question about a feature the car doesn't have could come out "yes"; "Can I stop by Saturday?" read as a request to stop; "60k mile service" read as money and "Carfax report" as a complaint; a phone area code the table doesn't know was ignored; and saved reads were reused after the facts' wording changed. Two showed the code-only comparison had never been measured: shoppers the second check stopped had no draft, so code alone was counted as holding them | A feature question is answered only when the listing names that feature; "stop" counts only in phrases or alone; a "k" before "mile" isn't money; "report" isn't a complaint; an unknown area code means no time zone; every saved read carries a fingerprint of what it was asked and is read again when that changes; the code-only comparison now drafts its own shoppers. Tests for each | The 40 re-read on today's facts: 8 ready, 0 wrongly. Without the second check: 2 wrongly ready on the 40 and on fresh sets 5 and 6 |

What the AI check still gets wrong, left as it is: it reads "you finished pre-qualifying" as money (0.26 to 0.35) and "is no longer available" as money (0.13, limit 0.10). Both go to a person, and the page says the AI check read them that way. The money limit stays strict.
