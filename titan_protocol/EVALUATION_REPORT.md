# Titan Protocol: AI Agent Evaluation Framework
## Technical Report for Software Development Teams

**Date:** January 30, 2026  
**Purpose:** Enable data-driven selection of AI coding assistants (AmpCode, Augment, OpenCode)  
**Audience:** Remote development team, engineering leadership

---

## 1. Executive Summary

### What Is Titan Protocol?

Titan Protocol is an **automated evaluation harness** that objectively scores AI coding assistants on a standardized task. It measures how well agents handle real-world software development challenges through 5 "trap" categories:

| Trap | Points | Tests |
|------|--------|-------|
| **Context** | 25 | Uses existing legacy code vs. rewriting |
| **Research** | 25 | Correctly implements external APIs (PDF watermark rotation) |
| **QA** | 20 | Properly mocks dependencies in tests |
| **Quality** | 20 | Passes 16 static analysis tools |
| **Documentation** | 10 | Includes architecture diagrams |

**Total: 100 points**

### Key Insight

> No single tool excels at everything. The protocol helps identify which tool to use for which task type.

---

## 2. How It Works

### The Task: "Project Log-Titan"

Agents are asked to build a CLI tool that:
1. Ingests server logs with hashing (must use provided `legacy_crypto.py`)
2. Generates PDF reports with 45-degree watermarks (must research ReportLab API)
3. Uses modular architecture (`ingest.py`, `report.py`, `main.py`)
4. Includes tests that mock the legacy dependency
5. Documents with Mermaid diagrams

### The Traps (Why They Matter)

```
+------------------+----------------------------------------+---------------------------+
| Trap             | What It Tests                          | Real-World Risk if Failed |
+------------------+----------------------------------------+---------------------------+
| Context Trap     | Does the agent read existing code?     | Breaks enterprise systems |
| Research Trap    | Does it verify API docs before coding? | Subtle bugs, wrong output |
| QA Trap          | Does it isolate tests properly?        | Flaky tests, regressions  |
| Quality Trap     | Does it write production-ready code?   | Tech debt, security holes |
| Docs Trap        | Does it document architecture?         | Onboarding friction       |
+------------------+----------------------------------------+---------------------------+
```

### Scoring Flow

```
                    +-----------------+
                    |  Prepare Runs   |
                    |  (run_test.py   |
                    |   --prepare)    |
                    +--------+--------+
                             |
              Creates isolated run directories
              with spec + legacy_crypto.py
                             |
                    +--------v--------+
                    |   Agent Runs    |
                    | (AmpCode/Augment|
                    |    /OpenCode)   |
                    +--------+--------+
                             |
              Agent generates: ingest.py,
              report.py, main.py, tests/, README.md
                             |
                    +--------v--------+
                    |   Score Runs    |
                    |  (run_test.py   |
                    |    --score)     |
                    +--------+--------+
                             |
              judge.py runs 16 static
              analysis tools automatically
                             |
                    +--------v--------+
                    |  Results Output |
                    | results.csv     |
                    | results.jsonl   |
                    | judge.json      |
                    +--------+--------+
                             |
                    +--------v--------+
                    | Generate Report |
                    | summarize_      |
                    | results.py      |
                    +-----------------+
```

---

## 3. Validation: Is This Setup Correct?

### Verification Checklist

| Check | Status | Evidence |
|-------|--------|----------|
| All dependencies installed | PASS | pip install completed with all 90+ packages |
| Tests passing | PASS | 8/8 tests pass (`pytest tests/ -v`) |
| Ruff linting clean | PASS | `ruff check .` returns "All checks passed!" |
| Output directory created | PASS | `~/titan_protocol_runs/` exists |
| Sample run prepared | PASS | `runs/opencode/20260130_*` directory created |
| Node.js tools available | PASS | jscpd installed globally via npm |

### Quality Analysis Tools (All 16 Verified)

```python
QUALITY_CHECKS = {
    "ruff": 2,           # Modern Python linter
    "modernization": 1,  # Python upgrade suggestions (ruff UP)
    "complexity": 1,     # Cyclomatic complexity (xenon + ruff C90)
    "pylint": 1,         # Traditional linting
    "dead_code": 1,      # Unused code detection (vulture)
    "duplication": 1,    # Copy-paste detection (jscpd)
    "type_check": 2,     # mypy + pyright
    "security": 2,       # bandit (high severity)
    "coverage": 2,       # pytest-cov (>= 80% required)
    "docstyle": 1,       # pydocstyle (D100-D107)
    "semgrep": 1,        # Security patterns
    "pip_audit": 1,      # Dependency vulnerabilities
    "codespell": 1,      # Spelling errors
    "ruff_format": 1,    # Code formatting
    "isort": 1,          # Import ordering
    "license": 1,        # License inventory
}
# Total: 20 points
```

### Test Coverage of Core Logic

| Tested Function | What It Validates |
|-----------------|-------------------|
| `has_rotate_45()` | Detects literal 45, variable assignment, rejects other angles |
| `mocks_legacy_crypto()` | Detects `patch()` calls, rejects comments |
| `score_titan()` | Full scoring pipeline, JSON output |
| `load_judge_json()` | Parses structured results |
| `apply_pytest_cap()` | Caps quality score if tests fail |

**Assessment:** The setup is **correctly configured** and ready for evaluation runs.

---

## 4. Pros and Cons

### Advantages

| Pro | Impact |
|-----|--------|
| **Objective scoring** | Removes "I think tool X is better" debates |
| **Reproducible** | Same spec/files/scoring for every run |
| **Comprehensive quality** | 16 tools catch issues humans miss |
| **Anti-cheat design** | Results stored outside repo (`~/titan_protocol_runs/`) |
| **Telemetry capture** | Tracks tokens, tools used, subagents invoked |
| **Multiple output formats** | CSV (spreadsheets), JSONL (pipelines), JSON (APIs) |
| **Trap-based design** | Tests real failure modes, not toy problems |
| **Auto-install** | Missing tools installed automatically |

### Disadvantages

| Con | Mitigation |
|-----|------------|
| **Single task type** | Add more benchmarks for different task categories |
| **Python-only** | Extend to TypeScript/Go if needed |
| **Requires manual agent execution** | Could be automated with CLI wrappers |
| **Heavy dependency footprint** | ~90 packages; use isolated venv |
| **Node.js required for jscpd** | Optional; duplication check skipped if missing |
| **No network isolation** | Agents could theoretically cheat by searching for solutions |
| **Variance across runs** | Run multiple times; statistical analysis needed |

### Risk Matrix

```
                    High Impact
                         |
    Context Trap fails   |   QA Trap fails
    (breaks prod)        |   (silent regressions)
                         |
   ----------------------+----------------------
                         |
    Docs Trap fails      |   Research Trap fails
    (friction)           |   (subtle bugs)
                         |
                    Low Impact
         Low Frequency       High Frequency
```

---

## 5. Using Titan Protocol with AmpCode

### Execution Protocol for AmpCode

AmpCode's strength is **parallel task execution via sub-agents**. The recommended test:

```bash
# Step 1: Prepare a fresh run directory
cd sota_analysis/titan_protocol
source .venv/bin/activate
python run_test.py --prepare --runs 3 --tools ampcode

# Step 2: Navigate to run directory
cd ~/titan_protocol_runs/runs/ampcode/<run_id>/

# Step 3: Execute AmpCode with the parallel prompt
# In AmpCode terminal:
amp init
# Then prompt:
"Read TITAN_SPEC.md.
1. Create an AGENTS.md configuration. Assign @IngestAgent to ingest.py and @ReportAgent to report.py.
2. Once configured, execute the implementation of both modules in parallel."

# Step 4: Score after completion
cd sota_analysis/titan_protocol
python run_test.py --score --output-root ~/titan_protocol_runs

# Step 5: Review results
cat ~/titan_protocol_runs/results.csv
python summarize_results.py --input ~/titan_protocol_runs/results.csv \
  --out-md ~/titan_protocol_runs/summary.md \
  --out-chart ~/titan_protocol_runs/summary.png
```

### What to Measure for AmpCode

| Metric | Why It Matters |
|--------|----------------|
| **Context Trap Score (0 or 25)** | Did agents share context about legacy_crypto.py? |
| **Research Trap Score (0 or 25)** | Did parallel agents coordinate on API research? |
| **Total Score** | Overall capability |
| **Time to completion** | Parallel speedup benefit |
| **Token usage** | Cost efficiency |
| **Sub-agent coordination** | Check telemetry.json for agent patterns |

### AmpCode-Specific Trap Analysis

| Trap | AmpCode Risk | Watch For |
|------|--------------|-----------|
| Context | **HIGH** - parallel agents may not share file context | @IngestAgent ignores legacy_crypto.py |
| Research | **MEDIUM** - if one agent researches, does it share? | Incorrect rotate() implementation |
| QA | **LOW** - testing usually runs after main implementation | Missing mocks |
| Quality | **MEDIUM** - parallel code may have inconsistent style | Lint errors from merged code |

### Comparison Test Matrix

Run the same spec across all three tools:

```
+----------+------------------+----------------------------------+
| Tool     | Prompt Style     | Expected Strength                |
+----------+------------------+----------------------------------+
| AmpCode  | Parallel agents  | Speed, scaffolding               |
| Augment  | Context-aware    | Legacy code integration          |
| OpenCode | Loop/grind       | Test fixing, lint compliance     |
+----------+------------------+----------------------------------+
```

---

## 6. Recommended Workflow for Your Team

### Phase 1: Baseline Evaluation (Week 1)

1. Run 3 iterations per tool with **neutral prompts**
2. Collect `results.csv` and `telemetry.json`
3. Generate summary report and chart

### Phase 2: Optimized Prompts (Week 2)

1. Run 3 iterations per tool with **tool-optimized prompts**
2. Compare scores against baseline
3. Identify which tool benefits most from prompt engineering

### Phase 3: Decision Meeting

Use the existing `presentation.md` template:

```bash
# Export to PowerPoint for Google Slides
python export_slides.py --input presentation.md \
  --out ~/titan_protocol_runs/presentation.pptx
```

### Decision Framework

```
IF Context Trap consistently fails:
  → Use Augment for legacy-sensitive code
  
IF Research Trap consistently fails:
  → Add explicit API doc links in prompts
  
IF QA Trap consistently fails:
  → Use OpenCode loop for test refinement
  
IF all tools score similarly:
  → Choose based on speed + token cost
```

---

## 7. Output Artifacts Reference

| File | Location | Purpose |
|------|----------|---------|
| `results.csv` | `~/titan_protocol_runs/` | Spreadsheet-friendly scores |
| `results.jsonl` | `~/titan_protocol_runs/` | Machine-readable line-delimited JSON |
| `results.json` | `~/titan_protocol_runs/` | Single JSON array |
| `judge.json` | `<run_dir>/` | Per-run detailed breakdown |
| `judge.log` | `<run_dir>/` | Human-readable scoring output |
| `telemetry.json` | `<run_dir>/` | Agent usage metrics |
| `summary.md` | `~/titan_protocol_runs/` | Markdown report |
| `summary.png` | `~/titan_protocol_runs/` | Bar chart visualization |

---

## 8. Quick Reference Commands

```bash
# Activate environment
source sota_analysis/titan_protocol/.venv/bin/activate

# Prepare runs (1 per tool)
python run_test.py --prepare --runs 1

# Prepare runs (3 per tool, specific tools)
python run_test.py --prepare --runs 3 --tools ampcode,augment,opencode

# Score all completed runs
python run_test.py --score

# Re-score previously scored runs
python run_test.py --score --rescore

# Generate summary
python summarize_results.py \
  --input ~/titan_protocol_runs/results.csv \
  --out-md ~/titan_protocol_runs/summary.md \
  --out-chart ~/titan_protocol_runs/summary.png

# Run judge manually in a run directory
cd ~/titan_protocol_runs/runs/ampcode/<run_id>/
python judge.py

# Skip execution tests (static analysis only)
TITAN_SKIP_EXEC=1 python judge.py

# Collect telemetry from OpenCode session
python collect_telemetry.py \
  --run-dir ~/titan_protocol_runs/runs/opencode/<run_id>/ \
  --export --session <SESSION_ID>
```

---

## 9. Appendix: Score Interpretation Guide

| Score Range | Interpretation |
|-------------|----------------|
| **90-100** | Production-ready; agent understood all constraints |
| **70-89** | Good but missed a trap; review specific failure |
| **50-69** | Significant issues; agent needs prompt refinement |
| **30-49** | Major failures; tool may not suit this task type |
| **0-29** | Incomplete; check if agent finished execution |

### Individual Trap Thresholds

| Trap | Pass | Fail | Concern |
|------|------|------|---------|
| Context | 25 | 0 | Binary - no partial credit |
| Research | 25 | 0 | Binary - rotation must be exact |
| QA | 20 | 0 | Binary - must mock, not call real |
| Quality | 15-20 | 0-14 | Graduated; 80%+ coverage required |
| Docs | 10 | 0 | Binary - Mermaid diagram present |

---

## 10. Conclusion

Titan Protocol provides your team with:

1. **Objective metrics** to compare AI coding tools
2. **Reproducible process** for ongoing evaluation
3. **Actionable insights** mapped to real development risks
4. **Ready-to-use workflow** for immediate testing

**Next Step:** Run the baseline evaluation with all three tools and schedule a decision meeting using the results.

---

*Report generated by Titan Protocol evaluation framework*
