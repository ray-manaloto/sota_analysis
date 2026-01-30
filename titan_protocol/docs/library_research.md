# Library Research Notes

## Telemetry / instrumentation
**Recommendation:** OpenTelemetry (OTel)
- Python packages: `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation`
- Rationale: vendor-neutral standard, OTLP export, broad ecosystem support.

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
