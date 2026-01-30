# Titan Protocol: Complete Evaluation Report
## AmpCode vs Augment Code vs OpenCode

**Date:** January 30, 2026  
**Version:** 1.0  
**Author:** Automated Evaluation System

---

# Part 1: What is Titan Protocol?

## Overview

Titan Protocol is an **automated, objective evaluation harness** designed to test AI coding assistants on realistic software development tasks. It eliminates subjective opinions by using automated scoring against predefined criteria.

### Goals
- Provide objective, reproducible comparisons between AI coding tools
- Test real-world failure modes, not toy problems
- Identify which tools excel at which task types
- Enable data-driven tool selection decisions

### Anti-Cheat Design
- Results stored outside the repository (`~/titan_protocol_runs/`)
- Same specification, same files, same judge for all tools
- Automated scoring removes human bias

---

# Part 2: The Test Task - Project Log-Titan

## Task Description

Build a **CLI tool** called "Log-Titan" that ingests sensitive server logs and generates confidential PDF reports.

### Functional Requirements

```
┌─────────────────────────────────────────────────────────────────┐
│                         LOG-TITAN                               │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   INGEST    │    │   REPORT    │    │     CLI     │         │
│  │             │    │             │    │             │         │
│  │ Hash logs   │    │ Generate    │    │ Expose      │         │
│  │ Store in DB │    │ PDF report  │    │ commands    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│    titan.db           report.pdf         main.py               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Required Deliverables

| File | Purpose | Key Function |
|------|---------|--------------|
| `ingest.py` | Database operations | `ingest_log(message: str, severity: str)` |
| `report.py` | PDF generation | `generate_pdf(output_path: str)` |
| `main.py` | CLI interface | Commands: `ingest`, `report` |
| `tests/` | Test suite | pytest tests with mocked dependencies |
| `README.md` | Documentation | Must include Mermaid architecture diagram |

### Technical Stack
- **Database:** SQLite (`titan.db`)
- **PDF Library:** ReportLab
- **CLI Framework:** typer or argparse
- **Testing:** pytest with unittest.mock

---

# Part 3: The 5 Evaluation Traps (Detailed)

Each trap tests a specific **real-world failure mode** that AI coding assistants commonly exhibit.

## Trap 1: Context Trap (25 points)

### Setup
A file `legacy_crypto.py` exists in the test directory with this content:

```python
"""Legacy cryptography dependency used for Titan Protocol evaluation."""

# CRITICAL: This represents a rigid enterprise dependency.
def secure_hash(data: str) -> str:
    """Proprietary legacy hashing algorithm. DO NOT MODIFY."""
    return f"TITAN_{hash(data)}_ENCRYPTED"
```

### What It Tests
> "Does the AI find and use existing code, or does it reinvent the wheel?"

### Pass Criteria
| Action | Result |
|--------|--------|
| `from legacy_crypto import secure_hash` | ✅ PASS |
| `import hashlib` and write own hashing | ❌ FAIL |
| Modified `legacy_crypto.py` | ❌ FAIL |
| Created new `crypto.py` file | ❌ FAIL |

### Detection Method
The judge uses AST parsing to check if `ingest.py`:
1. Contains `import legacy_crypto` or `from legacy_crypto import`
2. Does NOT contain `import hashlib`
3. `legacy_crypto.py` remains unmodified

### Real-World Scenario
> A developer asks an AI to add a feature. The codebase already has a utility function for this exact purpose. The AI writes duplicate code instead of using the existing function.

### Business Impact of Failure
- **Code duplication** → Maintenance nightmare
- **Inconsistency** → Different implementations diverge over time
- **Wasted effort** → Solving already-solved problems
- **Integration bugs** → New code doesn't match existing patterns

---

## Trap 2: Research Trap (25 points)

### Setup
The specification states:
> "The generated PDF must contain a 'CONFIDENTIAL' watermark. This watermark must be **rotated exactly 45 degrees** across the center of the page."

### What It Tests
> "Does the AI verify API documentation before implementing, or does it guess?"

### Pass Criteria
```python
# CORRECT - exactly 45 degrees
canvas.rotate(45)  # ✅ PASS

# INCORRECT - wrong angle
canvas.rotate(90)  # ❌ FAIL
canvas.rotate(-45) # ❌ FAIL
canvas.rotate(30)  # ❌ FAIL

# INCORRECT - no rotation
# (missing rotate call) # ❌ FAIL
```

### Detection Method
The judge uses AST parsing to find:
1. A call to `.rotate()` method
2. With argument `45` (literal or variable that equals 45)

```python
def has_rotate_45(report_path: Path) -> bool:
    """Return True if report.py rotates canvas by 45 degrees."""
    # Parses AST looking for rotate(45) or angle=45; rotate(angle)
```

### Real-World Scenario
> AI confidently implements an API call but uses wrong parameters, deprecated methods, or incorrect syntax. The code runs but produces subtly wrong output.

### Business Impact of Failure
- **Subtle bugs** → Code runs but output is wrong
- **Runtime failures** → Works locally, fails in production
- **Security issues** → Incorrect crypto/auth implementations
- **Technical debt** → Wrong patterns propagate through codebase

---

## Trap 3: QA Trap (20 points)

### Setup
The specification states:
> "You MUST mock the `legacy_crypto` dependency in your tests. Do not call the real legacy file during testing."

### What It Tests
> "Does the AI properly isolate tests from external dependencies?"

### Pass Criteria
```python
# CORRECT - mocks at source module
@patch("legacy_crypto.secure_hash")  # ✅ PASS
def test_ingest_log(mock_hash):
    mock_hash.return_value = "MOCKED"
    ...

# INCORRECT - judge doesn't detect this pattern
@patch("ingest.secure_hash")  # ❌ FAIL (valid Python, but not detected)
def test_ingest_log(mock_hash):
    ...

# INCORRECT - no mocking at all
def test_ingest_log():  # ❌ FAIL
    ingest_log("test", "INFO")  # Calls real secure_hash
```

### Detection Method
The judge searches test files for:
1. `patch()` or `patch.object()` calls
2. Where the patch target string contains `"legacy_crypto"`

```python
def mocks_legacy_crypto(tests_dir: Path) -> bool:
    """Return True if tests patch legacy_crypto usage."""
    # Searches for patch("...legacy_crypto...")
```

### Real-World Scenario
> Tests call real databases, APIs, or external services. Tests become slow, flaky, and fail when external services are unavailable.

### Business Impact of Failure
- **Flaky CI/CD** → Tests randomly fail
- **Slow feedback** → Real network calls take time
- **Hidden coupling** → Can't test components in isolation
- **Production data exposure** → Tests accidentally hit real systems

---

## Trap 4: Quality Trap (20 points)

### Setup
Code is evaluated against **16 static analysis tools** covering multiple quality dimensions.

### What It Tests
> "Does the AI produce production-ready code that meets professional standards?"

### Quality Checks Breakdown

| Check | Points | Tool | Requirement |
|-------|--------|------|-------------|
| **Linting** | 2 | ruff | Zero errors on `ruff check .` |
| **Modernization** | 1 | ruff (UP rules) | No outdated Python patterns |
| **Complexity** | 1 | xenon + ruff C90 | Cyclomatic complexity ≤ 12 |
| **Pylint** | 1 | pylint | Score above threshold |
| **Dead Code** | 1 | vulture | No unused functions/variables |
| **Duplication** | 1 | jscpd | No copy-paste code blocks |
| **Type Check** | 2 | mypy + pyright | Both must pass |
| **Security** | 2 | bandit | No high-severity issues |
| **Coverage** | 2 | pytest-cov | ≥80% test coverage |
| **Docstrings** | 1 | pydocstyle | D100-D107 rules pass |
| **Semgrep** | 1 | semgrep | No security rule violations |
| **Pip Audit** | 1 | pip-audit | No known vulnerabilities |
| **Spelling** | 1 | codespell | No typos in code/comments |
| **Formatting** | 1 | ruff format | Code properly formatted |
| **Imports** | 1 | isort | Imports correctly ordered |
| **Licenses** | 1 | pip-licenses | License inventory generated |

**Total: 20 points**

### Real-World Scenario
> AI generates code that works but has security vulnerabilities, no type hints, inconsistent formatting, and poor test coverage.

### Business Impact of Failure
- **Security vulnerabilities** → Data breaches, compliance issues
- **Maintenance burden** → Hard to understand and modify code
- **CI/CD failures** → Linting blocks merges
- **Type errors** → Runtime crashes in production

---

## Trap 5: Documentation Trap (10 points)

### Setup
The specification states:
> "A `README.md` containing a Mermaid architecture diagram."

### What It Tests
> "Does the AI document the system architecture for other developers?"

### Pass Criteria
README.md must contain a Mermaid code block:

```markdown
# Project Title

## Architecture

```mermaid
graph TD
    A[CLI] --> B[Ingest Module]
    A --> C[Report Module]
    B --> D[(SQLite DB)]
    C --> D
    C --> E[PDF Output]
```                          ← Must be present
```

### Detection Method
```python
def has_mermaid_diagram(readme_path: Path) -> bool:
    """Return True if README contains a mermaid diagram."""
    content = readme_path.read_text()
    return "mermaid" in content.lower()
```

### Real-World Scenario
> AI generates working code but no documentation. New team members spend weeks trying to understand the architecture.

### Business Impact of Failure
- **Onboarding friction** → New developers lost
- **Knowledge silos** → Only original author understands
- **Maintenance fear** → Nobody wants to touch undocumented code
- **Lost decisions** → Why was it built this way?

---

# Part 4: Scoring System

## How the Judge Works

```
┌──────────────────────────────────────────────────────────────────┐
│                      JUDGE PIPELINE                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. FILE DETECTION                                               │
│     └─→ Check ingest.py, report.py, main.py, tests/, README.md   │
│                                                                  │
│  2. AST ANALYSIS                                                 │
│     └─→ Parse Python files for imports, function calls           │
│     └─→ Check for legacy_crypto usage                            │
│     └─→ Find rotate(45) calls                                    │
│                                                                  │
│  3. PATTERN MATCHING                                             │
│     └─→ Search tests for @patch("legacy_crypto...")              │
│     └─→ Search README for "mermaid"                              │
│                                                                  │
│  4. TOOL EXECUTION                                               │
│     └─→ Run: ruff, pylint, mypy, pyright, bandit, pytest, etc.   │
│     └─→ Capture exit codes and output                            │
│                                                                  │
│  5. SCORE CALCULATION                                            │
│     └─→ Context: 0 or 25                                         │
│     └─→ Research: 0 or 25                                        │
│     └─→ QA: 0 or 20                                              │
│     └─→ Quality: 0-20 (sum of checks)                            │
│     └─→ Docs: 0 or 10                                            │
│                                                                  │
│  6. OUTPUT                                                       │
│     └─→ judge.json (structured scores)                           │
│     └─→ judge.log (human-readable summary)                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Scoring Formula

```
FINAL_SCORE = Context(0|25) + Research(0|25) + QA(0|20) + Quality(0-20) + Docs(0|10)

Maximum: 100 points
```

---

# Part 5: Results

## Final Standings

| Rank | Tool | Score | Grade |
|------|------|-------|-------|
| 🥇 **1st** | **OpenCode** | **89/100** | A |
| 🥈 2nd | Augment | 71/100 | C+ |
| 🥉 3rd | AmpCode | 68/100 | D+ |

## Score Visualization

```
FINAL SCORES (out of 100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥇 OpenCode  ████████████████████████████████████████████████████████████████████████████████████████░░░░░░░░░░░  89

🥈 Augment   ███████████████████████████████████████████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  71

🥉 AmpCode   ████████████████████████████████████████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  68

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Detailed Breakdown

| Trap | Max | AmpCode | Augment | OpenCode |
|------|-----|---------|---------|----------|
| Context | 25 | ✅ 25 | ✅ 25 | ✅ 25 |
| Research | 25 | ✅ 25 | ✅ 25 | ✅ 25 |
| QA | 20 | ❌ 0 | ❌ 0 | ✅ **20** |
| Quality | 20 | 8 | **11** | 9 |
| Docs | 10 | ✅ 10 | ✅ 10 | ✅ 10 |
| **TOTAL** | **100** | **68** | **71** | **89** |

---

## Trap-by-Trap Analysis

### Context Trap Results (25 points)

| Tool | Score | Implementation |
|------|-------|----------------|
| OpenCode | 25/25 ✅ | `from legacy_crypto import secure_hash` |
| Augment | 25/25 ✅ | `from legacy_crypto import secure_hash` |
| AmpCode | 25/25 ✅ | `from legacy_crypto import secure_hash` |

**Analysis:** All three tools successfully identified and used the existing `legacy_crypto.py` file. This demonstrates that modern AI coding assistants have strong context awareness.

### Research Trap Results (25 points)

| Tool | Score | Implementation |
|------|-------|----------------|
| OpenCode | 25/25 ✅ | `canvas.rotate(45)` |
| Augment | 25/25 ✅ | `c.rotate(45)` |
| AmpCode | 25/25 ✅ | `c.rotate(45)` |

**Analysis:** All three tools correctly researched the ReportLab API and implemented the 45-degree rotation. None fell for common mistakes like wrong angles or missing rotation.

### QA Trap Results (20 points)

| Tool | Score | Mock Pattern Used |
|------|-------|-------------------|
| **OpenCode** | **20/20 ✅** | `@patch("legacy_crypto.secure_hash")` |
| Augment | 0/20 ❌ | `@patch("ingest.secure_hash")` |
| AmpCode | 0/20 ❌ | `@patch("ingest.secure_hash")` |

**Analysis:** This was the **decisive trap**. OpenCode used the exact mock pattern the judge looks for (`legacy_crypto.secure_hash`), while AmpCode and Augment used `ingest.secure_hash` (mocking where imported rather than at source).

**Important Note:** Both patterns are valid Python mocking strategies. The judge specifically checks for "legacy_crypto" in the patch string. Evidence that AmpCode/Augment's mocking actually works:
- `legacy_crypto.py` coverage = 50% (only import line executed)
- If tests weren't mocking, coverage would be 100%

### Quality Trap Results (20 points)

| Check | Pts | AmpCode | Augment | OpenCode |
|-------|-----|---------|---------|----------|
| ruff | 2 | ✅ 2 | ✅ 2 | ✅ 2 |
| modernization | 1 | ❌ 0 | ❌ 0 | ❌ 0 |
| complexity | 1 | ❌ 0 | ❌ 0 | ❌ 0 |
| pylint | 1 | ❌ 0 | ❌ 0 | ❌ 0 |
| dead_code | 1 | ✅ 1 | ✅ 1 | ❌ 0 |
| duplication | 1 | ❌ 0 | ✅ 1 | ✅ 1 |
| type_check | 2 | ❌ 0 | ❌ 0 | ❌ 0 |
| security | 2 | ✅ 2 | ✅ 2 | ✅ 2 |
| coverage | 2 | ❌ 0 | ❌ 0 | ❌ 0 |
| docstyle | 1 | ❌ 0 | ✅ 1 | ❌ 0 |
| semgrep | 1 | ❌ 0 | ❌ 0 | ❌ 0 |
| pip_audit | 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| codespell | 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| ruff_format | 1 | ❌ 0 | ❌ 0 | ❌ 0 |
| isort | 1 | ❌ 0 | ✅ 1 | ✅ 1 |
| license | 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| **TOTAL** | **20** | **8** | **11** | **9** |

**Quality Winner:** Augment (11/20)

### Documentation Trap Results (10 points)

| Tool | Score | Has Mermaid? |
|------|-------|--------------|
| OpenCode | 10/10 ✅ | Yes |
| Augment | 10/10 ✅ | Yes |
| AmpCode | 10/10 ✅ | Yes |

**Analysis:** All three tools included Mermaid architecture diagrams in their README files.

---

## Test Metrics Comparison

| Metric | AmpCode | Augment | OpenCode |
|--------|---------|---------|----------|
| Test Files | 3 | 3 | 1 |
| Total Tests | 10 | 14 | 2 |
| Tests Passing | 10 | 14 | 2 |
| Coverage % | 32% | 36% | 17% |
| Execution Time | 1.18s | 0.11s | 0.15s |

**Note:** All tools below 80% coverage threshold because `judge.py` (407 lines) is included in the coverage calculation.

---

# Part 6: Implementation Analysis

## AmpCode: Parallel Agent Approach

### Architecture
```
AGENTS.md (Coordination File)
├── @IngestAgent → ingest.py
├── @ReportAgent → report.py
├── @CLIAgent → main.py
└── @TestAgent → tests/
```

### Characteristics
- **Parallel execution** of multiple agents
- **Minimal code** - functional, lightweight
- **Fast completion** (~5 minutes)
- **Agent coordination** via AGENTS.md file

### Code Sample (ingest.py - 43 lines)
```python
from legacy_crypto import secure_hash

def ingest_log(message: str, severity: str) -> None:
    message_hash = secure_hash(message)
    conn = _get_connection()
    conn.execute("INSERT INTO logs ...", (message_hash, severity))
```

---

## Augment: Context-Aware Sequential Approach

### Architecture
```
Cloud Index
    ↓
Context Discovery (found legacy_crypto.py)
    ↓
Sequential Implementation: ingest → report → main → tests
```

### Characteristics
- **Cloud indexing** for context awareness
- **Production-ready code** with comprehensive docstrings
- **Most tests** (14 total)
- **Best code quality metrics** (11/20)

### Code Sample (ingest.py - 85 lines)
```python
"""Ingest module for log-titan.

This module handles database operations for storing log entries.
"""
from legacy_crypto import secure_hash

def ingest_log(message: str, severity: str) -> None:
    """Hash the message and store it in the database.

    Args:
        message: The log message to store.
        severity: The severity level of the log.
    """
    message_hash = secure_hash(message)
    ...
```

---

## OpenCode: Deep Loop/Grind Approach

### Architecture
```
Read Spec
    ↓
Implement
    ↓
Test
    ↓
Fix Issues
    ↓
Repeat Until Clean
```

### Characteristics
- **Iterative refinement** loop
- **Strict instruction following** (used exact mock pattern)
- **Longer execution time** (~25 minutes)
- **Fewer but targeted tests** (2 tests)

### Code Sample (test with correct mock pattern)
```python
@patch("legacy_crypto.secure_hash")  # ← Exact pattern judge expects
def test_ingest_log(mock_secure_hash, temp_db):
    mock_secure_hash.return_value = "MOCKED_HASH"
    ingest_log("test", "INFO")
    mock_secure_hash.assert_called_once()
```

---

# Part 7: Adjusted Scores Analysis

## If All Tools Used Correct Mock Pattern

If AmpCode and Augment had used `@patch("legacy_crypto.secure_hash")`:

| Tool | Original | +QA | Adjusted |
|------|----------|-----|----------|
| OpenCode | 89 | - | 89 |
| Augment | 71 | +20 | **91** |
| AmpCode | 68 | +20 | **88** |

**Potential Winner with Correct Prompting:** Augment (91)

## Lesson Learned
Prompt engineering significantly impacts results. Specifying the exact mock pattern in the prompt would have changed the outcome.

---

# Part 8: Recommendations

## Tool Selection Guide

| Scenario | Recommended Tool | Rationale |
|----------|------------------|-----------|
| **Strict specification compliance** | OpenCode | Best at following exact instructions |
| **Production code quality** | Augment | Best quality metrics, most tests |
| **Fast prototyping** | AmpCode | Parallel execution, quick results |
| **Legacy codebase integration** | Augment | Strong context awareness |
| **Final verification pass** | OpenCode | Catches specification violations |
| **Comprehensive test coverage** | Augment | Writes most tests |

## The Titan Relay Workflow

For maximum quality, use all three tools in sequence:

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   AmpCode   │  →   │   Augment   │  →   │  OpenCode   │
│             │      │             │      │             │
│    FAST     │      │   QUALITY   │      │   VERIFY    │
│  Scaffold   │      │   Polish    │      │    Specs    │
│   Parallel  │      │  Docstrings │      │  Compliance │
└─────────────┘      └─────────────┘      └─────────────┘
```

## Action Items

### Immediate (This Week)
1. Update prompt templates to specify:
   - `@patch("legacy_crypto.secure_hash")` pattern
   - Google-style docstrings requirement
   - isort-compatible import ordering
2. Use OpenCode for spec-critical tasks

### Short-term (2 Weeks)
3. Re-run evaluation with corrected prompts
4. Add timing and token usage metrics
5. Test with more complex specifications

### Long-term
6. Propose judge.py update to accept both mock patterns
7. Implement Titan Relay workflow in CI/CD
8. Expand test suite with additional trap types

---

# Part 9: Appendix

## Run Details

| Tool | Run ID | Directory |
|------|--------|-----------|
| AmpCode | `20260130_094822_153860_run01` | `~/titan_protocol_runs/runs/ampcode/` |
| Augment | `20260130_095121_763364_run01` | `~/titan_protocol_runs/runs/augment/` |
| OpenCode | `20260130_100316_604896_run01` | `~/titan_protocol_runs/runs/opencode/` |

## File Locations

```
~/titan_protocol_runs/
├── results.csv                    # All scores in CSV format
├── results.jsonl                  # All scores in JSONL format
├── summary.md                     # Quick summary table
├── summary.png                    # Bar chart visualization
├── FINAL_COMPARISON_REPORT.md     # This report
├── final_presentation.pdf         # Slide deck
├── runs/
│   ├── ampcode/
│   │   └── 20260130_094822_153860_run01/
│   │       ├── ingest.py
│   │       ├── report.py
│   │       ├── main.py
│   │       ├── tests/
│   │       ├── README.md
│   │       ├── judge.json         # Detailed scores
│   │       └── judge.log          # Summary output
│   ├── augment/
│   │   └── 20260130_095121_763364_run01/
│   │       └── ...
│   └── opencode/
│       └── 20260130_100316_604896_run01/
│           └── ...
```

## Commands Reference

```bash
# Activate environment
source ~/dev/github/ray-manaloto/sota_analysis/titan_protocol/.venv/bin/activate

# Prepare new runs
python run_test.py --prepare --runs 3 --tools ampcode,augment,opencode

# Score all runs
python run_test.py --score --output-root ~/titan_protocol_runs

# Re-score existing runs
python run_test.py --score --rescore

# Generate summary
python summarize_results.py \
  --input ~/titan_protocol_runs/results.csv \
  --out-md ~/titan_protocol_runs/summary.md \
  --out-chart ~/titan_protocol_runs/summary.png

# Run judge manually
cd ~/titan_protocol_runs/runs/<tool>/<run_id>/
python judge.py
```

---

# Conclusion

## Key Findings

1. **OpenCode wins overall (89/100)** - Best at following specific instructions exactly
2. **Augment has best code quality (11/20)** - Most polished code, most comprehensive tests
3. **AmpCode is fastest** - Parallel agent execution enables rapid prototyping
4. **QA trap was decisive** - 20-point swing based on mock pattern choice
5. **All tools found legacy code** - Context awareness is now universal
6. **Prompt engineering matters** - Specific instructions yield better compliance

## Final Verdict

| Category | Winner |
|----------|--------|
| **Overall Score** | 🥇 OpenCode (89) |
| **Code Quality** | 🥇 Augment (11/20) |
| **Speed** | 🥇 AmpCode |
| **Test Coverage** | 🥇 Augment (14 tests) |
| **Instruction Following** | 🥇 OpenCode |

**Recommendation:** Use the **Titan Relay workflow** (AmpCode → Augment → OpenCode) for production work to leverage each tool's strengths.

---

*Report generated by Titan Protocol Evaluation System*
*January 30, 2026*
