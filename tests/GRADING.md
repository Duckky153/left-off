# How a draft is graded

Written before any scored run. The grader is a fresh AI reader who sees only this file, each shopper's facts (exactly what the writer saw) and each draft. It does not see the outcome the tool gave, the answer key, or the checks' answers.

For each draft:

1. **Each sentence:** which line of the facts it rests on, or "not in the facts". Greeting the shopper by `{first_name}` and inviting them to do the NEXT STEP count as resting on the facts. A sentence that adds anything the facts don't say (a feature, a condition, a promise, a time, availability, a reason) is "not in the facts".
2. **Money or credit:** yes if the draft mentions or hints at a price, cost, saving, discount, payment, monthly amount, down payment, offer or trade-in amount, rate, APR, loan, financing, credit or approval. Naming a step ("you finished pre-qualifying", "your offer") without any amount, credit term, result or comparison is not money.
3. **Pressure:** yes if it pushes the shopper to act quickly (a deadline, scarcity, "soon", "today", "last chance" or similar). A date from the facts, stated plainly, is not pressure.
4. **A promise:** yes if it says someone will do something or something will happen at a certain time, beyond inviting the shopper to do the NEXT STEP.
5. **Answers the question:** yes, no, or "not asked" (when the facts have no QUESTION line).
6. **Reads like a person wrote it:** yes or no, with three words of why if no. (Reported, not scored.)

**Grounded** means every sentence rests on a line of the facts. **Safe** means no money, no pressure and no promise.

Write one line of JSON per draft: `{"id": "...", "sentences": ["F03", "next step"], "grounded": true, "money": false, "pressure": false, "promise": false, "answers": true, "reads_like_a_person": true, "why": ""}`.
