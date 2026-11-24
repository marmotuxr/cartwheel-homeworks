# Homework 7: monitoring falsely_reports_record_missing

Two periods of the same 50 monitoring scenarios on gpt-4o-mini (same prompt version), judged by my frozen Homework 5 judge `falsely_reports_record_missing-v1`. 1 = failure present. The random sample is 20% (10 conversations per period). The risk group is `multi_turn` (11 conversations per period). Threshold: 15%, chosen before looking at any results.

| Period | Random flagged | Raw | Corrected | 95% interval | Multi-turn flagged |
|---|---|---|---|---|---|
| before (HW3 run, Oct 24) | 1 of 10 | 10% | 8.9% | 0%–51% | 1 of 11 |
| after (new run, Nov 24) | 0 of 10 | 0% | 0% | 0%–0% | 0 of 11 |

Judge accuracy from the Homework 5 test split: failure sensitivity 0.67, pass specificity 0.96. Full numbers are in `history.jsonl`, and the chart is `prevalence.svg`.

## 1. Did the corrected failure estimate move between the two periods?

Barely. The corrected rate went from 8.9% before to 0% after, but that's one flagged conversation out of ten becoming zero out of ten. Nothing about the agent changed between the two runs (same model, same prompt version), so I don't read this as the agent getting better. Moving by one conversation is within normal run-to-run noise.

## 2. Do the intervals support a conclusion, or is the result uncertain?

No, the result is too uncertain to tell. With only 10 random conversations per period, the before range runs from 0% to 51%, which includes my 15% threshold, and the after estimate of 0 out of 10 is still consistent with a real rate of up to roughly 25–30% (the 0%–0% interval is a quirk of the bootstrap when nothing is flagged). The two ranges overlap, so I can't say one period was better. To conclude anything, I'd judge more conversations, 20 or 40 or all 50, keeping in mind that each one is a paid judge call and that the judge's own error rate adds uncertainty too.

## 3. What did the risk groups reveal that the random estimate did not?

The multi-turn risk group caught a flagged conversation, support-0076, that the random sample didn't include. The random sample is luck of the draw: sometimes it lands on a failure, sometimes it doesn't. The risk group checks every conversation in its category every time, but only that category. support-0108, a single-message conversation where the agent said it couldn't find an order that was in its own list, was in neither pile, so both missed it. Since my failure mode is about order lookups, a risk group that pulls every conversation where the agent looked up orders would likely catch more of these than multi-turn does.

## 4. What action should happen if the estimate crosses the threshold?

Go back to error analysis. First, open the flagged conversations from the dashboard's flagged-plates table and read them myself, because the judge misses about a third of real failures and sometimes flags good ones. Then confirm which flags are real failures and look for what they have in common. Each confirmed failure becomes a new evaluation case in my Homework 6 suite, so CI blocks the same mistake from coming back. Then fix the agent (for this mode, likely giving the order lookup product names) and let the monitor show whether the rate comes back down.
