# How it was built

AI did the planning, the code, the sample data and the reviews. I chose the product decisions and said yes or no at each step.

## 1. Homework

AI read the Product Management Apex posting and Carvana's public pages for buying, selling and financing, and measured the site's look (colors, font, spacing) by script. The moment, shoppers who stop partway, came out of that homework. Following up fast with people who went quiet is close to work I have done before.

## 2. The plan

Four AI helpers each wrote one part: the rules for messaging car shoppers (sending hours, opt-outs, what an ad about credit may say), which model should write the drafts, the screen, and every claim the pitch may make. AI merged them into one plan.

Two fresh AI reviewers read the plan against the files, and their findings changed it (`DECISIONS.md`, P1 to P5):

- The plan had made every product decision itself. The real trade-offs became mine.
- A waiting question would have sat for three days. It now gets a reply in the next sending slot.
- The no-AI comparison could not answer any question, so the AI would win by default. It now answers from the same record with code alone.

## 3. My decisions

I said yes to the plan, then answered four choices, each offered with a recommendation and what would change the other way:

- **Who answers a waiting question:** the AI drafts it and a person approves it. The other choice was a person always answering, with the AI only nudging.
- **A question about payments, credit or price:** a person handles it, and the writing AI never sees it.
- **The test:** hold back 1 in 5 quiet shoppers, not 1 in 2.
- **How my pitch opens.**

I took the recommended option on all four (`DECISIONS.md`, D2 to D4). I said yes to the main screen and asked for more reviews, fixes, then publishing.

## 4. The code and the sample

AI wrote all the code and its tests. Before the writer drafted for any scored shopper:

- AI checked 22 real car models and trims against each maker's published feature table, keeping only features listed as standard.
- AI wrote the answer key from the rules: for each shopper, the outcome the rules should produce, and why.
- AI helpers wrote each shopper's message one at a time, from a slot ("asks, without any money word, whether the price can come down") and the writing rules, not from a template.

After the scored run, without seeing its results, a different AI family (OpenAI's model) checked 20 of the key's labels against the rules alone. It agreed with all 20.

## 5. The AI step

While planning, an AI helper tried four small open models on five made-up shoppers. The smallest wrote a shopper's "$400" monthly payment back into its draft. So the 4 billion parameter model writes the drafts, and money questions never reach it (`DECISIONS.md`, T1 to T5).

The prompt and the second check's questions were tuned on 24 practice shoppers, each change logged with the result that caused it (`prompts/CHANGELOG.md`). Then everything was fingerprinted and the 40 were read once.

That run held far too much: 6 of 19 fine shoppers came out ready. AI found the cause and changed it (`DECISIONS.md`, D6). From then on, each change was tested on a fresh set of 20 shoppers whose messages a different AI family wrote afterwards. There were six.

## 6. Reviews

- Four fresh AI design reviews compared the page with Carvana's own screens. Their findings led to the one-screen layout, larger type, plain labels, and four rule changes (`DECISIONS.md`, R7 to R10).
- Two AI graders, given only the grading rules, the facts and the drafts, read every ready draft. They found a phrase that said more than the record ("is ready for you to pick a delivery time"). Code now holds it.
- Seven more fresh AI reviewers read the finished build: as a Carvana product manager, as an engineer who recomputed every score, for truth and privacy, as a first-time visitor, for anything that reads machine-written, the publish path, and the whole build. Their findings are fixed or listed in the README's limits (`DECISIONS.md`, R11).

Nothing here sends a message, and nothing was ever run on real shoppers.
