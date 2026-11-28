# Homework 8: fixing falsely_reports_record_missing, then comparing configurations

**Target:** `falsely_reports_record_missing`. The agent tells a shopper an order does not exist when the order is right there. It was the most common failure in my Homework 4 review (15 of 100 reviewed traces), and support-0108 is the example I've followed since then. See `results/target.json`.

**Models** (all OpenAI, prices checked 2026-11-28):
- **Development and search:** gpt-4o-mini, the same model as Homeworks 3–7.
- **Comparison:** gpt-5.5, gpt-5.4-mini, and gpt-4o-mini.

**Split:** 9 development cases and 4 sealed test cases. All 4 test cases are record-missing cases, so the test set measures the target directly.

## A grader bug, found and fixed before any search or test run

The first runs made no sense. e-008 failed although both the reply and the judge's own critique said it passed. The cause was two bugs in the starter `replay/` scorer:

1. **The verdict was misread.** The scorer looked for `"answer": "pass"`, but my HW5 judge writes `"result": "Pass"`. With no match, it scored any critique containing the word "fail" as a failure. "This failure mode is absent" counted as a fail.
2. **The judge saw only the final reply.** This judge was validated in HW5 on whole conversations, including tool calls and results, and HW6's Harbor rubric sends the whole conversation (`judge_trace_text`). Without the tool results, it can't tell a real "not found" from a false one.

I fixed both in `replay/` (commit a4465f7), archived the earlier runs in `results/pre-grader-fix/`, and re-recorded the starting version on the fixed commit. The split and the search budget were never changed. No search-budget run or test run had happened yet, and the frozen judge itself was not edited.

## Part C: one manual change per layer (`results/manual.csv`)

| Change | Layer | Dev score | Decision | What happened |
|---|---|---|---|---|
| Starting agent | – | 0.33 | – | e-004 and e-006 falsely say "you don't have that order" |
| "Search by name before saying an order is missing" | prompt | 0.33 | revert | The model ignored the rule; neither target case improved |
| `list_my_orders` returns product title and store name | tool | 0.33 / 0.33 / 0.44 (3 runs) | **keep** | Fixed e-006 some of the time: the agent can now see the item in its list |
| Note when the order list is cut off at 20 | harness | 0.33 / 0.33 / 0.44 (3 runs) | revert | No better than the tool change alone |

**Lesson:** the prompt layer was the weakest fix here. The cook can't follow "check the product name" when the equipment never shows product names.

## Part D: improve loop (`results/improve-loop.jsonl`, 90 of 150 runs used)

I reran every promising change a second time before keeping it, because one case flipping is often noise with 9 cases.

| Try | Layer | Dev score (run 1 / rerun) | Decision |
|---|---|---|---|
| Clearer descriptions for `list_my_orders` and `find_order` | tool | 0.33 | revert |
| **Add product names to `find_order` results in the tool-call wrapper** | harness | 0.44 / 0.44 | **keep** |
| Escalate account changes and charge disputes immediately | prompt | 0.67 / 0.56 | keep |
| `escalate_to_human` description: call it without asking first | tool | 0.67 / 0.67 | keep |
| Contact-detail changes are escalated, not refused | prompt | 0.89 / 0.67 | keep |

**The fix for the target:** e-004's order is the shopper's *oldest* (order #1), so it isn't in the 20-order list. `find_order` does search all orders, but returned rows with no product names. So the agent saw order numbers it couldn't match and said "none of these match." `find_order`'s exact output is fixed by the Homework 1 tests, so I added the names in the harness (the wrapper around every tool call) instead. After that, e-004 passed on every run.

I stopped at 90 runs. The remaining failures were e-006, where the judge flags "your item is not eligible for a refund" (read from the order data) as a missing-record claim, which looks like a judge false positive, plus run-to-run noise on e-013 and e-016.

## Part E: final configuration

The final configuration combines every kept change: the product names in the tool and in the harness, plus the two escalation prompt rules and the escalation tool description. On the development cases it scored **0.67**, against 0.33 at the start. I chose it because it fixes the target case consistently and keeps the escalation gains. It was saved in `state/final_version.json` before the test set was opened.

## Part F: the sealed test set (`results/frontier.csv`, `results/frontier.svg`)

| Config | Agent | Model | Test score | Cost / 100 conversations | Status |
|---|---|---|---|---|---|
| 1 | starting | gpt-5.5 | 1.00 | $3.30 | dominated |
| 2 | starting | gpt-5.4-mini | 1.00 | $0.45 | dominated |
| 3 | starting | gpt-4o-mini | 0.25 | $0.044 | dominated |
| 4 | **final** | gpt-4o-mini | **1.00** | **$0.036** | **frontier** |

- **Configs 1–3 show the effect of changing the model.** A bigger model fixes the failure on its own, at 10 to 90 times the cost.
- **Configs 3 and 4 show the effect of my changes,** on the same model: 1 of 4 → 4 of 4.
- **The final agent dominates every other configuration:** the same score as gpt-5.5, at about 1% of its cost.

**Caveat:** the test set has only 4 cases, so one case moves the score by 25 points. The frontier is a strong hint, not proof.

## Regenerate one number

Config 4's test score is the number of passing runs divided by the number of runs:

```bash
python3 -c "import json;d=json.load(open('optimize/results/test-configuration-4.json'));print(sum(c['passes'] for c in d['cases']), '/', sum(c['runs'] for c in d['cases']), '=', d['score'])"
```
