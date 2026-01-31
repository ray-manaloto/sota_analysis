# Library Research Notes

## Telemetry / instrumentation
**Recommendation:** OpenTelemetry (OTel)
- Python packages: `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation`
- Rationale: vendor-neutral standard, OTLP export, broad ecosystem support.

## Phase timing capture (for PHASE: PLAN/DEV/QA markers)
**Options reviewed:**
- **otel-cli** (OpenTelemetry CLI) to emit spans/events from shell scripts. Requires an OTLP endpoint/collector but provides standard traces.
- **opentelemetry-cli** (otel) as an alternative OTLP CLI for spans.
- **moreutils `ts`** to timestamp each stdout line in pipelines. Simple but external package/tool.
- **Pendulum / Arrow** Python datetime libraries for timezone-aware ISO-8601 timestamps.

**Decision:** Use **Pendulum** in a small helper (`phase_log.py`) to timestamp `PHASE:` markers into `phases.log`.
- Rationale: minimal setup, no external collector requirement, clean UTC ISO-8601 timestamps, modern API.
- Future option: upgrade to otel-cli when we want OTLP traces end-to-end.

## OpenLIT (LLM observability)
**Options reviewed:**
- **OpenLIT SDK** (`pip install openlit`) with `openlit.init(...)` for OpenTelemetry-native LLM tracing.
- **OpenTelemetry env vars** (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`) to route telemetry to OpenLIT without code changes.

**Decision:** Add **OpenLIT env wiring** to the harness runner (`run_suite.sh`) so any tool that emits OTEL data can export to OpenLIT.
- Rationale: minimal changes, works across tools that already support OTEL, and avoids embedding OpenLIT SDK inside the harness.

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
