# Standard Langfuse view: reviewer observations (Part A)

Reviewed 2026-10-31 in local Langfuse (project `cartwheel-dev`), before designing the review interface.
Observations are the learner's own, lightly edited.

| # | Scenario | Trace | Shape |
|---|---|---|---|
| 1 | support-0016 | d56aa3781ab630ed09d68f0cfd348088 | merchant, 1 message, `list_my_orders` |
| 2 | support-0002 | e7e37c104d04bf9f782464f21c9d97dd | shopper, 2 messages, `list_my_orders` |
| 3 | support-0031 | 6a2f0950ce24e816f0f58b5760328a02 | support staff, 3 messages, no tools |
| 4 | support-0064 | a2f2b6e2e7932939b731ff3ac4f2205d | shopper refund, 4 messages, several tools (this trace is the timed-out first attempt) |

## What slowed review

1. **Multi-turn conversations are split.** "I'm only seeing the first message out of potentially many… if it's three messages, I only saw one. I don't know where the other two are." Each user message is its own trace, so followups appear in isolation.
2. **Too much clicking to answer one question.** "I go into the session message, look at the metadata, then the support agent details and the metadata, and then the tool call to see the tool call." The tool result is several clicks away from the reply that relies on it.
3. **Clutter.** "The view is just a little cluttered… the answer is freaking long." Internal spans (`Agent Workflow`, `cartwheel-support.agent`, two `openai.response` generations) sit at the same level as the conversation and tools.
4. **Errors are unexplained.** "I'm seeing error… I want to know what the error is. That part is not very clear." Trace 4 is a provider timeout from a first attempt that was later retried; the view gives no sign that it is a failed attempt rather than an agent failure.
5. **No expected behavior on screen** (added during discussion). Judging a trace needs the scenario's answer key, which lives in `scenarios/support_scenarios.jsonl`, not in Langfuse.

## Design consequences

- Group traces by `cartwheel.session_id` and show every turn in order on one page.
- Show tool calls and results inline, between the user message and the agent reply.
- Hide internal spans; collapse long tool results.
- Separate failed or timed-out attempts from the conversation that was graded, and label them.
- Show the scenario's expected behavior and source beside the conversation.

## Changes made after using the first version (2026-10-31)

- **Tool results as tables.** The first build showed each result as raw JSON wrapped onto a few dense lines. Reviewer: "so packed that I can't even tell if the dates are chronologically from most recent to oldest." Lists of records (orders, products) now render as a table, one row per record in the order the tool returned them, with dates in life-cycle order (ordered → shipped → delivered → status). Scalar fields sit above the table, and the raw JSON is one click away.
