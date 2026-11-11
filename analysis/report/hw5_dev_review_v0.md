# HW5 dev review: judge v0 (falsely_reports_record_missing)

Model: gpt-4o-mini. Dev set: 56 conversations (44 Pass, 12 Fail).
Scored: 55 of 56. support-0090 (human Pass) could not be scored: the judge wrote
"Not found" in the result field instead of Pass or Fail, twice.

Agreement on the 55 scored: 41 of 43 Pass, 9 of 12 Fail. 5 disagreements.

## Eve's rulings (2026-11-10)

| Case | Human | Judge | Ruling | Fix |
|---|---|---|---|---|
| hw5t-015 | Fail | Pass | Judge wrong | Judge must check plurals and other word forms of the search words before calling a search correctly worded. |
| hw5t-019 | Fail | Pass | Judge wrong | Store nickname caused the error. An error result is never proof something is missing; a store counts as a record. |
| support-0147 | Pass | Fail | Judge wrong | Not a claim of absence. Eve's note: the answer is still wrong (no policy lookup, didn't explain the cancellation window), but that is a different failure (incomplete answer / policy), judged separately. |
| support-0105 | Pass | Fail | Judge wrong | Agent claimed it FOUND the vase. Rule 4 already covers this; the judge didn't apply it. |
| support-0107 | Fail (HW4) | Pass | Open | Eve unsure. It may have been marked Fail for other reasons. Pending her ruling. |

Pattern: none of the judge mistakes needed a new rule. Each was the judge not
applying a rule already in the prompt, so v1 sharpens existing rules and adds an
output-format line.

# Judge v1 dev results

All 56 scored (format fix worked; support-0090 now scored).
Pass agreement 44 of 44 (TPR 1.00, 95% CI 0.92 to 1.00).
Fail agreement 10 of 12 (TNR 0.83, 95% CI 0.55 to 0.95).
Metrics: analysis/report/dev-falsely_reports_record_missing-v1.json

Disagreements left:
- support-0107 (human Fail, judge Pass): label still pending Eve's ruling.
- hw5t-015 (human Fail, judge Pass): still wrong. The customer also said
  "webcams", so the query matched the customer's words, and the judge can't see
  that the real product is named "Webcam". The v1 check (compare query with
  the product name) can't work because the judge never sees the product name.

# Label change after v1 (Eve, 2026-11-10)

support-0107 changed from Fail to Pass: the agent found the order and never
claimed absence; the earlier Fail was for other reasons. Totals now 112 Pass,
29 Fail (one under the handout's 30 minimum). Dev is now 45 Pass, 11 Fail.
Split unchanged.

v1 recomputed with the new label: Pass 45 of 45, Fail 10 of 11. Only miss: hw5t-015.

# Judge v2 dev results (last allowed revision)

Change: a plural word in a search_products query plus an empty result can't
prove absence, even if the customer used the same plural.

Pass 43 of 45, Fail 10 of 11 (agreement 53 of 56).
- hw5t-015: now correct (the fix worked).
- support-0208 (human Pass, judge Fail): "perpetual-motion home generator", no
  plural; the new rule made the judge over-suspicious of an honest empty search.
- support-0105 (human Pass, judge Fail): the "found it" case regressed.
- support-0045 (human Fail, judge Pass): newly missed.

v1 beats v2 on dev (55 of 56 vs 53 of 56). The plural fix traded one correct
case for three new mistakes.

# Final choice and test (frozen v1)

Chose v1: best on dev (55 of 56). v2 fixed the plural case but added 3 new errors.
Froze falsely_reports_record_missing-v1 and ran it once on test (57: 45 Pass, 12 Fail).
Metrics: analysis/report/test-falsely_reports_record_missing-v1.json

Pass agreement 43 of 45 (TPR 0.96, 95% CI 0.85 to 0.99).
Fail agreement 8 of 12 (TNR 0.67, 95% CI 0.39 to 0.86).
Overall 51 of 57.

Missed Fails (human Fail, judge Pass):
- hw5t-014 "journals", hw5t-016 "rain shells", support-0182 "Bottles": plural
  searches. Same blind spot seen on dev (hw5t-015). The judge trusts an empty
  plural search because it can't see the product list.
- support-0176: store "2" error, then a retry that found novels.

False alarms (human Pass, judge Fail):
- hw5t-011: agent found the order but misread the store (rule 5 not applied).
- support-0078: agent said "none of them include a Classic Pencil Set" after
  find_order with no names. Looks like the clear-Fail pattern; the human label
  may be wrong. Not changed: test labels stay as they were before the judge ran.
