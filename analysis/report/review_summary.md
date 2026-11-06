# HW4 review summary: Cartwheel failure taxonomy

Reviewer: Eve (human open coding and all final decisions). Agent model under review: `gpt-4o-mini`, HW3 final run (250 support scenarios).
Review interface: `analysis/review_app/` (see `interface_comparison.md`).
Walkthrough video (4:54): https://share.descript.com/view/9piAAkpMugc

## Reviewed sample

**100 distinct conversations** (each conversation groups every trace in one session), in four batches. No conversation counts toward more than one batch.

| Batch | Method | Size | Shopper / merchant / support | Coverage / challenge | Failures |
|---|---|---|---|---|---|
| 1 | 15 uniform random + 15 cluster representatives (k-means on shape: messages, tool calls, tools, role, intent) | 30 | 14 / 11 / 5 | 25 / 5 | 11 |
| 2 | Stratified by **role**, chosen before looking at outcomes (10 each) | 30 | 10 / 10 / 10 | 22 / 8 | 14 |
| 3 | Depth searches for candidate modes (20) + close negatives (5) | 25 | 18 / 4 / 3 | 17 / 8 | 18 |
| 4 | 15 uniform random after the taxonomy was drafted (stability check) | 15 | 8 / 5 / 2 | 9 / 6 | 9 |
| **Total** | | **100** | **50 / 30 / 20** | **73 / 27** | **52** |

31 of the 100 are multi-turn. Intents: policy question 19, product search 18, order status 16, refund 16, cancellation 12, dispute 8, account change 6, return deadline 3, out of scope 2.
Batch 3 has the highest failure rate by design: it was retrieved to contain likely failures.

## Method

1. **Open coding.** For each conversation I read the answer key, the turns and the tool results, and wrote the **first failure** in my own words, or recorded "no failure observed". Extra issues went into highlight notes on the exact text.
2. **Axial coding as I went.** After each batch I compared notes and grouped them under working tags, merging or splitting by the handout's test: *would one product change fix both?* Tag history is in `analysis/state/themes.json`.
3. **Depth search (Batch 3).** Deterministic filters over unreviewed conversations proposed likely positives and close negatives for each candidate mode. Each was a retrieval signal, not a label: I reviewed every one. **15 accepted, 10 rejected** (`analysis/state/suggestions.json`).
4. **Stability check (Batch 4).** A fresh random sample, reviewed after the taxonomy was drafted.
5. **Structured labeling.** Every final mode applied to every one of the 100 conversations (800 present/absent judgments), saved to `analysis/state/labels/<mode>.jsonl` and to Langfuse as scores (1 = failure present).

## Final failure modes (8)

Sample fractions describe this reviewed sample only. Clustering and targeted search changed its composition, so these are **not prevalence estimates** (HW5 estimates prevalence).

| Mode | Present | Sample fraction | Spec | Likely evaluator |
|---|---|---|---|---|
| `falsely_reports_record_missing` | 15 | 15% | RESP-3, RESP-6 | Code check |
| `claims_not_grounded_in_tools` | 12 | 12% | RESP-1, RESP-3 | LLM judge |
| `doesnt_escalate_when_required` | 7 | 7% | ESC-1 to ESC-4 | Code check |
| `mishandles_damaged_data` | 6 | 6% | ESC-5, RESP-6 (new) | LLM judge |
| `stalls_instead_of_acting` | 6 | 6% | RESP-7 (new) | Code check |
| `omits_decisive_detail` | 6 | 6% | RESP-5 | LLM judge |
| `hides_partial_list` | 3 | 3% | Answer key; RESP-3 | Code check |
| `unnatural_or_verbose_language` | 3 | 3% | RESP-5 | LLM judge |

Full definitions, boundaries, positives and close negatives are in `analysis/state/patterns.json`.
Observed but not adopted (too rare): `dismisses_repeat_request` (0021), `ignores_user_constraint` (0168), `unstated_assumption` (0185).

## Stability: new modes in the final 15

**1 new consequential theme** appeared in Batch 4 (`dismisses_repeat_request`, support-0021). The other 8 Batch 4 failures fit existing modes (3 × falsely reports missing, 2 × damaged data, 1 each of partial list, stalls, escalation). I treated the taxonomy as stable and did not adopt the new theme, since it appeared once.

## One taxonomy revision

Early on, `incomplete_response` covered both "showed 8 of 20 orders as if that were all of them" (0023, 0027) and "didn't explain which return window wins" (0161). The fixes differ (say "showing N of M" vs. retrieve and compare both policies), so I **split** it into `hides_partial_list` and `omits_critical_detail`. Later, in the final review, I **moved the damaged-data cases** (0043, 0077, 0078) out of the escalation mode into a new `mishandles_damaged_data` mode, because one fix (a damaged-data playbook) addresses all of them, while plain escalation failures need a different fix.

## A rejected search suggestion

Search flagged support-0068 as `stalls_instead_of_acting` (refund request, no refund call, reply asks to confirm). I rejected it: the order was past its return window, so the agent *should not* refund. The real failure was saying the order didn't exist when it was in the results (`falsely_reports_record_missing`). Boundary: stalling applies only to a clear request on an **eligible** order.

## Specification revisions (from human annotations)

- **ESC-5** (damaged order records escalate) and **RESP-6** (state damaged data plainly with IDs; clarify catalog damage). Motivated by support-0037, 0043, 0077, 0078, 0080, 0194, 0196, 0205: the agent failed 6 of the 8 damaged-record conversations, and RESP-3 alone did not say to escalate or how to word it.
- **RESP-7** (follow user intent on write actions). Motivated by support-0088 (refunded when the customer only asked whether it was possible) and support-0058, 0060, 0062, 0063 (stalled on clear requests).

## Key findings

1. **One tool gap explains the largest mode.** `list_my_orders` returns order IDs and status but no product names, so the agent tells customers "you don't have that order" when it is row 1 (0100, 0104, 0110, …). HW1 fixed the same gap in `get_order` (product title and store name); `list_my_orders` and `find_order` still lack it. **Recommendation:** add product title and store name to both, plus a prompt rule: never say an order doesn't exist unless a name search returned nothing. A separate variant (the agent invents `store: "2"`, gets an error, then reports nothing found; 0176, 0209) needs tool-side validation instead.
2. **Damaged data gets poor user-facing answers.** Missing dates, impossible dates and duplicate product names were hidden, guessed around or called "not found" (now ESC-5 / RESP-6).
3. **Correct facts, missing grounding.** Many replies were right but uncited or added unsupported numbers (12 conversations).

## Comparison with the AgentDebug taxonomy

AgentDebug ([Where LLM Agents Fail and How They Can Learn From Failures](https://icml.cc/virtual/2026/77923)) sorts agent failures by the module that broke: **memory, reflection, planning, action, and system**.

- Most of my modes are **action** failures (wrong tool or inputs, a missing or unconfirmed write, uncited claims). `doesnt_escalate_when_required` is a **planning** failure (the wrong next step).
- **Possible omission: memory across turns,** meaning the agent should carry forward what the user already said instead of treating each message as new. support-0168 is a clear case: the user said "only the teapots" and the agent kept re-adding a vase. support-0021 is weaker; the agent remembered sending the list but misread why the user asked again. With one clear example, I did not add a mode, but I would watch for it in HW5's larger run.
- AgentDebug also looks for the **critical error**, the earliest step that caused the failure, which matches the first-failure rule I used during open coding.

## What I'd explore next

- **Persistent, opt-in memory.** The one memory failure (0168) points beyond memory within a conversation to memory across conversations: remembering a customer's preferences and pet peeves so they don't repeat them. It should be opt-in, with ways to view, edit and delete what is stored, and it would need its own evals (stale preferences, another customer's memory applied, over-personalization).
- **Live traces and per-step labels.** In a production system with many parts, the review UI should read live from the trace store and attach each label to every trace in a conversation, or to the exact step that failed.

## Part C

Not completed (optional); no `workshop_notes.md`.
