# Titan Protocol Test Kit

This folder is the ready-to-run setup for the "Project Log-Titan" evaluation.

## How to run
1. Point your agent/tool at this folder.
2. Provide `TITAN_SPEC.md` as the spec to implement.
3. After the agent finishes, run the judge:

```bash
python judge.py
```

By default, `judge.py` will attempt to install missing tools (e.g., `ruff`).
To disable auto-install, set:

```bash
export TITAN_NO_INSTALL=1
```

## Batch runner
Prepare fresh run directories per tool, then score them into a CSV.

```bash
# Prepare 1 run per tool (ampcode, augment, opencode)
python run_test.py --prepare --runs 1

# After agents finish, score all runs (writes CSV + JSONL)
python run_test.py --score

# Re-score previously scored runs
python run_test.py --score --rescore --out-csv artifacts/results.csv

# Create a summary report + chart from results.csv
python summarize_results.py --input artifacts/results.csv --out-md artifacts/summary.md --out-chart artifacts/summary.png

# Skip auto-install if you want to manage dependencies yourself
python summarize_results.py --no-install

# Export PPTX for Google Slides import
python export_slides.py --input presentation.md --out artifacts/presentation.pptx

# Skip auto-install if you want to manage dependencies yourself
python export_slides.py --no-install
```

## Included files
- `legacy_crypto.py`: Control file that must be used for hashing.
- `TITAN_SPEC.md`: The full requirements and traps.
- `judge.py`: Automated scoring script.
- `run_test.py`: Runner to create run directories and log scores to CSV.
- `summarize_results.py`: Generates a summary report and optional chart.
- `collect_telemetry.py`: Extracts telemetry into `telemetry.json` for a run.
- `presentation.md`: Marp slide deck for team review.
- `export_slides.py`: Exports `presentation.md` to PPTX (Google Slides import).

## Documentation maintenance
- Update this README whenever you change scripts, flags, or output formats.

## Judge behavior notes
- The judge scans only `tests/*.py` and skips binary files.

## Artifacts layout
All generated files live under `artifacts/`:
- `artifacts/runs/<tool>/<run_id>/` (full run outputs)
- `artifacts/results.csv` and `artifacts/results.jsonl` (structured results)
- `artifacts/summary.md` and `artifacts/summary.png`

## Results format
- **CSV** for quick spreadsheet review and charts.
- **JSONL** for structured telemetry and automation.

## Telemetry (recommended)
Capture as much telemetry as possible per run and store it in `telemetry.json`.

**Option A: from opencode JSON events**
```bash
opencode run --format json "Read TITAN_SPEC.md. Implement the code sequentially." \\
  | tee artifacts/runs/opencode/<run_id>/opencode_events.jsonl

python collect_telemetry.py \\
  --run-dir artifacts/runs/opencode/<run_id> \\
  --events artifacts/runs/opencode/<run_id>/opencode_events.jsonl \\
  --model <provider/model> \\
  --variant <variant>
```

**Option B: from opencode export**
```bash
python collect_telemetry.py \\
  --run-dir artifacts/runs/opencode/<run_id> \\
  --export --session <SESSION_ID> \\
  --model <provider/model> \\
  --variant <variant>
```

Telemetry fields captured (if present):
- models used
- subagents
- tools used
- skills used
- slash commands
- token usage

## Expected outputs from the agent
- `ingest.py`, `report.py`, `main.py`
- `tests/` with mocked `legacy_crypto`
- `README.md` with a Mermaid diagram
- `titan.db` created at runtime
