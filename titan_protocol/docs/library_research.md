# Library Research Notes

## Telemetry / instrumentation
**Recommendation:** OpenTelemetry (OTel)
- Python packages: `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation`
- Rationale: vendor-neutral standard, OTLP export, broad ecosystem support.

## Phase timing capture (for PHASE: PLAN/DEV/QA markers)
**Options reviewed:**
- **otel-cli** (OpenTelemetry CLI) to emit spans/events from shell scripts. Requires an OTLP endpoint/collector but provides standard traces. citeturn0search0
- **opentelemetry-cli** (otel) as an alternative OTLP CLI for spans. citeturn0search1
- **moreutils `ts`** to timestamp each stdout line in pipelines. Simple but external package/tool. citeturn0search2
- **Pendulum / Arrow** Python datetime libraries for timezone-aware ISO-8601 timestamps. citeturn1search3turn1search2

**Decision:** Use **Pendulum** in a small helper (`phase_log.py`) to timestamp `PHASE:` markers into `phases.log`.
- Rationale: minimal setup, no external collector requirement, clean UTC ISO-8601 timestamps, modern API.
- Future option: upgrade to otel-cli when we want OTLP traces end-to-end.

## Functional verification / timeouts
**Considered:** `pytest-timeout`
- Pros: simple per-test timeout configuration.
- Cons: adds dependency across all runs; subprocess timeouts are sufficient for harness execution.
- Decision: use `subprocess.run(..., timeout=...)` to avoid extra dependencies.

## Existing dependencies already in use
These are already used in the harness. Re-evaluate before replacing:
- CLI: `typer`
- PDF generation: `reportlab`
- Charts: `matplotlib`
- Slide export: `python-pptx`

## Static analysis / linting (scored)
**Selected tools:**
- `ruff` (lint + modernization + complexity selectors)
- `pylint` (general linting)
- `xenon` (complexity gating)
- `vulture` (dead code detection)
- `jscpd` (duplication detection)
- `mypy` + `pyright` (type checking)
- `bandit` (security scanning)
- `pytest-cov` (coverage)
- `pydocstyle` (docstring style)
- `semgrep` (static security rules)
- `pip-audit` (dependency vulnerability scan)
- `codespell` (spelling checks)
- `isort` (import ordering)
- `pip-licenses` (license inventory)

**Rationale:** broad coverage across modernization, complexity, duplication, dead code,
type safety, security, coverage, and documentation expectations.

**Note:** `jscpd` installs via npm; the judge attempts auto-install when npm is available.

## Notes
- Update this file whenever new functionality introduces a new dependency category.
