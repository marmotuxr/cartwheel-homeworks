"""Monitor one period (or the last N hours) with the frozen Homework 5 judge.

Usage:
    uv run python -m monitoring.run --period before --dry-run
    uv run python -m monitoring.run --period after
    uv run python -m monitoring.run --last-hours 24

Steps: read the config, fetch the period's traces from Langfuse, validate the
scenario IDs and Cartwheel model, build one conversation record per scenario
(or per session for --last-hours), sample, show the judge call count, judge
the union once, correct the random-sample rate, write scores to Langfuse, and
save history and the chart.

Verdicts use 1 = failure present, 0 = absent. Only the random sample feeds
the failure-rate estimate; risk groups are for inspection.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MONITORING = ROOT / "monitoring"
CONFIG_PATH = MONITORING / "config.json"
HISTORY_PATH = MONITORING / "history.jsonl"
CHART_PATH = MONITORING / "prevalence.svg"
OUTPUT_DIR = MONITORING / "output"
SCENARIOS_PATH = ROOT / "scenarios" / "monitoring_scenarios.jsonl"


def _load_env() -> None:
    """Load .env without overriding variables already set in the shell."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Z0-9_]+)\s*=\s*(.*)$", line)
        if match:
            os.environ.setdefault(match.group(1), match.group(2).strip().strip("'\""))


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_window(start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Return full Langfuse traces (as dicts) whose timestamp is in [start, end]."""
    from langfuse import get_client

    from analysis.helpers.normalization import _data

    client = get_client()
    summaries: list[Any] = []
    page = 1
    while True:
        response = client.api.trace.list(
            from_timestamp=start, to_timestamp=end, page=page, limit=100
        )
        summaries.extend(response.data or [])
        total_pages = getattr(response.meta, "total_pages", None) or 1
        if page >= total_pages:
            break
        page += 1
    traces = []
    for summary in summaries:
        full = client.api.trace.get(summary.id)
        traces.append(_data(full))
    return traces


def _conversation(group: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """Merge one conversation's traces into the Homework 5 judge input shape."""
    from analysis.helpers.normalization import _flatten, normalize_trace
    from analysis.run_judges import _hw4_messages

    group = sorted(group, key=lambda trace: trace.get("timestamp") or "")
    messages: list[dict[str, Any]] = []
    models: list[str] = []
    for trace in group:
        messages.extend(_hw4_messages(trace))
        models.extend(normalize_trace(trace)["models"])
    tools = sorted({m["name"] for m in messages if m["role"] == "tool_call"})
    return {
        "id": str(group[-1]["id"]),  # final trace id receives the scores
        "key": key,
        "trace_ids": [str(trace["id"]) for trace in group],
        "text": _flatten(messages),  # same text format the judge saw in HW5
        "tools": tools,
        "turn_count": sum(m["role"] == "user" for m in messages),
        "models": sorted(set(models)),
    }


def build_records(
    traces: list[dict[str, Any]],
    model: str,
    scenario_ids: set[str] | None,
) -> tuple[list[dict[str, Any]], int]:
    """Group traces into conversations and validate them.

    With scenario_ids (a period), group by scenario and require exactly those
    scenarios, each from one session (no combined retries). Without it (the
    scheduled window), group by session id.
    Returns (records, number of eligible Langfuse traces).
    """
    from analysis.helpers.normalization import normalize_trace

    groups: dict[str, list[dict[str, Any]]] = {}
    sessions: dict[str, set[str]] = {}
    for trace in traces:
        meta = normalize_trace(trace)["meta"]
        if scenario_ids is not None:
            key = meta.get("scenario_id")
            if key not in scenario_ids:
                continue
        else:
            key = meta.get("session_id") or trace.get("sessionId")
            if not key:
                continue
        groups.setdefault(key, []).append(trace)
        sessions.setdefault(key, set()).add(
            str(meta.get("session_id") or trace.get("sessionId"))
        )

    if scenario_ids is not None:
        missing = sorted(scenario_ids - set(groups))
        if missing:
            raise SystemExit(f"period rejected: {len(missing)} scenario IDs missing, e.g. {missing[:5]}")
        retried = sorted(key for key, ids in sessions.items() if len(ids) > 1)
        if retried:
            raise SystemExit(f"period rejected: separate retries combined for {retried[:5]}")

    records = [_conversation(group, key) for key, group in sorted(groups.items())]
    wrong = [
        r["key"] for r in records
        if not r["models"] or any(not m.startswith(model) for m in r["models"])
    ]
    if wrong:
        raise SystemExit(f"period rejected: traces not from {model} in {wrong[:5]}")
    eligible = sum(len(r["trace_ids"]) for r in records)
    return records, eligible


def _batch_trace(mode: str, label: str, summary: dict[str, Any], estimate: dict[str, Any]) -> str:
    """Create (or update) one stable trace that holds the period's prevalence score."""
    from langfuse import get_client

    client = get_client()
    trace_id = client.create_trace_id(seed=f"monitor|{mode}|{label}")
    with client.start_as_current_span(
        name="monitor_run", trace_context={"trace_id": trace_id}
    ) as span:
        span.update_trace(
            name=f"monitor_run {label}",
            tags=["monitor_run"],
            metadata={"period": label, "judge_id": summary["judge_id"], "model": summary["model"]},
            output={k: estimate[k] for k in ("raw", "corrected", "ci_low", "ci_high", "n_sample")},
        )
    client.flush()
    return trace_id


def _upsert_history(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    if HISTORY_PATH.exists():
        rows = [json.loads(line) for line in HISTORY_PATH.read_text().splitlines() if line.strip()]
    rows = [row for row in rows if row["label"] != entry["label"]] + [entry]
    order = {label: i for i, label in enumerate(["before", "after"])}
    rows.sort(key=lambda row: (order.get(row["label"], 99), row["label"]))
    HISTORY_PATH.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--period", help="period label from monitoring/config.json")
    which.add_argument("--last-hours", type=float, help="monitor the previous N hours")
    parser.add_argument("--dry-run", action="store_true", help="show counts, call no judge")
    args = parser.parse_args(argv)

    _load_env()
    from analysis.helpers import langfuse_io
    from monitoring.correct import corrected_mode_prevalence
    from monitoring.run_judges import judge_sample, judge_test_data
    from monitoring.sample import DEFAULT_RISK_GROUPS, select_traces
    from monitoring.write_scores import build_score_records, post_scores

    if not langfuse_io.is_configured():
        raise SystemExit("set LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_HOST")

    config = json.loads(CONFIG_PATH.read_text())
    mode, judge_id, model = config["judge_mode"], config["judge_id"], config["model"]

    if args.period:
        period = next((p for p in config["periods"] if p["label"] == args.period), None)
        if period is None:
            raise SystemExit(f"no period {args.period!r} in {CONFIG_PATH}")
        label, start, end = period["label"], _parse_time(period["from"]), _parse_time(period["to"])
        scenario_ids = {json.loads(l)["id"] for l in SCENARIOS_PATH.read_text().splitlines() if l.strip()}
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=args.last_hours)
        label, scenario_ids = f"last-{args.last_hours:g}h-{end.strftime('%Y%m%dT%H%MZ')}", None

    traces = fetch_window(start, end)
    records, eligible = build_records(traces, model, scenario_ids)
    if scenario_ids is not None and len(records) != len(scenario_ids):
        raise SystemExit(f"period rejected: {len(records)} conversations, expected {len(scenario_ids)}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    summary: dict[str, Any] = {
        "label": label, "judge_id": judge_id, "model": model,
        "from": _iso(start), "to": _iso(end),
        "langfuse_traces": eligible, "conversations": len(records),
    }
    if not records:
        summary.update({"random_sample": 0, "risk_sample": 0, "judge_calls": 0})
        (OUTPUT_DIR / "latest.json").write_text(json.dumps(summary, indent=2))
        print(f"{label}: no eligible conversations; judge not called.")
        return 0

    groups = {name: DEFAULT_RISK_GROUPS[name] for name in config["risk_groups"]}
    plan = select_traces(records, config["random_rate"], groups, seed=7)
    risk_ids = list(dict.fromkeys(t["id"] for group in plan["risk_groups"].values() for t in group))
    summary.update({
        "random_sample": len(plan["random"]),
        "risk_sample": len(risk_ids),
        "risk_groups": {name: len(group) for name, group in plan["risk_groups"].items()},
        "judge_calls": len(plan["to_judge"]),
    })
    print(
        f"{label}: {eligible} Langfuse traces -> {len(records)} conversations; "
        f"random {summary['random_sample']}, risk {summary['risk_sample']} "
        f"{summary['risk_groups']}; judge calls {summary['judge_calls']} "
        f"({judge_id})"
    )
    if args.dry_run:
        return 0

    verdicts = judge_sample(judge_id, plan["to_judge"])
    random_verdicts = {t["id"]: verdicts[t["id"]] for t in plan["random"]}
    risk_verdicts = {tid: verdicts[tid] for tid in risk_ids}
    estimate = corrected_mode_prevalence(list(random_verdicts.values()), *judge_test_data(judge_id))
    scores = build_score_records(mode, random_verdicts, risk_verdicts, estimate, label)
    batch_trace_id = _batch_trace(mode, label, summary, estimate)
    # Langfuse rejects a score with no target, so the period score attaches to
    # one stable "monitor run" trace per period (same id on every rerun).
    posted = [
        {**s, "trace_id": batch_trace_id} if s["trace_id"] is None else s for s in scores
    ]
    written = post_scores(posted)

    keys = {r["id"]: r["key"] for r in records}
    detail = {
        **summary,
        "random_verdicts": {keys[t]: {"trace_id": t, "verdict": v} for t, v in random_verdicts.items()},
        "risk_verdicts": {keys[t]: {"trace_id": t, "verdict": v} for t, v in risk_verdicts.items()},
        "estimate": estimate,
        "score_ids": [s["score_id"] for s in scores],
    }
    (OUTPUT_DIR / f"{label}.json").write_text(json.dumps(detail, indent=2))
    (OUTPUT_DIR / "latest.json").write_text(json.dumps(detail, indent=2))

    history_entry = {
        **summary,
        "raw": estimate["raw"], "corrected": estimate["corrected"],
        "ci_low": estimate["ci_low"], "ci_high": estimate["ci_high"],
        "failure_sensitivity": estimate["failure_sensitivity"],
        "pass_specificity": estimate["pass_specificity"],
    }
    if args.period:
        rows = _upsert_history(history_entry)
        from monitoring.chart import prevalence_chart

        CHART_PATH.write_text(prevalence_chart(rows, threshold=config["threshold"], mode=mode))
    print(
        f"{label}: raw {estimate['raw']}, corrected {estimate['corrected']} "
        f"(95% CI {estimate['ci_low']}-{estimate['ci_high']}); {written} scores written"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
