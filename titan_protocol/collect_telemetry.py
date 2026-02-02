#!/usr/bin/env python3
"""Collect telemetry for a run directory and write telemetry.json."""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path


KEY_MAP = {
    "tools_used": {"tool", "tool_name", "toolName"},
    "subagents": {"agent", "agent_name", "agentName", "subagent_type"},
    "skills_used": {"skill", "skills"},
    "slash_commands": {"command", "slash_command", "slashCommand"},
}

TOKEN_KEYS = [
    ("tokens_prompt", {"prompt_tokens", "input_tokens"}),
    ("tokens_completion", {"completion_tokens", "output_tokens"}),
    ("tokens_total", {"total_tokens"}),
]

SESSION_KEYS = ("sessionID", "session_id", "sessionId")
PHASE_REGEX = re.compile(r"\bPHASE:\s*([A-Z][A-Z0-9_-]*)", re.IGNORECASE)
PHASE_FIELDS = ("content", "text", "message", "input", "output", "prompt")

LOG_TOKEN_PATTERNS = {
    "tokens_prompt": [
        re.compile(r"prompt[_\\s-]*tokens?\\s*[:=]\\s*(\\d+)", re.IGNORECASE),
        re.compile(r"input[_\\s-]*tokens?\\s*[:=]\\s*(\\d+)", re.IGNORECASE),
    ],
    "tokens_completion": [
        re.compile(r"completion[_\\s-]*tokens?\\s*[:=]\\s*(\\d+)", re.IGNORECASE),
        re.compile(r"output[_\\s-]*tokens?\\s*[:=]\\s*(\\d+)", re.IGNORECASE),
    ],
    "tokens_total": [
        re.compile(r"total[_\\s-]*tokens?\\s*[:=]\\s*(\\d+)", re.IGNORECASE),
        re.compile(r"tokens?[_\\s-]*total\\s*[:=]\\s*(\\d+)", re.IGNORECASE),
    ],
}

LOG_COMBINED_PATTERN = re.compile(
    r"prompt\\s*[:=]\\s*(\\d+).*?completion\\s*[:=]\\s*(\\d+).*?total\\s*[:=]\\s*(\\d+)",
    re.IGNORECASE | re.DOTALL,
)


def walk(obj, handler):
    if isinstance(obj, dict):
        handler(obj)
        for value in obj.values():
            walk(value, handler)
    elif isinstance(obj, list):
        for value in obj:
            walk(value, handler)


def parse_events(events):
    collected = {
        "tools_used": set(),
        "models": set(),
        "subagents": set(),
        "skills_used": set(),
        "slash_commands": set(),
        "tokens_prompt": 0,
        "tokens_completion": 0,
        "tokens_total": 0,
        "session_id": None,
        "variant": None,
        "phase_timeline": [],
    }

    def parse_timestamp(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            ts = int(value)
            if ts > 1_000_000_000_000:
                return ts
            if ts > 1_000_000_000:
                return ts * 1000
            return ts
        if isinstance(value, str):
            try:
                parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
                return int(parsed.timestamp() * 1000)
            except ValueError:
                return None
        return None

    def extract_timestamp(node):
        if not isinstance(node, dict):
            return None
        for key in ("timestamp", "time", "created_at", "createdAt", "started_at"):
            if key in node:
                ts = parse_timestamp(node.get(key))
                if ts is not None:
                    return ts
        return None

    def add_tokens(token_node):
        if not isinstance(token_node, dict):
            return
        prompt = token_node.get("prompt")
        if prompt is None:
            prompt = token_node.get("input")
        if prompt is None:
            prompt = token_node.get("prompt_tokens")
        if prompt is None:
            prompt = token_node.get("input_tokens")
        completion = token_node.get("completion")
        if completion is None:
            completion = token_node.get("output")
        if completion is None:
            completion = token_node.get("completion_tokens")
        if completion is None:
            completion = token_node.get("output_tokens")
        total = token_node.get("total")
        if total is None:
            total = token_node.get("total_tokens")
        if isinstance(prompt, int):
            collected["tokens_prompt"] += prompt
        if isinstance(completion, int):
            collected["tokens_completion"] += completion
        if isinstance(total, int):
            collected["tokens_total"] += total

    def add_model(node):
        if "model" in node:
            model_value = node.get("model")
            model_name, variant = parse_model_value(model_value)
            if model_name:
                collected["models"].add(model_name)
            if variant and not collected["variant"]:
                collected["variant"] = variant
        if "modelID" in node or "modelId" in node:
            model_id = node.get("modelID") or node.get("modelId")
            provider = node.get("providerID") or node.get("providerId")
            model_name, variant = parse_model_value(
                {"providerID": provider, "modelID": model_id}
            )
            if model_name:
                collected["models"].add(model_name)
            if variant and not collected["variant"]:
                collected["variant"] = variant
        if (
            "variant" in node
            and isinstance(node.get("variant"), str)
            and not collected["variant"]
        ):
            collected["variant"] = node["variant"]

    def add_phase_markers(node):
        ts = extract_timestamp(node)
        for field in PHASE_FIELDS:
            value = node.get(field)
            if isinstance(value, str):
                match = PHASE_REGEX.search(value)
                if match and ts is not None:
                    collected["phase_timeline"].append(
                        {"phase": match.group(1).upper(), "timestamp_ms": ts}
                    )

    def handler(node):
        if not collected["session_id"]:
            for key in SESSION_KEYS:
                value = node.get(key)
                if isinstance(value, str):
                    collected["session_id"] = value
                    break
        for field, keys in KEY_MAP.items():
            for key in keys:
                if key in node:
                    value = node[key]
                    if isinstance(value, str):
                        collected[field].add(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                collected[field].add(item)
        add_model(node)
        add_phase_markers(node)
        if "tokens" in node:
            add_tokens(node.get("tokens"))
        if "usage" in node:
            add_tokens(node.get("usage"))
        if "token_usage" in node:
            add_tokens(node.get("token_usage"))
        for output_key, token_keys in TOKEN_KEYS:
            for key in token_keys:
                if key in node and isinstance(node[key], int):
                    collected[output_key] += node[key]

    walk(events, handler)
    if (
        collected["tokens_total"] == 0
        and collected["tokens_prompt"]
        and collected["tokens_completion"]
    ):
        collected["tokens_total"] = (
            collected["tokens_prompt"] + collected["tokens_completion"]
        )
    return collected


def parse_model_value(model_value):
    if isinstance(model_value, str):
        return model_value, None
    if isinstance(model_value, dict):
        provider = (
            model_value.get("providerID")
            or model_value.get("provider")
            or model_value.get("providerId")
        )
        model_id = (
            model_value.get("modelID")
            or model_value.get("modelId")
            or model_value.get("model")
        )
        variant = model_value.get("variant") or model_value.get("modelVariant")
        if provider and model_id:
            return f"{provider}/{model_id}", variant
        if model_id:
            return str(model_id), variant
    return None, None


def load_events_from_jsonl(path: Path):
    events = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def load_events_from_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_phase_log(path: Path):
    timeline = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",", 1)]
        if len(parts) != 2:
            continue
        ts_raw, phase_raw = parts
        ts = None
        try:
            ts = int(ts_raw)
        except ValueError:
            try:
                parsed = dt.datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts = int(parsed.timestamp() * 1000)
            except ValueError:
                ts = None
        if ts is None:
            continue
        timeline.append({"phase": phase_raw.upper(), "timestamp_ms": ts})
    return timeline


def compute_phase_durations(timeline):
    if not timeline:
        return {}, None
    timeline = sorted(timeline, key=lambda x: x["timestamp_ms"])
    durations = {}
    for idx, entry in enumerate(timeline):
        phase = entry["phase"]
        start = entry["timestamp_ms"]
        end = timeline[idx + 1]["timestamp_ms"] if idx + 1 < len(timeline) else None
        if end is not None:
            durations[phase] = end - start
    total = timeline[-1]["timestamp_ms"] - timeline[0]["timestamp_ms"]
    return durations, total


def parse_tokens_from_text(text: str) -> dict:
    values = {"tokens_prompt": [], "tokens_completion": [], "tokens_total": []}
    for key, patterns in LOG_TOKEN_PATTERNS.items():
        for pattern in patterns:
            for match in pattern.findall(text):
                try:
                    values[key].append(int(match))
                except (TypeError, ValueError):
                    continue
    for match in LOG_COMBINED_PATTERN.findall(text):
        try:
            prompt, completion, total = (int(match[0]), int(match[1]), int(match[2]))
        except (TypeError, ValueError):
            continue
        values["tokens_prompt"].append(prompt)
        values["tokens_completion"].append(completion)
        values["tokens_total"].append(total)
    parsed = {}
    for key, items in values.items():
        parsed[key] = max(items) if items else None
    return parsed


def parse_tokens_from_logs(paths) -> dict:
    combined = {"tokens_prompt": None, "tokens_completion": None, "tokens_total": None}
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            continue
        parsed = parse_tokens_from_text(text)
        for key, value in parsed.items():
            if value is None:
                continue
            if combined[key] is None or value > combined[key]:
                combined[key] = value
    return combined


def export_opencode(session_id: str, out_path: Path):
    opencode_bin = os.getenv("OPENCODE_BIN", "opencode")
    result = subprocess.run(
        [opencode_bin, "export", session_id],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit("opencode export failed")
    out_path.write_text(result.stdout, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Collect run telemetry.")
    parser.add_argument("--run-dir", required=True, help="Run directory path.")
    parser.add_argument("--events", help="Path to JSONL events file.")
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export opencode session JSON.",
    )
    parser.add_argument("--session", help="opencode session ID for export.")
    parser.add_argument("--model", help="Model identifier (provider/model).")
    parser.add_argument("--variant", help="Model variant (if used).")
    parser.add_argument(
        "--phase-log",
        help="Optional phase log file with lines: <epoch_ms_or_iso>,<PHASE>.",
    )
    parser.add_argument(
        "--logs",
        help="Comma-separated log paths to parse token stats from (best-effort).",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_export_path = None
    events = []

    if args.export:
        if not args.session:
            raise SystemExit("--session is required when using --export")
        raw_export_path = run_dir / "telemetry_raw.json"
        export_opencode(args.session, raw_export_path)
        events = load_events_from_json(raw_export_path)
    elif args.events:
        events_path = Path(args.events).resolve()
        raw_export_path = events_path
        events = load_events_from_jsonl(events_path)
    else:
        for candidate in (run_dir / "events.jsonl", run_dir / "opencode_events.jsonl"):
            if candidate.exists():
                raw_export_path = candidate
                events = load_events_from_jsonl(candidate)
                break

    phase_timeline = []
    if args.phase_log:
        phase_timeline = load_phase_log(Path(args.phase_log).resolve())

    collected = parse_events(events) if events else {
        "tools_used": set(),
        "models": set(),
        "subagents": set(),
        "skills_used": set(),
        "slash_commands": set(),
        "tokens_prompt": None,
        "tokens_completion": None,
        "tokens_total": None,
        "session_id": None,
        "variant": None,
        "phase_timeline": [],
    }

    if collected.get("phase_timeline"):
        phase_timeline.extend(collected["phase_timeline"])
    phase_durations, duration_ms = compute_phase_durations(phase_timeline)

    models = sorted(collected.get("models", []))

    log_tokens = {}
    if args.logs:
        log_paths = [p.strip() for p in args.logs.split(",") if p.strip()]
        log_tokens = parse_tokens_from_logs(log_paths)

    def is_missing(value):
        return value is None or value == 0

    if log_tokens:
        for key in ("tokens_prompt", "tokens_completion", "tokens_total"):
            if is_missing(collected.get(key)) and log_tokens.get(key) is not None:
                collected[key] = log_tokens[key]
    telemetry = {
        "session_id": args.session or collected.get("session_id"),
        "model": args.model or (models[0] if models else None),
        "variant": args.variant or collected.get("variant"),
        "tokens_prompt": collected.get("tokens_prompt") or None,
        "tokens_completion": collected.get("tokens_completion") or None,
        "tokens_total": collected.get("tokens_total") or None,
        "tools_used": sorted(collected.get("tools_used", [])),
        "subagents": sorted(collected.get("subagents", [])),
        "skills_used": sorted(collected.get("skills_used", [])),
        "slash_commands": sorted(collected.get("slash_commands", [])),
        "models": models,
        "event_count": len(events) if events else None,
        "raw_events": str(raw_export_path) if raw_export_path else None,
        "phase_timeline": phase_timeline or None,
        "phase_durations_ms": phase_durations or None,
        "duration_ms": duration_ms,
    }

    (run_dir / "telemetry.json").write_text(
        json.dumps(telemetry, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote telemetry to {run_dir / 'telemetry.json'}")


if __name__ == "__main__":
    main()
