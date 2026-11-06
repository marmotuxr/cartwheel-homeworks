# Draft failure modes for Eve's review (lunch, 2026-11-04)

Drafted by Claude from Eve's 100 open codes and tags. Nothing is final until Eve accepts, edits or rejects each one.
"Present" = the failure happened. Each mode lists its spec rule, likely evaluator, and the evidence.

---

## 1. `falsely_reports_record_missing`
**Present when:** the agent tells the user an order or product doesn't exist, or that it "couldn't find" it, but a tool result in the conversation contains it, or the agent caused the empty result itself (wrong tool or an invented filter).
**Not present when:** every reasonable lookup genuinely returned nothing.
**Boundary vs. 4 (damaged data):** if the record exists but is broken, that is mode 4; mode 1 is denying a record that exists.
**Spec:** RESP-3 (don't invent a value, including "not found"), RESP-6.
**Evaluator:** code check (reply says not-found while the target order or product is in a tool result) plus LLM judge for wording.
**Positives (15):** 0068, 0077, 0080, 0095, 0100, 0103, 0104, 0107, 0109, 0110, 0114, 0115, 0183 (`list_my_orders` has no product names); 0176, 0209 (invented store filter "2").
**Close negatives:** 0117 (correctly said nothing is cancellable), 0003 and 0011 (found the order via `list_my_orders`).
**Merges Eve's tag:** `wrong_about_order_records`.

## 2. `doesnt_escalate_when_required`
**Present when:** the case must go to a human (refund over $100 when the tool queues it, account change, dispute, damaged order record, or unsure about policy) and the agent neither calls `escalate_to_human` nor says it will hand off.
**Not present when:** the agent escalates (ticket created) or the tool queued the refund and the agent explained it.
**Boundary vs. 5 (stalls):** stalling is not acting on a clear, allowed request; this mode is not handing off a case the agent must not resolve itself.
**Spec:** ESC-1 to ESC-5.
**Evaluator:** code check (required case and no `escalate_to_human` call) plus LLM judge for whether it promised a handoff.
**Positives (9):** 0043, 0077, 0078, 0220, 0222, 0228, 0231, 0233, 0235.
**Close negatives:** 0214, 0216 (escalated disputes correctly), 0049 (declined and asked for context).
**Merges:** `doesnt_escalate_when_required`, `didn't_escalate_bad_data`.

## 3. `claims_not_grounded_in_tools`
**Present when:** the reply states a policy, deadline, number, product attribute or availability that no tool result or retrieved policy supports, or attributes it to a policy that does not say it.
**Not present when:** every such claim traces to a tool result or a retrieved, cited policy.
**Boundary vs. 6 (omits detail):** this mode is saying something unsupported; mode 6 is leaving out something true and decisive.
**Spec:** RESP-1, RESP-3.
**Evaluator:** LLM judge (compare each claim with tool outputs and retrieved policies).
**Positives (9):** 0002, 0080, 0083, 0112, 0132, 0149 (policy); 0180, 0194, 0196 (product facts that don't exist).
**Close negatives:** 0159 (looked up and cited), 0175 (borderline: "available" = listed).
**Merges:** `claims_policy_without_checking`, `states_unverified_facts`.

## 4. `mishandles_damaged_data`
**Present when:** a tool result contains missing, contradictory or invalid data that matters to the request, and the reply hides it, guesses around it, reports the record as missing, or (for order records) doesn't escalate.
**Not present when:** the agent names the problem plainly, uses IDs, and escalates (orders) or clarifies (catalog).
**Boundary vs. 1:** see mode 1.
**Spec:** ESC-5, RESP-6 (new HW4 revisions).
**Evaluator:** LLM judge, run only on conversations whose tool results contain a known data defect.
**Positives (6):** 0043, 0077, 0078, 0080, 0194, 0196.
**Close negatives:** 0037 (reversed dates handled), 0205 (negative price flagged).
**New mode** from Eve's damaged-data finding.

## 5. `stalls_instead_of_acting`
**Present when:** the user clearly requests a refund or cancellation on a uniquely identified, eligible order, and the agent asks for confirmation, a reason, an amount, or other information instead of calling the tool.
**Not present when:** the user only asked whether it's possible (then confirming is correct), or the order is ambiguous or ineligible.
**Boundary vs. `acts_without_confirmation`:** that is the opposite error (acting when the user only asked a question); both follow RESP-7.
**Spec:** RESP-7 (new HW4 revision).
**Evaluator:** code check (request intent, eligible target, no write tool) plus LLM judge for "clear request".
**Positives (6):** 0058, 0059, 0062, 0063, 0087, 0177.
**Close negatives:** 0096, 0101 (cancelled immediately on a clear request), 0090 ($100 refund executed).

## 6. `omits_decisive_detail`
**Present when:** the reply is technically true but leaves out the fact that decides the user's next step: a deadline that is today, the store window that overrides the platform default, which policy wins, or why something is not eligible.
**Not present when:** the decisive fact is stated, or the user asked only for something narrower.
**Spec:** RESP-5 (explain the relevant decision).
**Evaluator:** LLM judge.
**Positives (5):** 0082, 0083, 0092, 0161, 0162.
**Close negatives:** 0090 (boundary refund explained), 0159 (gave exactly the asked timeframe).
**Renames:** `omits_critical_detail` (0194 and 0196 move to mode 4).

## 7. `hides_partial_list`
**Present when:** the agent shows only part of the records a tool returned, or of a capped search, as if it were the full set.
**Not present when:** it shows everything, or says "showing N of M" or "there may be more".
**Spec:** answer-key requirement "make any displayed subset clear"; RESP-3.
**Evaluator:** code check (items listed < tool count, and no subset wording).
**Positives (3):** 0023, 0027, 0180.
**Close negatives:** 0021 (listed all 20), 0166 (all 4 results shown).

## 8. `unnatural_or_verbose_language` (optional; Eve decides whether to keep)
**Present when:** the reply is far longer or more robotic than the user asked for, or exposes internal terms ("policy ID", "retrieval issue"), especially when the user asked for a short, plain answer.
**Spec:** RESP-5.
**Evaluator:** LLM judge.
**Positives (3):** 0131, 0149, 0165.
**Close negatives:** 0003, 0216 (short and plain as asked).

---

### Observed but not proposed as modes (too rare in the sample)
- `dismisses_repeat_request` (0021): the only new theme in the final 15; stability count = 1.
- `ignores_user_constraint` (0168), `unstated_assumption` (0185), `acts_without_confirmation` (0088, practice, outside the sample).
