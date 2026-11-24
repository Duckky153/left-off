# Left Off: the test plan

Pick 1 in 5 quiet shoppers at random and don't send them this nudge. Everyone else gets it. After two weeks, compare how many in each group took their next step. Roll it out only if the nudged group is clearly ahead and people aren't opting out or complaining more.

Written 2026-11-23, before any code. Nothing here has been run on real shoppers.

The question: **does one short nudge bring quiet shoppers back?** Answers to questions are not tested: nobody waits for an answer because of a test.

| Part | Setting |
|---|---|
| Unit | The shopper, counted once, at their first quiet stall inside the test window. A shopper who stalls again keeps their group. |
| Who is in | Quiet for 3 to 30 days at one of the stop points (saved a car or a search, pre-qualified, a trade-in or sell offer), no unanswered message, not part-way through a purchase, and allowed to be contacted. The contact rules are applied before the split. |
| Control | Business as usual: everything shoppers get today. The held-back group misses only this nudge, and their questions are answered as usual. |
| Held back | 1 in 5, by a hash of the shopper ID with a fixed salt written down before the test, assigned before any draft is written. |
| Counting | Everyone assigned to the nudge group counts, including shoppers whose nudge was held for a person. |
| The number | Shoppers who move one step on within 14 days, per 100: saved a car or a search, then pre-qualified or started a purchase; pre-qualified, then started a purchase; got an offer, then accepted it. Nudge group minus held-back group. |
| Also read | Purchases finished within 30 days, per 100. Reported, never deciding. |
| Watched | Opt-outs per 100 nudges, complaints per 1,000, and nudges held for a person. Their lines are starting guesses: opt-outs under 1 per 100 and complaints under 1 per 1,000 (Carvana's own numbers would set them); more than 1 in 4 nudges held for a person means "fix before rolling out". |
| Stop at once | Any message sent that breaks a hold or a contact rule. |
| Decision | Read once, 14 days after the last shopper enters. Roll out if the nudge group is ahead with the 95% range of the gap above zero, and opt-outs and complaints are under their lines. Otherwise keep business as usual. No early win calls. |
| How many | If 8 in 100 move on without the nudge (a guess until real numbers replace it), finding a gain of 1.5 per 100, 8 times out of 10, takes about 17,700 shoppers: 3,544 held back and 14,176 nudged. That is the cautious formula; the other common one gives 16,590. `docs/sample_size.py` prints both and a table for other guesses. |
| How long | Until enough shoppers have entered, then 14 days. No traffic number is guessed. |

## Which stop point should move most, and why

- **An offer that is still open** is the closest to a decision: one step (accept) and a real end date.
- **Saved a car that is still listed** is the most common and the earliest: a small move per 100, many shoppers.
- **Pre-qualified** is where money worries sit: the nudge can only say they finished pre-qualifying, so expect the smallest move.

These are guesses written down first. The one deciding number covers every stop point in the test.

