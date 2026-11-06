"""HW4 review app: open coding, emerging themes, taxonomy, and labels.

Run from the repository root:
    .venv/bin/python -m analysis.review_app.server        # http://localhost:8021

One conversation (all traces sharing a session) is the unit of review. Its
anchor trace is the conversation's first trace; every trace id is kept with it.

State lives in analysis/state/ (committed for grading):
    annotations.json      {"annotations": [...]}  open codes, highlights, tags, edit history
    themes.json           working tags: memos, renames, merges (history kept)
    patterns.json         {"modes": [...]}         the taxonomy
    suggestions.json      [...]                    AI suggestions with accept/reject decisions
    sample_manifest.json  review batches
    labels/<mode>.jsonl   append-only present/absent judgments (1 = failure present)

Labels are also written to Langfuse as scores. This app points at the local
Langfuse stack by default (REVIEW_LANGFUSE_HOST etc. override it), so the
student's cloud settings in .env are left alone.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from analysis.helpers import _state

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = Path(__file__).resolve().parent
PORT = int(os.environ.get("REVIEW_PORT", "8021"))
TOOL_OUTPUT_LIMIT = 20000

SCENARIOS = ROOT / "scenarios/support_scenarios.jsonl"
RESULTS = ROOT / "scenarios/final-results.jsonl"
TRACES = ROOT / "traces/support_traces.json"
HW3_REVIEW = ROOT / "scenarios/support_review.jsonl"
MONITORING = ROOT / "scenarios/monitoring_scenarios.jsonl"

LANGFUSE = {
    "host": os.environ.get("REVIEW_LANGFUSE_HOST", "http://localhost:3000"),
    "public_key": os.environ.get("REVIEW_LANGFUSE_PUBLIC_KEY", "pk-lf-cartwheel-dev"),
    "secret_key": os.environ.get("REVIEW_LANGFUSE_SECRET_KEY", "sk-lf-cartwheel-dev"),
}
SUGGEST_MODEL = os.environ.get("REVIEW_SUGGEST_MODEL", "gpt-4.1")

_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# conversations
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict]:
    return _state.read_jsonl(path)


def parse_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def message_text(value) -> str:
    value = parse_json(value)
    if not isinstance(value, list):
        return "" if value is None else str(value)
    return "\n\n".join(
        part["content"]
        for msg in value
        for part in (msg or {}).get("parts", []) or []
        if part.get("type") == "text" and part.get("content")
    )


def clip(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    if len(text) > TOOL_OUTPUT_LIMIT:
        return text[:TOOL_OUTPUT_LIMIT] + f"\n… ({len(text) - TOOL_OUTPUT_LIMIT} more characters)"
    return text


def trace_turn(trace: dict) -> dict:
    tools, model = [], None
    for obs in sorted(trace.get("observations") or [], key=lambda o: o.get("startTime") or ""):
        attrs = ((obs.get("metadata") or {}).get("attributes")) or {}
        if obs.get("type") == "TOOL":
            output = parse_json(obs.get("output"))
            tools.append({
                "name": obs.get("name"),
                "args": parse_json(obs.get("input")),
                "output": clip(output),
                "ok": output.get("ok") if isinstance(output, dict) else None,
                "denied": attrs.get("cartwheel.permission_denied") == "true",
            })
        elif obs.get("type") == "GENERATION":
            model = obs.get("model") or model
    return {
        "trace_id": trace.get("id"),
        "timestamp": trace.get("timestamp"),
        "user": message_text(trace.get("input")),
        "agent": message_text(trace.get("output")),
        "tools": tools,
        "model": model,
    }


def build_conversations() -> list[dict]:
    results = {r["scenario_id"]: r for r in read_jsonl(RESULTS)}
    reviews = {r["scenario_id"]: r for r in read_jsonl(HW3_REVIEW)}
    monitoring = {r["id"] for r in read_jsonl(MONITORING)}
    by_scenario: dict[str, list[dict]] = {}
    for trace in json.loads(TRACES.read_text()).get("traces", []):
        sid = trace.get("cartwheel_scenario_id")
        if sid:
            by_scenario.setdefault(sid, []).append(trace)

    out = []
    for scenario in read_jsonl(SCENARIOS):
        sid = scenario["id"]
        result = results.get(sid, {})
        sessions: dict[str, list[dict]] = {}
        for trace in by_scenario.get(sid, []):
            sessions.setdefault(trace.get("sessionId") or trace["id"], []).append(trace)
        ordered = sorted(
            (sorted(ts, key=lambda t: t.get("timestamp") or "") for ts in sessions.values()),
            key=lambda ts: ts[-1].get("timestamp") or "",
        )
        graded = ordered[-1] if ordered else []
        turns = [trace_turn(t) for t in graded]
        for i, rt in enumerate(result.get("turns") or []):
            if i < len(turns):
                turns[i]["user"] = rt.get("user") or turns[i]["user"]
                turns[i]["agent"] = rt.get("agent") or turns[i]["agent"]
            else:
                turns.append({"user": rt.get("user"), "agent": rt.get("agent"), "tools": [],
                              "trace_id": None, "no_trace": True})
        trace_ids = [t["trace_id"] for t in turns if t.get("trace_id")]
        out.append({
            "id": sid,
            "trace_id": trace_ids[0] if trace_ids else None,
            "trace_ids": trace_ids,
            "session_id": graded[0].get("sessionId") if graded else None,
            "group": scenario.get("scenario_group"),
            "dq": scenario.get("data_quality_case_id"),
            "tuple": scenario.get("tuple") or {},
            "expected": scenario.get("expected") or {},
            "grounding": scenario.get("grounding"),
            "opening": scenario.get("opening_message"),
            "status": result.get("status", "not run"),
            "model": result.get("model"),
            "turns": turns,
            "tool_count": sum(len(t["tools"]) for t in turns),
            "earlier_attempts": [[trace_turn(t) for t in ts] for ts in ordered[:-1]],
            "hw3_review": reviews.get(sid),
            "monitoring": sid in monitoring,
        })
    return out


_conversations: bytes | None = None


def conversations_bytes() -> bytes:
    global _conversations
    if _conversations is None:
        _conversations = json.dumps(build_conversations(), ensure_ascii=False).encode()
    return _conversations


# ---------------------------------------------------------------------------
# state files
# ---------------------------------------------------------------------------

DEFAULTS = {
    "annotations": {"annotations": []},
    "themes": {"tags": {}, "history": []},
    "patterns": {"modes": []},
    "suggestions": [],
    "sample_manifest": {"unit": "conversation", "batches": []},
}


def state_file(name: str) -> Path:
    return _state.state_path(f"{name}.json")


def load(name: str):
    data = _state.read_json(state_file(name), default=None)
    if data is None or (name == "annotations" and isinstance(data, dict) and "annotations" not in data):
        return json.loads(json.dumps(DEFAULTS[name]))
    return data


def save(name: str, data) -> None:
    _state.write_json(state_file(name), data)


def _stamp(a: dict) -> str:
    return max(a.get("updated_ts") or "", a.get("saved_ts") or "", a.get("ts") or "")


def merge_annotations(disk: dict, incoming: dict) -> dict:
    """Record-level merge so two writers (a browser tab and a dictated note) never erase each other.

    Records only on disk are kept; for a record in both, the newer one wins.
    """
    by_id = {a["id"]: a for a in disk.get("annotations", [])}
    for a in incoming.get("annotations", []):
        old = by_id.get(a["id"])
        if old is None or _stamp(a) >= _stamp(old):
            by_id[a["id"]] = a
    return {**incoming, "annotations": list(by_id.values())}


def live_labels() -> dict[str, dict[str, dict]]:
    """{mode: {scenario_id: latest live label row}}"""
    out: dict[str, dict[str, dict]] = {}
    labels_dir = _state.state_path("labels")
    for path in sorted(labels_dir.glob("*.jsonl")) if labels_dir.exists() else []:
        rows = {}
        for row in _state.read_jsonl(path):
            if row.get("superseded_by") or "scenario_id" not in row:
                continue
            rows[row["scenario_id"]] = row
        out[path.stem] = rows
    return out


def append_label(mode: str, conv: dict, label: int | None) -> dict:
    """Append a judgment, marking the prior live row for this conversation superseded."""
    path = _state.state_path("labels", f"{mode}.jsonl")
    rows = _state.read_jsonl(path)
    new_id = f"{conv['id']}#{sum(1 for r in rows if r.get('scenario_id') == conv['id'])}"
    for row in rows:
        if row.get("scenario_id") == conv["id"] and not row.get("superseded_by"):
            row["superseded_by"] = new_id
    record = {
        "trace_id": conv["trace_id"],
        "scenario_id": conv["id"],
        "session_id": conv.get("session_id"),
        "trace_ids": conv.get("trace_ids"),
        "label": label,
        "source": "human",
        "ts": now(),
        "label_id": new_id,
    }
    if label is None:
        record["cleared"] = True
    rows.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    os.replace(tmp, path)
    return record


# ---------------------------------------------------------------------------
# Langfuse scores
# ---------------------------------------------------------------------------

def push_score(mode: str, record: dict) -> None:
    """Write the label to the conversation's anchor trace; record the outcome in langfuse_sync.json.

    Uses the public REST endpoint directly so a failed write is reported, not silently queued.
    """
    import base64
    import urllib.request

    status = {"ts": now()}
    try:
        if record.get("label") is None:
            status["result"] = "skipped (cleared)"
        else:
            body = json.dumps({
                "id": f"{mode}-{record['trace_id']}",  # one live score per trace and mode; relabels overwrite
                "traceId": record["trace_id"], "name": mode, "value": int(record["label"]),
                "dataType": "NUMERIC", "comment": f"{record['scenario_id']} ({record['label_id']}) via review_app",
            }).encode()
            auth = base64.b64encode(f"{LANGFUSE['public_key']}:{LANGFUSE['secret_key']}".encode()).decode()
            req = urllib.request.Request(f"{LANGFUSE['host']}/api/public/scores", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                status["result"] = "ok" if resp.status < 300 else f"error: HTTP {resp.status}"
                status["score_id"] = json.loads(resp.read() or b"{}").get("id")
    except Exception as exc:  # keep the local label even when Langfuse is down
        status["result"] = f"error: {exc}"
    with _lock:
        sync = _state.read_json(_state.state_path("langfuse_sync.json"), default={}) or {}
        sync.setdefault(mode, {})[record["scenario_id"]] = {**status, "label_id": record["label_id"]}
        _state.write_json(_state.state_path("langfuse_sync.json"), sync)


# ---------------------------------------------------------------------------
# theme suggestions (only on request, only on the student's own tags)
# ---------------------------------------------------------------------------

SUGGEST_PROMPT = """You help a UX researcher name themes during qualitative coding of AI support-agent \
conversations. The researcher wrote every note and created every tag below. Work ONLY with these tags.
Do not invent new themes that are not grounded in at least two of the researcher's notes.

For the request type "{kind}":
- "rename": for each tag, suggest a clearer, more specific name if one exists (snake_case, describes an \
observable agent behavior). Skip tags whose name is already good.
- "structure": point out tags that look like the same theme (merge) or one tag whose notes look like two \
different problems (split). A merge is right only if one product change would fix both.

Return JSON: {{"suggestions": [{{"type": "rename"|"merge"|"split", "tags": [...], \
"proposal": "new name or description", "reason": "one sentence citing the notes"}}]}}. \
Return at most 5. If nothing would help, return an empty list.

Tags and their notes:
{tags}
"""


def suggest(kind: str, tag_names: list[str]) -> list[dict]:
    from openai import OpenAI

    ann = load("annotations")["annotations"]
    themes = load("themes")
    lines = []
    for name in tag_names:
        notes = [a["note"] for a in ann if name in (a.get("tags") or []) and a.get("note")]
        memo = (themes["tags"].get(name) or {}).get("memo", "")
        lines.append(f"## {name}\nmemo: {memo or '(none)'}\n" + "\n".join(f"- {n}" for n in notes))
    resp = OpenAI().chat.completions.create(
        model=SUGGEST_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": SUGGEST_PROMPT.format(kind=kind, tags="\n\n".join(lines))}],
    )
    items = json.loads(resp.choices[0].message.content).get("suggestions", [])
    created = [{
        "id": f"sug-{uuid.uuid4().hex[:8]}",
        "source": "ai",
        "kind": f"theme_{s.get('type', kind)}",
        "tags": s.get("tags", []),
        "proposal": s.get("proposal", ""),
        "reason": s.get("reason", ""),
        "model": SUGGEST_MODEL,
        "status": "pending",
        "ts": now(),
    } for s in items]
    with _lock:
        data = load("suggestions")
        data.extend(created)
        save("suggestions", data)
    return created


# ---------------------------------------------------------------------------
# sampling (never looks at outcomes or notes, only at the conversation's shape)
# ---------------------------------------------------------------------------

STRATIFY_DIMENSIONS = ("role", "intent", "scenario_group", "difficulty", "tools_needed",
                       "applicable_policy", "record_state", "user_style")


def conv_features(c: dict) -> dict:
    tools = [t["name"] for turn in c["turns"] for t in turn["tools"]]
    return {
        "messages": len(c["turns"]),
        "tool_calls": len(tools),
        "distinct_tools": len(set(tools)),
        "reply_chars": sum(len(t.get("agent") or "") for t in c["turns"]),
        "role": c["tuple"].get("role"),
        "intent": c["tuple"].get("intent"),
        "tools": sorted(set(tools)),
    }


def dim_value(c: dict, dim: str):
    return c.get("group") if dim == "scenario_group" else c["tuple"].get(dim)


def draw_sample(method: str, n: int, seed: int, dimension: str | None, exclude: set[str]) -> list[dict]:
    import math
    import random

    convs = [c for c in json.loads(conversations_bytes()) if c["id"] not in exclude and c["status"] == "completed"]
    rng = random.Random(seed)
    n = max(1, min(n, len(convs)))

    if method == "random":
        return [{"scenario_id": c["id"], "reason": "uniform random draw"} for c in rng.sample(convs, n)]

    if method == "stratified":
        if dimension not in STRATIFY_DIMENSIONS:
            raise ValueError(f"dimension must be one of {', '.join(STRATIFY_DIMENSIONS)}")
        groups: dict[str, list[dict]] = {}
        for c in convs:
            groups.setdefault(str(dim_value(c, dimension)), []).append(c)
        for g in groups.values():
            rng.shuffle(g)
        picks, keys = [], sorted(groups)
        while len(picks) < n and any(groups[k] for k in keys):
            for k in keys:  # round robin keeps every value represented as evenly as possible
                if groups[k] and len(picks) < n:
                    picks.append({"scenario_id": groups[k].pop()["id"], "reason": f"{dimension} = {k}"})
        return picks

    feats = {c["id"]: conv_features(c) for c in convs}
    roles = sorted({f["role"] for f in feats.values()})
    intents = sorted({f["intent"] for f in feats.values()})
    all_tools = sorted({t for f in feats.values() for t in f["tools"]})

    if method == "outlier":
        lengths = sorted(f["reply_chars"] + 400 * f["tool_calls"] for f in feats.values())
        q1, q3 = lengths[len(lengths) // 4], lengths[3 * len(lengths) // 4]
        tool_freq = {t: sum(t in f["tools"] for f in feats.values()) for t in all_tools}
        scored = []
        for c in convs:
            f = feats[c["id"]]
            size = f["reply_chars"] + 400 * f["tool_calls"]
            rare = [t for t in f["tools"] if tool_freq[t] <= max(2, len(convs) // 50)]
            reasons = []
            if size > q3 + 1.5 * (q3 - q1):
                reasons.append(f"unusually long ({f['messages']} messages, {f['tool_calls']} tool calls)")
            if rare:
                reasons.append(f"rare tool: {', '.join(rare)}")
            if f["messages"] >= 4:
                reasons.append(f"{f['messages']}-message conversation")
            if reasons:
                scored.append((len(reasons), size, c["id"], "; ".join(reasons)))
        scored.sort(reverse=True)
        return [{"scenario_id": sid, "reason": why} for _, _, sid, why in scored[:n]]

    # cluster: k-means over shape features, one representative (closest to centroid) per cluster
    def vec(f):
        base = [f["messages"], f["tool_calls"], f["distinct_tools"], math.log1p(f["reply_chars"])]
        return base + [float(f["role"] == r) for r in roles] + [float(f["intent"] == i) for i in intents] \
            + [float(t in f["tools"]) for t in all_tools]
    ids = list(feats)
    raw = [vec(feats[i]) for i in ids]
    dims = len(raw[0])
    means = [sum(v[d] for v in raw) / len(raw) for d in range(dims)]
    sds = [math.sqrt(sum((v[d] - means[d]) ** 2 for v in raw) / len(raw)) or 1.0 for d in range(dims)]
    X = [[(v[d] - means[d]) / sds[d] for d in range(dims)] for v in raw]
    k = n
    cents = [X[i][:] for i in rng.sample(range(len(X)), k)]
    assign = [0] * len(X)
    for _ in range(50):
        new = [min(range(k), key=lambda c: sum((a - b) ** 2 for a, b in zip(x, cents[c]))) for x in X]
        if new == assign:
            break
        assign = new
        for c in range(k):
            members = [X[i] for i in range(len(X)) if assign[i] == c]
            if members:
                cents[c] = [sum(m[d] for m in members) / len(members) for d in range(dims)]
    picks = []
    for c in range(k):
        members = [i for i in range(len(X)) if assign[i] == c]
        if not members:
            continue
        best = min(members, key=lambda i: sum((a - b) ** 2 for a, b in zip(X[i], cents[c])))
        f = feats[ids[best]]
        picks.append({"scenario_id": ids[best],
                      "reason": f"typical of a group of {len(members)}: {f['role']}, {f['intent']}, "
                                f"{f['messages']} msg, {f['tool_calls']} tool calls"
                                + (f" ({', '.join(f['tools'])})" if f["tools"] else "")})
    return picks


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

WRITABLE = {"annotations", "themes", "patterns", "suggestions", "sample_manifest"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype="application/json", status=200):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"null")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._send((APP_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/conversations":
            return self._send(conversations_bytes())
        if path == "/api/state":
            with _lock:
                sync = _state.read_json(_state.state_path("langfuse_sync.json"), default={})
                return self._send({**{k: load(k) for k in WRITABLE}, "labels": live_labels(),
                                   "langfuse_sync": sync, "suggest_model": SUGGEST_MODEL})
        self._send({"error": "not found"}, status=404)

    def do_PUT(self):
        # PUT /api/state/<name> replaces one state file.
        parts = self.path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "state"] and parts[2] in WRITABLE:
            with _lock:
                body = self._body()
                if parts[2] == "annotations":
                    body = merge_annotations(load("annotations"), body)
                save(parts[2], body)
            return self._send({"ok": True, "merged": body if parts[2] == "annotations" else None})
        self._send({"error": "not found"}, status=404)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/label":
                body = self._body()
                convs = {c["id"]: c for c in json.loads(conversations_bytes())}
                conv = convs[body["scenario_id"]]
                if body.get("label") not in (0, 1, None):
                    raise ValueError("label must be 0, 1, or null")
                with _lock:
                    record = append_label(body["mode"], conv, body.get("label"))
                threading.Thread(target=push_score, args=(body["mode"], record), daemon=True).start()
                return self._send(record)
            if path == "/api/sample":
                body = self._body()
                manifest = load("sample_manifest")
                exclude = {i for b in manifest["batches"] for i in b.get("scenario_ids", [])}
                exclude |= set(body.get("exclude") or [])
                return self._send(draw_sample(body.get("method", "random"), int(body.get("n", 15)),
                                              int(body.get("seed", 1)), body.get("dimension"), exclude))
            if path == "/api/suggest":
                body = self._body()
                return self._send(suggest(body.get("kind", "rename"), body.get("tags") or []))
        except Exception as exc:
            return self._send({"error": str(exc)}, status=400)
        self._send({"error": "not found"}, status=404)

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith(("GET /api/state", "PUT /api/state")):
            return
        sys.stderr.write("%s\n" % (fmt % args))


if __name__ == "__main__":
    print(f"HW4 review app: http://localhost:{PORT}  (Langfuse scores → {LANGFUSE['host']})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
