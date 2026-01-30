#!/usr/bin/env python3
"""Summarize Titan Protocol results into a Markdown report and optional chart."""

import argparse
import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_rows(path: Path):
    rows = []
    if path.suffix in {".jsonl", ".json"}:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    else:
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


def summarize(rows):
    tools = {}
    for row in rows:
        tool = row.get("tool", "unknown")
        tools.setdefault(tool, []).append(row)

    summary = {}
    for tool, items in tools.items():
        scores = [parse_int(r.get("score")) for r in items]
        scores = [s for s in scores if s is not None]
        complete_count = sum(
            1 for r in items if str(r.get("complete", "")).lower() == "true"
        )
        total = len(items)

        def avg(field):
            vals = [parse_int(r.get(field)) for r in items]
            vals = [v for v in vals if v is not None]
            return round(statistics.mean(vals), 2) if vals else None

        summary[tool] = {
            "runs": total,
            "complete": complete_count,
            "avg_score": round(statistics.mean(scores), 2) if scores else None,
            "min_score": min(scores) if scores else None,
            "max_score": max(scores) if scores else None,
            "context": avg("context"),
            "research": avg("research"),
            "qa": avg("qa"),
            "quality": avg("quality"),
            "docs": avg("docs"),
        }
    return summary


def write_markdown(summary, out_path: Path, source_path: Path):
    lines = []
    lines.append("# Titan Protocol Summary")
    lines.append("")
    lines.append(f"Source: `{source_path}`")
    lines.append("")
    lines.append("## Overall Scores")
    lines.append("")
    lines.append("| Tool | Runs | Complete | Avg | Min | Max |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for tool, data in sorted(summary.items()):
        lines.append(
            "| {tool} | {runs} | {complete} | {avg} | {min} | {max} |".format(
                tool=tool,
                runs=data["runs"],
                complete=data["complete"],
                avg=data["avg_score"],
                min=data["min_score"],
                max=data["max_score"],
            )
        )

    lines.append("")
    lines.append("## Trap Averages")
    lines.append("")
    lines.append("| Tool | Context | Research | QA | Lint | Docs |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for tool, data in sorted(summary.items()):
        lines.append(
            "| {tool} | {context} | {research} | {qa} | {quality} | {docs} |".format(
                tool=tool,
                context=data["context"],
                research=data["research"],
                qa=data["qa"],
                quality=data["quality"],
                docs=data["docs"],
            )
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_package(import_name: str, package: str, allow_install: bool) -> bool:
    try:
        __import__(import_name)
        return True
    except ImportError:
        if not allow_install:
            return False
        print(f"Missing dependency: {package}. Attempting install...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            return False
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False


def write_chart(summary, out_path: Path, allow_install: bool):
    if not ensure_package("matplotlib.pyplot", "matplotlib", allow_install):
        return False

    import matplotlib.pyplot as plt

    tools = sorted(summary.keys())
    avgs = [summary[t]["avg_score"] or 0 for t in tools]

    plt.figure(figsize=(8, 4.5))
    plt.bar(tools, avgs, color="#4c78a8")
    plt.ylim(0, 100)
    plt.ylabel("Average Score")
    plt.title("Titan Protocol Results")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    return True


def main():
    parser = argparse.ArgumentParser(description="Summarize Titan Protocol results.")
    parser.add_argument(
        "--input",
        default="artifacts/results.csv",
        help="Results input path (CSV or JSONL).",
    )
    parser.add_argument(
        "--out-md",
        default="artifacts/summary.md",
        help="Markdown summary output.",
    )
    parser.add_argument(
        "--out-chart",
        default="artifacts/summary.png",
        help="Chart output (PNG).",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Disable auto-install of missing dependencies.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / args.input
    out_md = base_dir / args.out_md
    out_chart = base_dir / args.out_chart

    if not input_path.exists():
        raise SystemExit(f"Missing results file: {input_path}")

    rows = load_rows(input_path)
    summary = summarize(rows)
    write_markdown(summary, out_md, input_path)
    chart_written = write_chart(summary, out_chart, allow_install=not args.no_install)

    print(f"Wrote summary: {out_md}")
    if chart_written:
        print(f"Wrote chart: {out_chart}")
    else:
        print("Matplotlib not available; skipped chart.")


if __name__ == "__main__":
    main()
