#!/usr/bin/env python3
"""Prepare Titan Protocol test runs and score them into a CSV."""

import argparse
import csv
import datetime as dt
import re
import shutil
import subprocess
import sys
import json
from pathlib import Path

TEMPLATE_FILES = [
    "legacy_crypto.py",
    "TITAN_SPEC.md",
    "judge.py",
    "README.md",
    "ruff.toml",
    ".pylintrc",
    "mypy.ini",
    "pyrightconfig.json",
    ".pydocstyle",
    "bandit.yaml",
    ".jscpd.json",
    ".codespellrc",
    ".isort.cfg",
    ".semgrepignore",
]

DEFAULT_TOOLS = ["ampcode", "augment", "opencode"]
SCORED_MARKER = ".scored"
REQUIRED_OUTPUTS = ["ingest.py", "report.py", "main.py", "tests"]
DEFAULT_OUTPUT_ROOT = Path.home() / "titan_protocol_runs"

SCORE_PATTERNS = {
    "context": re.compile(r"\[(\d+)/25\].*Context Trap", re.IGNORECASE),
    "research": re.compile(r"\[(\d+)/25\].*Research Trap", re.IGNORECASE),
    "qa": re.compile(r"\[(\d+)/20\].*QA Trap", re.IGNORECASE),
    "quality": re.compile(r"\[(\d+)/20\].*Quality", re.IGNORECASE),
    "docs": re.compile(r"\[(\d+)/10\].*Documentation", re.IGNORECASE),
    "final": re.compile(r"FINAL SCORE:\s*(\d+)/100", re.IGNORECASE),
    "ruff_errors": re.compile(r"Linter Failed \((\d+) errors\)", re.IGNORECASE),
}
CSV_FIELDS = [
    "timestamp",
    "tool",
    "run_id",
    "complete",
    "missing",
    "score",
    "context",
    "research",
    "qa",
    "quality",
    "quality_ruff",
    "quality_modernization",
    "quality_complexity",
    "quality_pylint",
    "quality_dead_code",
    "quality_duplication",
    "quality_type_check",
    "quality_security",
    "quality_coverage",
    "quality_docstyle",
    "quality_semgrep",
    "quality_pip_audit",
    "quality_codespell",
    "quality_ruff_format",
    "quality_isort",
    "quality_license",
    "quality_details",
    "docs",
    "ruff_errors",
    "judge_exit",
    "model",
    "variant",
    "session_id",
    "tokens_prompt",
    "tokens_completion",
    "tokens_total",
    "duration_ms",
    "phase_timeline",
    "phase_durations_ms",
    "tools_used",
    "subagents",
    "skills_used",
    "slash_commands",
    "telemetry_json",
]


def parse_score(output: str) -> dict:
    result = {
        "context": None,
        "research": None,
        "qa": None,
        "quality": None,
        "docs": None,
        "final": None,
        "ruff_errors": None,
    }
    for key, pattern in SCORE_PATTERNS.items():
        match = pattern.search(output)
        if match:
            value = match.group(1)
            result[key] = int(value)
    return result


def load_judge_json(run_dir: Path) -> dict:
    judge_path = run_dir / "judge.json"
    if not judge_path.exists():
        return {}
    try:
        return json.loads(judge_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def apply_pytest_cap(score: dict, judge_payload: dict) -> dict:
    execution = judge_payload.get("execution") or {}
    pytest_payload = execution.get("pytest") or {}
    if pytest_payload.get("ok") is False:
        score["quality"] = 0
        quality_breakdown = score.get("quality_breakdown")
        if isinstance(quality_breakdown, dict):
            quality_breakdown["score"] = 0
            for check in quality_breakdown.get("checks", {}).values():
                if isinstance(check, dict):
                    check["earned"] = 0
        components = [
            score.get("context") or 0,
            score.get("research") or 0,
            score.get("qa") or 0,
            score.get("quality") or 0,
            score.get("docs") or 0,
        ]
        score["final"] = sum(components)
    return score


def unique_run_dir(tool_root: Path, timestamp: str, run_idx: int) -> Path:
    base_name = f"{timestamp}_run{run_idx:02d}"
    run_dir = tool_root / base_name
    if not run_dir.exists():
        return run_dir
    suffix = 1
    while True:
        candidate = tool_root / f"{base_name}_{suffix:02d}"
        if not candidate.exists():
            return candidate
        suffix += 1


def prepare_runs(base_dir: Path, output_root: Path, tools: list, runs: int) -> list:
    runs_root = output_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    created = []
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for tool in tools:
        tool_root = runs_root / tool
        tool_root.mkdir(exist_ok=True)
        for idx in range(1, runs + 1):
            run_dir = unique_run_dir(tool_root, timestamp, idx)
            run_dir.mkdir()
            for filename in TEMPLATE_FILES:
                src = base_dir / filename
                dst = run_dir / filename
                shutil.copy2(src, dst)
            created.append(run_dir)
    return created


def check_completion(run_dir: Path) -> tuple[bool, list]:
    missing = []
    for name in REQUIRED_OUTPUTS:
        path = run_dir / name
        if name == "tests":
            if not path.exists() or not any(path.rglob("*.py")):
                missing.append(name)
        elif not path.exists():
            missing.append(name)
    return len(missing) == 0, missing


def load_telemetry(run_dir: Path) -> dict:
    telemetry_path = run_dir / "telemetry.json"
    if not telemetry_path.exists():
        return {}
    try:
        return json.loads(telemetry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def score_runs(
    base_dir: Path,
    output_root: Path,
    tools: list,
    out_csv: Path,
    out_json: Path,
    rescore: bool,
) -> list:
    runs_root = output_root / "runs"
    if not runs_root.exists():
        raise FileNotFoundError("No runs directory found. Run prepare first.")

    run_dirs = []
    for tool in tools:
        tool_root = runs_root / tool
        if not tool_root.exists():
            continue
        for path in sorted(tool_root.glob("*/")):
            if (path / "judge.py").exists():
                run_dirs.append(path)

    rows = []
    for run_dir in run_dirs:
        marker = run_dir / SCORED_MARKER
        if marker.exists() and not rescore:
            continue

        complete, missing = check_completion(run_dir)
        output = ""
        proc = None
        score = {
            "context": None,
            "research": None,
            "qa": None,
            "quality": None,
            "docs": None,
            "final": None,
            "ruff_errors": None,
        }

        if complete:
            proc = subprocess.run(
                [sys.executable, "judge.py"],
                cwd=str(run_dir),
                capture_output=True,
                text=True,
            )
            output = proc.stdout + proc.stderr
            judge_payload = load_judge_json(run_dir)
            if judge_payload:
                score = {
                    "context": judge_payload.get("context"),
                    "research": judge_payload.get("research"),
                    "qa": judge_payload.get("qa"),
                    "quality": judge_payload.get("quality"),
                    "docs": judge_payload.get("docs"),
                    "final": judge_payload.get("score"),
                    "ruff_errors": judge_payload.get("ruff_errors"),
                    "quality_breakdown": judge_payload.get("quality_breakdown"),
                }
                score = apply_pytest_cap(score, judge_payload)
            else:
                score = parse_score(output)
        else:
            output = f"INCOMPLETE RUN: missing {', '.join(missing)}\n"

        (run_dir / "judge.log").write_text(output, encoding="utf-8")
        if complete:
            marker.write_text(
                dt.datetime.now().isoformat(timespec="seconds"),
                encoding="utf-8",
            )
        telemetry = load_telemetry(run_dir)
        quality_breakdown = score.get("quality_breakdown") or {}
        checks = quality_breakdown.get("checks") or {}
        row = {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "tool": run_dir.parent.name,
            "run_id": run_dir.name,
            "complete": complete,
            "missing": ",".join(missing),
            "score": score["final"],
            "context": score["context"],
            "research": score["research"],
            "qa": score["qa"],
            "quality": score["quality"],
            "quality_ruff": checks.get("ruff", {}).get("earned"),
            "quality_modernization": checks.get("modernization", {}).get("earned"),
            "quality_complexity": checks.get("complexity", {}).get("earned"),
            "quality_pylint": checks.get("pylint", {}).get("earned"),
            "quality_dead_code": checks.get("dead_code", {}).get("earned"),
            "quality_duplication": checks.get("duplication", {}).get("earned"),
            "quality_type_check": checks.get("type_check", {}).get("earned"),
            "quality_security": checks.get("security", {}).get("earned"),
            "quality_coverage": checks.get("coverage", {}).get("earned"),
            "quality_docstyle": checks.get("docstyle", {}).get("earned"),
            "quality_semgrep": checks.get("semgrep", {}).get("earned"),
            "quality_pip_audit": checks.get("pip_audit", {}).get("earned"),
            "quality_codespell": checks.get("codespell", {}).get("earned"),
            "quality_ruff_format": checks.get("ruff_format", {}).get("earned"),
            "quality_isort": checks.get("isort", {}).get("earned"),
            "quality_license": checks.get("license", {}).get("earned"),
            "quality_details": (
                json.dumps(quality_breakdown) if quality_breakdown else None
            ),
            "docs": score["docs"],
            "ruff_errors": score["ruff_errors"],
            "judge_exit": proc.returncode if proc else -1,
            "model": telemetry.get("model"),
            "variant": telemetry.get("variant"),
            "session_id": telemetry.get("session_id"),
            "tokens_prompt": telemetry.get("tokens_prompt"),
            "tokens_completion": telemetry.get("tokens_completion"),
            "tokens_total": telemetry.get("tokens_total"),
            "duration_ms": telemetry.get("duration_ms"),
            "phase_timeline": (
                json.dumps(telemetry.get("phase_timeline"))
                if telemetry.get("phase_timeline")
                else None
            ),
            "phase_durations_ms": (
                json.dumps(telemetry.get("phase_durations_ms"))
                if telemetry.get("phase_durations_ms")
                else None
            ),
            "tools_used": (
                json.dumps(telemetry.get("tools_used"))
                if telemetry.get("tools_used")
                else None
            ),
            "subagents": (
                json.dumps(telemetry.get("subagents"))
                if telemetry.get("subagents")
                else None
            ),
            "skills_used": (
                json.dumps(telemetry.get("skills_used"))
                if telemetry.get("skills_used")
                else None
            ),
            "slash_commands": (
                json.dumps(telemetry.get("slash_commands"))
                if telemetry.get("slash_commands")
                else None
            ),
            "telemetry_json": json.dumps(telemetry) if telemetry else None,
        }
        rows.append(row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    ensure_csv_schema(out_csv)
    with out_csv.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerows(rows)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    out_json_array = json_array_path(out_json)
    write_json_array(out_json, out_json_array)

    return rows


def ensure_csv_schema(out_csv: Path) -> None:
    if not out_csv.exists():
        with out_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
        return

    with out_csv.open(newline="") as f:
        reader = csv.reader(f)
        existing_header = next(reader, [])

    if existing_header == CSV_FIELDS:
        return

    rows = []
    with out_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            normalized = {field: row.get(field) for field in CSV_FIELDS}
            writer.writerow(normalized)


def json_array_path(out_jsonl: Path) -> Path:
    if out_jsonl.suffix == ".jsonl":
        return out_jsonl.with_suffix(".json")
    return out_jsonl.with_suffix(out_jsonl.suffix + ".json")


def write_json_array(out_jsonl: Path, out_json: Path) -> None:
    if not out_jsonl.exists():
        return
    rows = []
    with out_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare Titan Protocol runs and score results.",
    )
    parser.add_argument(
        "--tools",
        default=",".join(DEFAULT_TOOLS),
        help="Comma-separated tool names (default: ampcode,augment,opencode)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs per tool when preparing.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="(Deprecated) CSV path for scoring output. Use --out-csv.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for runs and results (default: ~/titan_protocol_runs).",
    )
    parser.add_argument(
        "--out-csv",
        default="results.csv",
        help="CSV path for scoring output (relative to --output-root unless absolute).",
    )
    parser.add_argument(
        "--out-json",
        default="results.jsonl",
        help=(
            "JSONL path for scoring output (relative to --output-root unless absolute)."
        ),
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Create fresh run directories for each tool.",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="Run judge.py in each run directory and append to CSV.",
    )
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Re-score runs even if they were scored before.",
    )

    args = parser.parse_args()
    tools = [t.strip() for t in args.tools.split(",") if t.strip()]
    if not tools:
        raise SystemExit("No tools specified.")

    base_dir = Path(__file__).resolve().parent
    output_root = Path(args.output_root).expanduser().resolve()
    if args.out:
        out_csv = Path(args.out).expanduser()
        if not out_csv.is_absolute():
            out_csv = output_root / out_csv
    else:
        out_csv = Path(args.out_csv).expanduser()
        if not out_csv.is_absolute():
            out_csv = output_root / out_csv
    out_json = Path(args.out_json).expanduser()
    if not out_json.is_absolute():
        out_json = output_root / out_json

    if not args.prepare and not args.score:
        parser.print_help()
        return

    if args.prepare:
        created = prepare_runs(base_dir, output_root, tools, args.runs)
        print(f"Prepared {len(created)} run directories under {output_root / 'runs'}")

    if args.score:
        rows = score_runs(
            base_dir,
            output_root,
            tools,
            out_csv,
            out_json,
            rescore=args.rescore,
        )
        print(f"Scored {len(rows)} runs. Appended to {out_csv}")


if __name__ == "__main__":
    main()
