# Changelog: the prompt and the second check

Every change, what caused it, and what the next run showed. Quotes and numbers are copied from the run files by script.

## v0, planning tests (before any build code)

An AI helper tried four small open models on five made-up shoppers while planning (`prompts/planning-tests/`). What they showed: the smallest model wrote a shopper's payment question and "$400" back into its draft (money questions were already planned to go to a person; this showed why); a next step written about the shopper was copied word for word, so code writes it to the shopper; one prompt edit dropped an answer and was rolled back; "you stopped at the offer" sounds watched, so sentence one says a useful true thing instead. Then a larger 7.6-billion-parameter model was compared on the practice set and wrote worse drafts (`runs/practice-candidate-cmp7b-1.json` against `runs/practice-candidate-cmp4b-1.json`).

## Second check, lo-q1 to lo-q2 (practice run 1)

Run: `runs/practice-v1-1.json`, `checks/practice-lo-q1.json`. With lo-q1, 1 of the 12 practice shoppers the key marks ready came out ready.

What it read wrongly, copied from the check file:
- Ordinary questions read as instructions to the writer: P-2011 "Do I need to bring the title?" [0.22, 0.23]; P-2003 "Any new ones with AWD?" [0.3, 0.28] (limit 0.20). The question said "or say something specific", which every question does.
- Haggling read as a complaint: P-2014 "Is that the best you can do?" [0.74, 0.73] (limit 0.30).
- Plain dates read as promises and offers as money: P-2012 promise [0.94, 0.93], money [0.4, 0.37]; P-2010 promise [0.88, 0.9], money [0.4, 0.34].
- Correct sentences just under the grounding bar: P-2001 sentence 1 [0.82, 0.84], sentence 2 [0.8, 0.86] (bar 0.85).

Changed: the wording of five questions (instructions, complaint, grounded, money, promise), each saying what does not count. Thresholds unchanged.

Result after the change (`checks/practice-lo-q2.json`): 16 of 24 practice shoppers as keyed (13 with lo-q1). The instruction and complaint misreads are gone.

## Round 2: prompt v2, second check lo-q3, two code fixes (practice run 2)

What run 2 showed, copied from the check and run files:
- Correct sentences just under the grounding bar: P-2005 "yes, it seats eight" [0.84, 0.82]; P-2012 sentence 2 [0.86, 0.83]. The made-up "match your pickup year" (P-2004) scored [0.8, 0.77]. Changed: grounded bar 0.85 to 0.80.
- A plain logistics question just over the money bar: P-2018 "Do you pick the car up or do I drop it off?" [0.09, 0.11]; the money questions scored 0.76 and up. Changed: money bar on questions 0.10 to 0.20.
- The writer wrote "November 26" where the facts say "Nov 26" (P-2009, held by code). Changed: prompt v2 says to copy dates exactly. One change from v1.
- "Do I need to bring the title?" was answered ("yes, you must bring the title") but held because the draft didn't repeat the whole list (P-2011). Changed in code: a list line's answer is the items the question names.
- A pre-qualified nudge said "your pre-qualified status is complete" and was held as money [0.67, 0.64] (P-2006). Changed in code: the fact reads "you finished pre-qualifying on <date>".

Result after round 2 (`runs/practice-v2-1.json`, `checks/practice-lo-q3.json`): 20 of 24 practice shoppers as keyed. Every shopper the key holds was held; the four differences are extra holds, none a wrong "ready".

## What practice run 3 showed, and why nothing more was changed

The plan allows two rounds of changes on practice before the freeze, so these stay as they are and are counted in the scored run:
- P-2004: "here are 4 new cars that match your pickup year": a made-up phrase, held by code.
- P-2006: "you finished pre-qualifying on Nov 14": the second check still reads pre-qualifying as credit, money [0.34, 0.41].
- P-2008: "upload your proof of insurance whenever you are ready": under the grounding bar, [0.77, 0.71].
- P-2011: "yes, you need to bring the title": held by code's repeats-the-message check, because a natural answer echoes the question.

Practice questions, answered:
1. The second check caught the money questions with no money word ("Any wiggle room on this one?", "Is that the best you can do?", "Can I put less down?"); the word list caught none of them.
2. The writer answered the question in every practice draft that had one (6 of 6).
3. With lo-q3 the second check held 2 good drafts by mistake (P-2006, P-2008).
4. The larger open model read worse and broke the format (v0).

## After the scored run: v3 to v7, second check lo-q4 to lo-q6

- **v3** (after design review 1): name the car, no readiness phrases, one or two sentences. Fresh set 2.
- **v4**: one change from v3, "end on the next step". Practice still added "now" on the same three drafts. Dropped; kept as tried.
- **v5** (after design review 2): one sentence with the fact; code adds the next step as a link. Practice: the writer still copied the next step onto every draft ("take another look"). Dropped.
- **v6**: the writer no longer sees the next step at all. Practice: no copied endings. Fresh set 3.
- **v7**: v6's last line still read "Write only the two sentences." (left from v3). Now "Write only that sentence." Nothing else changed. Fresh set 4.
- **lo-q4**: inviting the shopper to act whenever they are ready is not a promise.
- **lo-q5**: the promise question dropped "something will happen at a certain time", which every offer end date is. Practice v6: "the trade-in offer ended on Nov 21" went from [0.37, 0.46] to [0.03, 0.03].
- **lo-q6**: a yes or no that answers the question counts as written. Practice v6: "yes, it has heated front seats" went from [0.79, 0.75] to [0.90, 0.91]; the made-up "matching your pickup year" stayed at [0.80, 0.79], which code also holds.

Also seen: the same sentence read for grounding moved from [0.82, 0.81] to [0.79, 0.75] between two runs when only another question's wording changed. Reads near a limit can flip; the limits were not moved for it.

## After design review 3: v8, v9, lo-q7

- **v8**: a nudge about a saved car adds one detail of that car (its miles or one feature); never the word "ready". Practice: the detail was skipped where it was meant to go, a purchase draft gained car details and a second sentence, and "pickup year preference" came back. Dropped.
- **v9**: v7 plus one line, never the word "ready". The saved car's miles now come from code, in its status line. Fresh sets 5 and 6.
- **lo-q7**: limits only, no wording changed. Complaint 0.30 to 0.50, orders to the AI 0.20 to 0.50, and the strongest reading over its limit sets the reason. The saved reads of the practice set and the 40 were re-decided under the new limits with no new call (`jev_check.py rederive`).
- Seen on fresh set 6: correct sentences held at 0.78 and 0.79 against 0.80, and a plain answer read as money at 0.21 against 0.10. Not changed after seeing it; listed in the README under what I'd change next.
