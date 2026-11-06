# Interface comparison: my review app vs. the reference and standard Langfuse

My interface: `analysis/review_app/` (`server.py` + `index.html`), run with `.venv/bin/python -m analysis.review_app.server` → http://localhost:8021.
Observations of the standard Langfuse view that shaped it are in `langfuse_view_notes.md`.

## The principle: the reviewer is the user

Reviewing 100 traces is heavy work, so I treated the review tool as a product whose user is the reviewer. Two forces pulled against each other:
- **Make review easier.** Aids that reduce effort without suggesting a verdict.
- **Protect independent judgment.** Nothing that suggests the answer before I decide.

## One design retained from the reference interface

**Notes anchored to the evidence, with AI suggestions kept separate.** Like `analysis/ui/index.html`, I select text in a message to attach a note to it, and notes show as cards in a margin beside the message. AI or search suggestions never mix with my own notes: they appear in their own box (purple, labeled), and each one needs an explicit Accept or Reject, recorded in `suggestions.json`.

## Designs I changed after inspecting my traces

1. **One conversation per page, in order.** Langfuse shows one trace per user message, so multi-turn conversations were split ("I'm only seeing the first message out of potentially many"). The app groups traces by session and shows every message, tool call and reply in order, with timed-out first attempts tucked away and labeled as not graded.
2. **Tool results as tables, with the right row highlighted.** Raw JSON was "so packed that I can't even tell if the dates are chronologically from most recent to oldest". Results now render as tables (columns can be moved and hidden), and the order the customer means is highlighted with a label, e.g. "result (20 orders · #2053 is row 1)". This made the largest failure mode (the agent saying an order doesn't exist when it is row 1) visible at a glance.
3. **Answer key as a checklist.** I kept missing the last clause of the answer key (e.g. "make any displayed subset clear"). Each clause is now its own checkbox.
4. **Effort savers.** Built-in dictation in every text box (my voice-typing app was unreliable here), one-tap tags, keyboard shortcuts (P pass, F note, ⌘↵ save, ←/→), text zoom, light mode, a collapsible conversation list, compact theme cards (clearest example plus case chips, one note open at a time), and bolded failure clauses in the Table view.
5. **Things I deliberately left out.** I removed a "your past verdicts on similar conversations" check because it anchored me to earlier calls ("I want to view each one as an isolated incident"), and I did not add AI summaries before judging. Opinion-shaped aids come after the human decision, if at all.

## One limitation remaining

**The app reads the frozen HW3 trace export (`traces/support_traces.json`) rather than querying Langfuse live.** I used the export because it is exactly the 250-scenario dataset HW3 produced, and because my local Langfuse stack (Docker) was unavailable after machine restarts on several review days. Stable Langfuse trace IDs are preserved, and every label is written back to the live local Langfuse as a score. A second limitation: each conversation-level label is stored on the conversation's **first** trace, so a reviewer looking at a later turn in Langfuse will not see it. Both could be fixed by reading from the Langfuse API and writing the score to every trace in the session.

**What I'd build next:** an optional, clearly labeled plain-language summary shown only after the reviewer decides. Briefings were far easier on my eyes than the raw view, but shown first they would bias open coding.
