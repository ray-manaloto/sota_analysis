#!/usr/bin/env python3
"""Capture PHASE markers from stdin and write a phase log for telemetry."""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PHASE_REGEX = re.compile(r"\bPHASE:\s*([A-Z][A-Z0-9_-]*)", re.IGNORECASE)


def ensure_pendulum():
    try:
        import pendulum  # type: ignore
    except ModuleNotFoundError:
        if os.getenv("TITAN_NO_INSTALL") == "1":
            raise SystemExit("pendulum not installed and TITAN_NO_INSTALL=1")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pendulum"])
        import pendulum  # type: ignore
    return pendulum


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pass-through logger that records PHASE markers with timestamps.",
    )
    parser.add_argument(
        "--phase-log",
        required=True,
        help="Path to append phase log lines: <iso_timestamp>,<PHASE>",
    )
    args = parser.parse_args()

    pendulum = ensure_pendulum()
    log_path = Path(args.phase_log).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    with log_path.open("a", encoding="utf-8") as log:
        for line in sys.stdin:
            sys.stdout.write(line)
            match = PHASE_REGEX.search(line)
            if match:
                phase = match.group(1).upper()
                timestamp = pendulum.now("UTC").to_iso8601_string()
                log.write(f"{timestamp},{phase}\n")
                log.flush()


if __name__ == "__main__":
    main()
