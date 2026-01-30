# AGENTS.md

## Project context
This repo contains the Log-Titan test harness under `titan_protocol/`. Treat it as a test kit: keep harness code clean, reproducible, and auditable.

## Output location (anti-cheat)
All generated runs and results must live **outside** the repo.
- Default output root: `~/titan_protocol_runs`
- The harness uses `--output-root` to control where runs/results are stored.

## Required workflow (modern libraries first)
Before writing or editing code:
1. **Research modern third-party libraries** relevant to the change (telemetry, CLI, reporting, charts, etc.).
2. **Document findings and choice** in `titan_protocol/docs/library_research.md`.
3. Only then proceed with implementation.

## Telemetry guidance
- Prefer **OpenTelemetry** for telemetry/instrumentation.
- Store run telemetry in `<run_dir>/telemetry.json` using `titan_protocol/collect_telemetry.py`.
- Any tool can emit JSON events to `<run_dir>/events.jsonl` for extraction.

## Running the harness
- Prepare runs: `python titan_protocol/run_test.py --prepare --runs 1 --output-root ~/titan_protocol_runs`
- Score runs: `python titan_protocol/run_test.py --score --output-root ~/titan_protocol_runs`
- Summarize: `python titan_protocol/summarize_results.py --input ~/titan_protocol_runs/results.csv --out-md ~/titan_protocol_runs/summary.md --out-chart ~/titan_protocol_runs/summary.png`

## External review (Gemini CLI)
Run Gemini headless to grade harness correctness and thoroughness. Store review output under the output root:
- Enable preview models in `.gemini/settings.json` and use the preview model ID.
- `cat prompt.txt | gemini --model gemini-3-pro-preview > ~/titan_protocol_runs/reviews/gemini_review.md`

Telemetry is configured via `.gemini/settings.json` to write to a local log file under `~/titan_protocol_runs/reviews/`.

## Documentation maintenance
If you change scripts, flags, output formats, or workflow assumptions, update:
- `titan_protocol/README.md`
- `titan_protocol/docs/library_research.md` (if library choices change)
