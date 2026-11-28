# Results before the grader fix (not used)

These runs scored the frozen Homework 5 judge with two starter bugs in `replay/`:

1. The verdict parser looked only for `"answer": "pass|fail"`, but the HW5 judge
   returns `"result": "Pass|Fail"`. With no match it fell back to "fail" whenever
   the word "fail" appeared anywhere in the critique, so a critique saying
   "this failure mode is absent" was scored as a failure (e.g., e-008).
2. The judge saw only the agent's final reply, not the tool calls and results,
   although this judge was validated in Homework 5 on full traces and the HW6
   Harbor rubric sends the full trace (`judge_trace_text`).

Both were fixed in `replay/` before any search-budget or test-set run. The
starting version was re-recorded on the fixed commit, and Part C was redone.
The split and search budget were not changed (no `--search` run had happened).
