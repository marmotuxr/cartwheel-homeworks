# HW4 insights (draft, in Eve's words, for review_summary.md, interface_comparison.md and the video)

## Root cause behind the largest theme (wrong_about_order_records, 15 conversations)
- `list_my_orders` returns order ids, status and dates but **no product names**. The agent cannot see the item, so it tells the customer "you don't have that order" even when the order is row 1 (0100, 0103, 0104, 0109, 0110, 0114, 0115, 0095, ...).
- **Recommendation (Eve):** add product title and store name to `list_my_orders` results.
- **Backstop prompt rule:** never say an order doesn't exist unless a name search (`find_order`) returned nothing.
- **Separate variant:** the agent invents a store filter (`store: "2"`), gets an error, then says nothing was found (0176, 0209, 0185). Adding names to `list_my_orders` would not fix this, so it likely belongs in its own mode (fix: accept store names, clearer errors, only filter by a store the user named).
- **Full circle with HW1:** the HW1 product-verification finding was the same gap: `get_order` returned a product id without a title, so the agent called a vase a jacket.

## Designing the review interface: the reviewer is the user
- Human review of 100 traces is heavy; the review tool is a product and its user is the reviewer.
- Kept: aids that reduce effort without suggesting a verdict: highlight the order the customer means in tool tables, answer key as a checklist, one-tap tags, keyboard shortcuts, built-in dictation, text zoom, light mode, tool results as tables.
- Avoided: anything that suggests the answer before the reviewer decides: AI summaries shown up front, past verdicts on similar conversations (removed: "I want to view each one as an isolated incident"), automatic failure flags.
- Principle: effort-reducing aids are fine; answer-suggesting aids bias open coding. Anything opinion-shaped comes after the human decision, if at all.
- Evidence from use: chat briefings were far easier to read than the raw dashboard ("it's much easier to read this way"), which led to the deterministic aids above.

## Damaged or missing data needs a better user-facing answer (Eve)
- 8 reviewed conversations target a damaged record; the agent failed 6 (0043, 0077, 0078, 0080, 0194, 0196) and passed 2 (0037, 0205).
- The 6 failures are scattered across 4 tags (doesnt_escalate_when_required, wrong_about_order_records, didn't_escalate_bad_data, omits_critical_detail), but one fix (a "bad data playbook") would address all of them, so it is a candidate mode of its own.
- **Candidate mode `mishandles_damaged_data`:** a tool result contains missing, contradictory or invalid data that matters to the request, and the reply hides it, guesses around it, reports "not found", or does not escalate it. Close negatives: 0037, 0205.
- **What a good answer does:** (1) say what is known, (2) name the problem in plain words (no "null", no "retrieval issue"), (3) don't guess around it, (4) escalate so the record gets fixed, (5) give the next step and timing.
- **Example (null delivery date):** "I found your Classic Pencil Set order (#8002). It shows as delivered, but the delivery date is missing from our records, so I can't calculate your return deadline. I've asked our team to check (ticket #…); they'll reply within 24 hours."

## SPEC.md revision (approved by Eve, 2026-11-03)
- Added **ESC-5** (damaged order records always escalate) and **RESP-6** (how to state any damaged data; catalog damage is clarified with product IDs, not escalated).
- RESP-3 already required stating missing or inconsistent information; the gap was escalation, plain-language wording, stable identifiers, and never reporting a damaged record as "not found".
- Motivating annotations: support-0037, 0043, 0077, 0078, 0080 (orders); 0194, 0196, 0205 (catalog).
- Added **RESP-7** (approved by Eve): answer-then-confirm when the user only asks whether an action is possible (support-0088); act without an extra confirmation on a clear request (support-0058, 0060, 0062, 0063).
