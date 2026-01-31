# Titan Protocol Automation Runbook

This document captures the exact steps used in the latest evaluation runs and the gaps that required manual intervention. It is intended as the source of truth for automation.

## Scope
- Tools: AmpCode (amp), Augment (auggie), OpenCode (opencode)
- Output root: `~/titan_protocol_runs`
- Runs used for latest report:
  - AmpCode: `runs/ampcode/20260130_085528_234187_run01`
  - Augment: `runs/augment/20260130_094554_552071_run01`
  - OpenCode: `runs/opencode/20260130_083642_577625_run01`

## Pre-reqs
- Python 3.11+
- Node/npm (for some linters and optional reporting)
- Tools installed:
  - `amp`
  - `auggie`
  - `opencode`
- Tokens available:
  - `AUGMENT_SESSION_AUTH` for Auggie non-interactive runs
- Optional env vars:
  - `TITAN_NO_INSTALL=1` to skip auto-install during judge/summary/export.
  - Note: `phase_log.py` auto-installs `pendulum` unless `TITAN_NO_INSTALL=1` is set.
- Optional OpenLIT env vars (OTLP export):
  - `OPENLIT_ENDPOINT` (e.g., `http://localhost:4318`)
  - `OPENLIT_HEADERS` (e.g., `Authorization=...`)
  - `OPENLIT_SERVICE_NAME` / `OPENLIT_ENVIRONMENT` / `OPENLIT_PROTOCOL`
  - `OPENLIT_ENABLE=1` to force wrapper usage
  - `OPENLIT_TRACE_TOOLS=1` to wrap Amp/Auggie/OpenCode runs in OTEL spans via `otel_span.py`.
  - Note: `run_suite.sh` will auto-install `openlit` unless `TITAN_NO_INSTALL=1`.
  - When enabled, `run_suite.sh` wraps Python commands with `openlit-instrument` and wires OTEL_* env vars.
- Authentication check:
  - OpenCode: ensure provider credentials are configured (env vars/ADC/etc). Automation should fail fast if a smoke run returns non-zero.
  - Augment: `AUGMENT_SESSION_AUTH` must be present for non-interactive runs.
  - OpenCode auth list: `opencode auth list` should succeed (script enforces this).

## Pre-flight checks (automation)
```bash
set -e
command -v amp >/dev/null || { echo "amp missing"; exit 1; }
command -v auggie >/dev/null || { echo "auggie missing"; exit 1; }
command -v opencode >/dev/null || { echo "opencode missing"; exit 1; }
python3 -c 'import sys; assert sys.version_info[:2] >= (3,11)' || { echo "Python 3.11+ required"; exit 1; }
node --version >/dev/null || { echo "node missing"; exit 1; }
npm --version >/dev/null || { echo "npm missing"; exit 1; }
```

## Automation Checklist (Ideal)
1. Prepare run directories (outside repo)
   ```bash
   python titan_protocol/run_test.py --prepare --runs 1 --output-root ~/titan_protocol_runs
   ```
   Use `--tools` to target specific tools when debugging:
   ```bash
   python titan_protocol/run_test.py --prepare --runs 1 --tools ampcode --output-root ~/titan_protocol_runs
   ```
2. Run each tool in its run directory with tool-specific prompts.
3. Ensure tests pass and `judge.py` passes in each run directory:
   ```bash
   python3 -m pytest -q && python3 judge.py
   ```
   (exit code 0 required to continue)
4. Generate telemetry for each run.
5. Score runs and generate summary report and slides.

## Recommended Commands (Automation-Ready)
`run_suite.sh` is the primary and preferred automation entrypoint (source of truth):
```bash
./titan_protocol/run_suite.sh --output-root ~/titan_protocol_runs --tools ampcode,augment,opencode --runs 1 --clean --score --report
```

If you need to debug individual steps, use `run_test.py --prepare` and run each tool manually in the created run directory.
Note: `run_suite.sh` includes the OpenCode self-healing loop (`opencode loop ... --limit 5`).

## Historical: Actual Steps Used (Latest Run)
Historical reference only. If you use `run_suite.sh`, the prompts already include the `legacy_crypto` import guidance and `SystemExit(2)` instruction.

### 1) Prepare run dirs
```bash
python titan_protocol/run_test.py --prepare --runs 1 --output-root ~/titan_protocol_runs
```

### 2) AmpCode (amp) run
Command used:
```bash
cd ~/titan_protocol_runs/runs/ampcode/20260130_085528_234187_run01
amp --dangerously-allow-all -x "Read TITAN_SPEC.md. Work ONLY in this directory. 1. Create an AGENTS.md configuration. Assign @IngestAgent to ingest.py and @ReportAgent to report.py. 2. Once configured, execute the implementation of both modules in parallel."
```
Follow-up command used:
```bash
amp --dangerously-allow-all -x "Continue from current state. Implement main.py CLI (argparse or typer), add tests/ with pytest that MOCK legacy_crypto, update README.md with a Mermaid diagram. Run pytest and fix failures, then run judge.py."
```

**Manual intervention required:**
- Tests failed because `legacy_crypto.secure_hash` was patched, but `ingest.py` imported `secure_hash` directly.
- Fix applied manually:
  - Changed `from legacy_crypto import secure_hash` to `import legacy_crypto` and used `legacy_crypto.secure_hash(...)`.
- Then ran:
  ```bash
  python3 -m pytest -q
  python3 judge.py
  ```

Telemetry written manually (no token/model data available):
```json
{"tools_used": ["amp"], "subagents": ["IngestAgent", "ReportAgent"], "tokens_total": null}
```

### 3) Augment (auggie) run
Command used:
```bash
cd ~/titan_protocol_runs/runs/augment/20260130_094554_552071_run01
AUGMENT_DISABLE_AUTO_UPDATE=1 \
AUGMENT_SESSION_AUTH=$AUGMENT_SESSION_AUTH \
auggie --print --quiet "You are running the Titan Protocol evaluation. Work ONLY in this directory..."
```

**Manual intervention required:**
- Tests failed because `main.py` printed help but did not exit with non-zero code.
- Fix applied manually:
  - Added `raise SystemExit(2)` after `parser.print_help()`.
- Then ran:
  ```bash
  python3 -m pytest -q
  python3 judge.py
  ```

Telemetry written manually (no token/model data available):
```json
{"tools_used": ["auggie"], "tokens_total": null}
```

### 4) OpenCode (opencode) run
Command used:
```bash
cd ~/titan_protocol_runs/runs/opencode/20260130_083642_577625_run01
opencode run --format json "Read TITAN_SPEC.md. Implement the code sequentially." \
  | tee opencode_events.jsonl
```
Then ran:
```bash
python3 -m pytest -q
python3 judge.py
```
Telemetry collected from events:
```bash
python titan_protocol/collect_telemetry.py \
  --run-dir ~/titan_protocol_runs/runs/opencode/20260130_083642_577625_run01 \
  --events ~/titan_protocol_runs/runs/opencode/20260130_083642_577625_run01/opencode_events.jsonl
```

## Known Automation Gaps
- AmpCode and Augment runs do **not** emit structured events by default.
- Token/model data for Amp/Auggie is missing unless the tools expose it via CLI or events.
- Phase timing (plan/dev/qa) requires tools to emit `PHASE:` markers; `run_suite.sh` captures them into `phases.log` for Amp/Auggie.
- If a tool does not emit markers, `phases.log` will be empty and no phase timing will be recorded.

## How to Remove Manual Steps
- AmpCode: ensure tests patch the correct import or enforce `import legacy_crypto` in prompt.
- Augment: enforce `SystemExit` on help usage in prompt or add a lint/test gate.
- Add pre-flight linters or a QA loop step after each tool run to fix failures automatically.
- For fairness, avoid auto-fixing agent output. If a run violates the import or exit-code rules, record the failure and continue to the next run.
  - If you use `run_suite.sh`, the prompt already includes the `legacy_crypto` import requirement and `SystemExit(2)` instruction. Treat manual fixes in the history section as reference only.

## Clean runs
For automated clean runs, prefer the script flag:
```bash
./titan_protocol/run_suite.sh --clean --score --report
```

Manual alternative (if you are not using the wrapper):
```bash
mv ~/titan_protocol_runs ~/titan_protocol_runs_$(date +%Y%m%d_%H%M%S)
```

## Phase Timing (Optional)
To capture plan/dev/qa timing, include phase markers in prompts:
```
PHASE: PLAN
PHASE: DEV
PHASE: QA
```
If you can log phases to a file, write lines as:
```
2026-01-30T10:00:00Z,PLAN
2026-01-30T10:05:00Z,DEV
2026-01-30T10:15:00Z,QA
```
Then collect:
```bash
python titan_protocol/collect_telemetry.py --run-dir <run_dir> --phase-log phases.log
```

Note: `collect_telemetry.py` auto-detects `opencode_events.jsonl` (or `events.jsonl`) in the run directory if `--events` is omitted.
`run_suite.sh` uses `phase_log.py` to record `PHASE:` markers from Amp/Auggie output into `phases.log`.

## Post-Run Scoring + Reports
If you used `run_suite.sh --report`, these steps are automatic.

```bash
python titan_protocol/run_test.py --score --rescore --output-root ~/titan_protocol_runs
python titan_protocol/summarize_results.py --input ~/titan_protocol_runs/results.csv \
  --out-md ~/titan_protocol_runs/summary.md --out-chart ~/titan_protocol_runs/summary.png
```

## Slides Export
If you used `run_suite.sh --report`, this step is automatic.
```bash
python titan_protocol/export_slides.py --input presentation.md --out ~/titan_protocol_runs/presentation.pptx
```

## Latest-Run-Only Summary
This is optional; `run_suite.sh --report` does not run this step.
```bash
python - <<'PY'
import csv, datetime as dt
from pathlib import Path

def parse_time(value):
    try:
        return dt.datetime.fromisoformat(value).timestamp()
    except Exception:
        return 0.0

input_path = Path('~/titan_protocol_runs/results.csv').expanduser()
rows = list(csv.DictReader(input_path.open()))
latest = {}
for row in rows:
    tool = row.get('tool') or 'unknown'
    ts = parse_time(row.get('timestamp') or '')
    if tool not in latest or ts > latest[tool][0]:
        latest[tool] = (ts, row)

out = Path('~/titan_protocol_runs/results_latest.csv').expanduser()
with out.open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    for _, row in sorted(latest.values(), key=lambda x: x[1].get('tool', '')):
        writer.writerow(row)

print(out)
PY

python titan_protocol/summarize_results.py --input ~/titan_protocol_runs/results_latest.csv \
  --out-md ~/titan_protocol_runs/summary_latest.md --out-chart ~/titan_protocol_runs/summary_latest.png
```
