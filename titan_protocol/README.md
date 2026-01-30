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
Prepare fresh run directories per tool outside this repo (default: `~/titan_protocol_runs`), then score them into a CSV.
Use `--output-root` to override the location.

```bash
# Prepare 1 run per tool (ampcode, augment, opencode)
python run_test.py --prepare --runs 1

# After agents finish, score all runs (writes CSV + JSONL + JSON)
python run_test.py --score

# Re-score previously scored runs
python run_test.py --score --rescore --out-csv ~/titan_protocol_runs/results.csv

# Create a summary report + chart from results.csv
python summarize_results.py --input ~/titan_protocol_runs/results.csv --out-md ~/titan_protocol_runs/summary.md --out-chart ~/titan_protocol_runs/summary.png

# Skip auto-install if you want to manage dependencies yourself
python summarize_results.py --no-install

# Export PPTX for Google Slides import
python export_slides.py --input presentation.md --out ~/titan_protocol_runs/presentation.pptx

# Skip auto-install if you want to manage dependencies yourself
python export_slides.py --no-install
```

## Included files
- `legacy_crypto.py`: Control file that must be used for hashing.
- `TITAN_SPEC.md`: The full requirements and traps.
- `judge.py`: Automated scoring script.
- `ruff.toml`: Lint config applied by the judge (copied into each run).
- `.pylintrc`, `mypy.ini`, `pyrightconfig.json`, `.pydocstyle`, `bandit.yaml`, `.jscpd.json`: Static analysis configs.
- `.codespellrc`, `.isort.cfg`, `.semgrepignore`: Additional analysis configs.
- `run_test.py`: Runner to create run directories and log scores to CSV.
- `summarize_results.py`: Generates a summary report and optional chart.
- `collect_telemetry.py`: Extracts telemetry into `telemetry.json` for a run.
- `presentation.md`: Marp slide deck for team review.
- `export_slides.py`: Exports `presentation.md` to PPTX (Google Slides import).
- `docs/library_research.md`: Notes on preferred modern libraries (telemetry, etc.).

## Documentation maintenance
- Update this README whenever you change scripts, flags, or output formats.

## Judge behavior notes
- Static analysis runs across the full run directory (including `judge.py`).
- The judge writes `judge.json` with structured scores and `quality_breakdown`.
- Set `TITAN_SKIP_EXEC=1` to skip pytest/smoke execution.
- If pytest fails, the quality score is capped to 0 in scoring output.
- `judge.py` itself is kept ruff-clean to avoid tainting lint checks in runs.

### Quality checks (scored)
- Ruff (lint)
- Ruff modernization (`UP`)
- Complexity (Ruff `C90` + Xenon gates)
- Pylint
- Dead code (Vulture)
- Duplication (jscpd)
- Type checking (mypy + pyright)
- Security (Bandit, high severity)
- Coverage (pytest-cov, >= 80%)
- Docstring style (pydocstyle D100-D107)
- Semgrep (security rules, severity ERROR)
- pip-audit (dependency vulnerability scan)
- Codespell (typos)
- Ruff format check
- isort (import ordering)
- License inventory (pip-licenses)

Notes:
- `jscpd` requires Node/npm for installation (auto-install is attempted).
- Semgrep auto-install uses pip and may be slower on first run.
- Quality weights are configured in `judge.py` and sum to 20 points.

## Artifacts layout
All generated files live under your output root (default `~/titan_protocol_runs`):
- `runs/<tool>/<run_id>/` (full run outputs)
- `results.csv`, `results.jsonl`, and `results.json` (structured results)
- `summary.md` and `summary.png`

## Results format
- **CSV** for quick spreadsheet review and charts.
- **JSONL** for structured telemetry and automation pipelines.
- **JSON** array for tools that prefer a single structured document.
- `quality_details` contains per-check scores and tool outputs.

## Telemetry (recommended)
Capture as much telemetry as possible per run and store it in `telemetry.json`.

**Option A: from opencode JSON events**
```bash
opencode run --format json "Read TITAN_SPEC.md. Implement the code sequentially." \\
  | tee ~/titan_protocol_runs/runs/opencode/<run_id>/opencode_events.jsonl

python collect_telemetry.py \\
  --run-dir ~/titan_protocol_runs/runs/opencode/<run_id> \\
  --events ~/titan_protocol_runs/runs/opencode/<run_id>/opencode_events.jsonl
```

**Option B: from opencode export**
```bash
python collect_telemetry.py \\
  --run-dir ~/titan_protocol_runs/runs/opencode/<run_id> \\
  --export --session <SESSION_ID>

**Other tools:** write JSON events to `events.jsonl` inside the run directory, then run
`python collect_telemetry.py --run-dir <run_dir>`. If `--events` is omitted,
`collect_telemetry.py` will autodetect `events.jsonl` or `opencode_events.jsonl`.
```

Telemetry fields captured (if present):
- session ID
- models used
- subagents
- tools used
- skills used
- slash commands
- token usage
- event count

## Gemini review (headless)
Gemini CLI is configured via `.gemini/settings.json` to enable preview models and local telemetry.
Run the headless review with the preview model ID:

```bash
cat prompt.txt | gemini --model gemini-3-pro-preview > ~/titan_protocol_runs/reviews/gemini_review.md
```

## Expected outputs from the agent
- `ingest.py`, `report.py`, `main.py`
- `tests/` with mocked `legacy_crypto`
- `README.md` with a Mermaid diagram
- `titan.db` created at runtime
