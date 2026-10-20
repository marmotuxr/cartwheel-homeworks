# Homework 2 — review and recording guide

## What this homework demonstrates

The server establishes a user's identity, runs the Cartwheel agent, and records its model calls and tool activity. A trace links the request and reply to the authenticated caller and the system-prompt version used.

The target is one continuous screen recording, no longer than five minutes. Use this as an outline and explain the evidence in your own words.

## Prepare the screen

- Open the Cartwheel project in VS Code and its terminal. Close the `.env` tab before recording.
- Open the two selected local traces below, and the two prompt-comparison traces, in browser tabs.
- Local chat: http://127.0.0.1:8012/
- Local Langfuse: http://localhost:3000/project/cartwheel-dev/traces?dateRange=7d
- These local traces are separate reruns of the scenarios reviewed in Cloud. Inspect their exact replies during rehearsal; wording can differ. The selected JSON records point to these local runs.

## A 4-minute-40-second route

### 0:00–0:20 — purpose and identity

Explain that the agent supports shoppers, merchants, and support staff. The server loads the user's stored identity and checks the claimed role before issuing a signed session token. The tools receive that server-established context. A user typing “I am support” does not change it.

### 0:20–0:45 — run one authentication test

In the project terminal:

```sh
cd /Users/ejkim17/cartwheel-homeworks
.venv/bin/python -m pytest tests/test_observability.py -k token_cannot_authorize_another_session -q
```

Explain the test's claim: a token issued for session A cannot authorize session B. It uses temporary data and does not call a model or Langfuse. It does not prove all production authentication is secure; this is the course's development authentication.

### 0:45–1:50 — merchant denied

[Open selected merchant trace](http://localhost:3000/project/cartwheel-dev/traces/115b435c8bfc787585e4e5a2df30ba08)

Request: “Show me order #4127.”

1. Root `cartwheel.session_message`: user 9002, merchant, original prompt hash.
2. First `openai.response`: the model requests `get_order` for order 4127.
3. `get_order`: caller is merchant 9002, Store 2; the output reports permission denied. Inspect the recorded denial reason. It does not return the protected order details.
4. Final `openai.response`: read how the model explains the denial.

The tool enforces the boundary; the model communicates the result. `final_status: completed` means the request finished normally, even though the requested access was correctly denied.

### 1:50–2:55 — support allowed

[Open selected support trace](http://localhost:3000/project/cartwheel-dev/traces/a0fd48ce0444ad9e36d88f39edebcf75)

Request: “What is the status of order #4127?”

1. Root: user 9501, support, original prompt hash.
2. First model call requests `get_order`.
3. Tool input identifies order 4127. Output is successful and reports delivered status; permission denied is false.
4. Final model call receives the tool result and produces the reply. Compare the reply with the returned data.

This contrasts allowed and denied access to the same order using different authenticated roles. It demonstrates these examples, rather than proving every permission scenario works.

### 2:55–3:55 — show prompt version tracking

Both runs used support user 9501, `gpt-4o-mini`, the same read-only order question, fresh sessions, and the same database state.

| Version | Tone instruction | Recorded hash | Trace |
|---|---|---|---|
| Original | Plain and warm. No legalese. | `457cf684927e` | [Original](http://localhost:3000/project/cartwheel-dev/traces/e88c9bb700fead1df6e49bd05c019ada) |
| Temporary change | Use plain, warm language. Avoid legalese. | `23510cb71fe4` | [Changed](http://localhost:3000/project/cartwheel-dev/traces/0d8254a90ad8f2b4f81759ca6448a407) |

Show `cartwheel.prompt_version` on each root span. Explain that the fingerprint hashes the system-prompt template, not the user's question. The original prompt has been restored.

Your assessment: the second reply was easier to scan. The verified experiment result is that the two versions were recorded distinctly. One run per version does not establish that the changed prompt is consistently better or that the wording change caused the formatting difference.

### 3:55–4:30 — regenerate the span count

```sh
.venv/bin/python scripts/hw2_span_count.py --local 115b435c8bfc787585e4e5a2df30ba08
```

Expected: **6 spans**:

1. `cartwheel.session_message`
2. `Agent Workflow`
3. `cartwheel-support.agent`
4. `openai.response`
5. `get_order`
6. `openai.response`

The trace heading in the UI is a container for the trace; do not count it as an additional span. Workflow/agent spans group operations and are not extra model calls. The helper reads the saved trace from Langfuse without making a new model call.

### 4:30–4:40 — show the saved record

Open `hw2-traces.json` in the repository. It contains exactly the two selected trace records with their links, prompt versions, caller identities, ordered tool names, and completion status.

## Five required request scenarios

All five were executed through the endpoint and verified in local Langfuse. Additional browser practice runs do not erase the saved runs.

| Scenario | Authenticated caller | Recorded tool sequence |
|---|---|---|
| Order 4127 outside merchant's store | Merchant 9002 / Store 2 | `get_order`; denied |
| Order 4127 status | Support 9501 | `get_order`; allowed |
| Jacket description conflicts with order 4127's vase | Shopper 1 | `get_order`; allowed, reply asks for clarification |
| Recent orders for own store | Merchant 9002 / Store 2 | `list_my_orders`; returned Store 2 records |
| Basketball question | Support 9501 | No tool calls; out-of-scope refusal |

You reviewed the fifth request on October 19: a refusal, one model call, no tool spans. `unknown_service` labels the tracing service; it does not mean a lookup found no match.

## Submission checklist

- [ ] Review the exact two selected local traces before recording.
- [ ] Rehearse once using the outline; aim below five minutes.
- [ ] Record one continuous screen video in your own words.
- [ ] Verify playback, readable evidence, audio, and duration.
- [ ] Confirm the required files are present: `observability/instrument.py`, `server/app.py`, `tests/test_observability.py`, and root `hw2-traces.json`.
- [ ] Decide when to commit and submit. No commit or upload is authorized merely by preparing this guide.

Implementation, five-request local tracing verification, controlled prompt comparison, and offline testing have been completed. The student reports the recording is complete; its duration, playback, share link, and final submission remain to be verified. The latest complete offline suite passed 170 tests, with 4 skips, 18 expected failures for later work, and 9 expected-failure tests now passing.
