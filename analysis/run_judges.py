"""Homework 5: judge inputs, labels, splits and judge runs.

Mode: falsely_reports_record_missing.

Sources of conversations:
- HW4 traces: the Langfuse export at traces/support_traces.json.
- HW5 targeted scenarios (hw5t-*): Langfuse was not running when they were run,
  so they come from the agent's own session store (.sessions.db). Each one is
  matched to its scenario by the customer's opening message.

Labels:
- HW4 labels live in analysis/state/labels/<mode>.jsonl with 1 = failure present.
- Eve's HW5 voice verdicts live in analysis/state/hw5_voice_verdicts_part*.txt.
- The HW5 export at analysis/state/hw5_labels/<mode>.jsonl uses 1 = Pass, 0 = Fail.

The judge input keeps only what the agent saw: customer messages, tool calls,
tool results and agent replies. No labels, notes, scenario metadata or
database facts.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODE = "falsely_reports_record_missing"
STATE = ROOT / "analysis" / "state"
HW4_TRACES = ROOT / "traces" / "support_traces.json"
SESSIONS_DB = ROOT / ".sessions.db"
TARGETED_SCENARIOS = ROOT / "scenarios" / "hw5_targeted_scenarios.jsonl"
VOICE_VERDICTS = sorted(STATE.glob("hw5_voice_verdicts_part*.txt"))
INPUTS_PATH = STATE / "hw5_trace_inputs.json"
HW5_LABELS_PATH = STATE / "hw5_labels" / f"{MODE}.jsonl"


# ---------------------------------------------------------------------------
# messages
# ---------------------------------------------------------------------------

def _tool_call(name: str, arguments) -> dict:
    args = arguments if isinstance(arguments, str) else json.dumps(arguments, sort_keys=True)
    return {"role": "tool_call", "name": name, "arguments": f"{name}({args})"}


def _tool_result(name: str, output) -> dict:
    out = output if isinstance(output, str) else json.dumps(output, sort_keys=True)
    return {"role": "tool_result", "name": name, "content": f"{name} returned: {out}"}


def _hw4_messages(trace: dict) -> list[dict]:
    """Messages for one Langfuse trace (one turn), with tool names kept in the text."""
    from analysis.helpers.normalization import normalize_trace

    out = []
    for m in normalize_trace(trace)["trace"]:
        role = m.get("role")
        if role == "tool_call":
            out.append(_tool_call(m.get("name", "tool"), m.get("arguments")))
        elif role == "tool_result":
            out.append(_tool_result(m.get("name", "tool"), m.get("content")))
        elif role in ("user", "assistant"):
            out.append({"role": role, "text": m.get("text", "")})
    return out


def _session_messages(rows: list[dict]) -> list[dict]:
    """Messages for one session stored by the agent SDK in .sessions.db."""
    names: dict[str, str] = {}
    out = []
    for item in rows:
        kind = item.get("type")
        if item.get("role") == "user":
            content = item.get("content")
            text = content if isinstance(content, str) else " ".join(
                p.get("text", "") for p in content if isinstance(p, dict))
            out.append({"role": "user", "text": text})
        elif kind == "message" and item.get("role") == "assistant":
            text = "".join(p.get("text", "") for p in item.get("content", []) if isinstance(p, dict))
            if text.strip():
                out.append({"role": "assistant", "text": text})
        elif kind == "function_call":
            names[item["call_id"]] = item["name"]
            out.append(_tool_call(item["name"], item.get("arguments", "{}")))
        elif kind == "function_call_output":
            out.append(_tool_result(names.get(item["call_id"], "tool"), item.get("output")))
    return out


# ---------------------------------------------------------------------------
# conversations
# ---------------------------------------------------------------------------

def _hw4_label_rows() -> list[dict]:
    """Live HW4 label per trace (1 = failure present), last write wins."""
    live: dict[str, dict] = {}
    for line in (STATE / "labels" / f"{MODE}.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            if not row.get("superseded_by"):
                live[row["trace_id"]] = row
    return list(live.values())


def _voice_verdicts() -> dict[str, tuple[str, str]]:
    verdicts = {}
    for path in VOICE_VERDICTS:
        for line in path.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            sid, verdict, reason = (part.strip() for part in line.split("|", 2))
            verdicts[sid] = (verdict, reason)
    return verdicts


def _targeted_sessions() -> dict[str, tuple[str, list[dict]]]:
    """scenario_id -> (session_id, raw messages) for the hw5t-* runs (latest run wins)."""
    openers = {}
    for line in TARGETED_SCENARIOS.read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            openers[rec["opening_message"].strip()] = rec["id"]
    db = sqlite3.connect(f"file:{SESSIONS_DB}?mode=ro", uri=True)
    rows = db.execute(
        "SELECT m.session_id, m.message_data FROM agent_messages m "
        "JOIN agent_sessions s USING (session_id) ORDER BY s.created_at, m.id"
    ).fetchall()
    by_session: dict[str, list[dict]] = {}
    for session_id, data in rows:
        by_session.setdefault(session_id, []).append(json.loads(data))
    found = {}
    for session_id, msgs in by_session.items():
        first = msgs[0]
        if first.get("role") != "user":
            continue
        content = first.get("content")
        text = content if isinstance(content, str) else " ".join(
            p.get("text", "") for p in content if isinstance(p, dict))
        sid = openers.get(text.strip())
        if sid:
            found[sid] = (session_id, msgs)
    return found


def _conversations() -> list[dict]:
    """One record per labeled conversation: ids, label (1 = Pass), evidence, messages."""
    traces = json.loads(HW4_TRACES.read_text())["traces"]
    by_id = {t["id"]: t for t in traces}
    by_scenario: dict[str, list[dict]] = {}
    for t in traces:
        by_scenario.setdefault(t.get("cartwheel_scenario_id"), []).append(t)
    verdicts = _voice_verdicts()
    convs = []

    # HW4 labels (Group 1 and earlier review).
    for row in _hw4_label_rows():
        ids = row.get("trace_ids") or [row["trace_id"]]
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise ValueError(f"{row['scenario_id']}: traces not in export: {missing}")
        turns = sorted((by_id[i] for i in ids), key=lambda t: t["timestamp"])
        convs.append({
            "trace_id": row["trace_id"], "scenario_id": row["scenario_id"],
            "label": 1 - int(row["label"]), "evidence": "HW4 label",
            "source": "hw4", "trace": [m for t in turns for m in _hw4_messages(t)],
        })

    seen = {c["scenario_id"] for c in convs}
    targeted = _targeted_sessions()
    for sid, (verdict, reason) in verdicts.items():
        if verdict not in ("PRESENT", "ABSENT"):
            raise ValueError(f"{sid}: verdict {verdict!r} still needs a decision")
        if sid in seen:
            raise ValueError(f"{sid} already has an HW4 label")
        label = 0 if verdict == "PRESENT" else 1
        evidence = reason or "voice label, no reason given"
        if sid.startswith("hw5t-"):
            session_id, msgs = targeted[sid]
            convs.append({"trace_id": session_id, "scenario_id": sid, "label": label,
                          "evidence": evidence, "source": "hw5_voice",
                          "trace": _session_messages(msgs)})
        else:
            turns = sorted(by_scenario[sid], key=lambda t: t["timestamp"])
            convs.append({"trace_id": turns[0]["id"], "scenario_id": sid, "label": label,
                          "evidence": evidence, "source": "hw5_voice",
                          "trace": [m for t in turns for m in _hw4_messages(t)]})
    return convs


# ---------------------------------------------------------------------------
# Part A / B outputs
# ---------------------------------------------------------------------------

def export_hw5_labels() -> Path:
    """Write analysis/state/hw5_labels/<mode>.jsonl with 1 = Pass, 0 = Fail."""
    HW5_LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({k: c[k] for k in ("trace_id", "scenario_id", "label", "evidence", "source")}
                        | {"label_convention": "1=Pass,0=Fail"})
             for c in _conversations()]
    HW5_LABELS_PATH.write_text("\n".join(lines) + "\n")
    return HW5_LABELS_PATH


def prepare_inputs() -> Path:
    """Write analysis/state/hw5_trace_inputs.json: trace_id + messages only."""
    records = [{"trace_id": c["trace_id"], "trace": c["trace"]} for c in _conversations()]
    INPUTS_PATH.write_text(json.dumps(records, indent=1, ensure_ascii=False))
    return INPUTS_PATH


def split_data(mode: str = MODE) -> dict:
    """20/40/40 split, seed 7. Run once, after labels are final."""
    from analysis.helpers import split_labels

    records = json.loads(INPUTS_PATH.read_text())
    return split_labels(
        mode,
        fractions=(0.20, 0.40, 0.40),
        seed=7,
        min_per_class=10,
        eligible_trace_ids=[r["trace_id"] for r in records],
    )


# ---------------------------------------------------------------------------
# Part C: development runs
# ---------------------------------------------------------------------------

JUDGE_MODEL = "gpt-4o-mini"
REPORT_DIR = ROOT / "analysis" / "report"


def _use_hw5_inputs() -> None:
    import os
    os.environ.setdefault("CARTWHEEL_JUDGE_TRACE_SOURCE", str(INPUTS_PATH))


def run_development(mode: str, prompt_path: str | Path) -> dict:
    """Register one prompt version, run it on dev, save metrics to the report folder."""
    from analysis.helpers import judge_alignment, register_judge, run_judge

    _use_hw5_inputs()
    record = register_judge(mode=mode, prompt_text=Path(prompt_path).read_text(),
                            judge_model=JUDGE_MODEL)
    judge_id = record["judge_id"]
    run_judge(judge_id, split="dev", batch_size=10)
    development = judge_alignment(judge_id, split="dev")
    out = {"judge_id": judge_id, "prompt_path": str(prompt_path),
           "prompt_hash": record["prompt_hash"], "model": JUDGE_MODEL, "dev": development}
    (REPORT_DIR / f"dev-{judge_id}.json").write_text(json.dumps(out, indent=2, default=str))
    return out


# ---------------------------------------------------------------------------
# Part D: freeze and test
# ---------------------------------------------------------------------------

def run_test(judge_id: str) -> dict:
    """Freeze the chosen judge, run it once on test, save metrics. Call freeze only once."""
    from analysis.helpers import freeze_judge, judge_alignment, run_judge

    _use_hw5_inputs()
    freeze_judge(judge_id)
    run_judge(judge_id, split="test", batch_size=10)
    test = judge_alignment(judge_id, split="test")
    out = {"judge_id": judge_id, "model": JUDGE_MODEL, "test": test}
    (REPORT_DIR / f"test-{judge_id}.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    print(export_hw5_labels())
    print(prepare_inputs())
