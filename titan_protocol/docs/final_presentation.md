---
marp: true
theme: default
class: lead
paginate: true
backgroundColor: #fff
---

# Titan Protocol Results
## AmpCode vs Augment vs OpenCode

**Date:** January 30, 2026
**AI Coding Assistant Evaluation**

---

# Agenda

1. What is Titan Protocol?
2. The Test Task: Project Log-Titan
3. The 5 Evaluation Traps (Detailed)
4. How Scoring Works
5. Results & Analysis
6. Recommendations

---

# What is Titan Protocol?

An **automated, objective evaluation harness** for AI coding assistants.

### Why We Built It
- Eliminate subjective "I think tool X is better" debates
- Test real-world failure modes, not toy problems
- Reproducible results with automated scoring
- Compare tools on equal footing

### Anti-Cheat Design
- Results stored outside repo (`~/titan_protocol_runs/`)
- Same spec, same files, same judge for all tools

---

# The Test Task: Project Log-Titan

Build a **CLI tool** that:

```
┌─────────────────────────────────────────────────────────┐
│                    LOG-TITAN                            │
│                                                         │
│  1. INGEST: Hash server logs and store in SQLite        │
│  2. REPORT: Generate PDF with confidential watermark    │
│  3. CLI: Expose ingest/report commands                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Time:** ~5-25 minutes per tool
**Complexity:** Moderate (database + PDF + CLI + tests)

---

# The Required Deliverables

| File | Purpose | Requirements |
|------|---------|--------------|
| `ingest.py` | Database logic | `ingest_log(message, severity)` function |
| `report.py` | PDF generation | `generate_pdf(output_path)` function |
| `main.py` | CLI interface | typer or argparse commands |
| `tests/` | Test suite | pytest with mocked dependencies |
| `README.md` | Documentation | Must include Mermaid diagram |

**Total: 5 files minimum**

---

# The 5 Evaluation Traps

Each trap tests a **real-world failure mode**:

| Trap | Points | Failure Mode Tested |
|------|--------|---------------------|
| **Context** | 25 | Ignoring existing code |
| **Research** | 25 | Not reading API docs |
| **QA** | 20 | Improper test isolation |
| **Quality** | 20 | Technical debt |
| **Docs** | 10 | Missing documentation |

**Total: 100 points**

---

# Trap 1: Context (25 points)

### The Setup
A file `legacy_crypto.py` exists in the directory:
```python
def secure_hash(data: str) -> str:
    """Proprietary legacy hashing algorithm. DO NOT MODIFY."""
    return f"TITAN_{hash(data)}_ENCRYPTED"
```

### The Test
> "Does the AI find and use existing code, or reinvent the wheel?"

### Pass Criteria
- ✅ `from legacy_crypto import secure_hash`
- ❌ `import hashlib` (wrote own hashing)
- ❌ Modified `legacy_crypto.py`

---

# Trap 1: Why It Matters

### Real-World Scenario
> Developer asks AI to add a feature. Codebase already has a utility function for this. AI writes duplicate code instead of using existing function.

### Business Impact
- 🔴 **Code duplication** - maintenance nightmare
- 🔴 **Inconsistency** - different implementations diverge
- 🔴 **Wasted effort** - solving already-solved problems
- 🔴 **Integration bugs** - new code doesn't match existing patterns

---

# Trap 2: Research (25 points)

### The Setup
Spec requires: *"PDF watermark must be rotated exactly 45 degrees"*

### The Test
> "Does the AI verify API documentation before implementing?"

### Pass Criteria
```python
# Must call canvas.rotate(45) - exactly 45, not 90, not -45
canvas.rotate(45)  # ✅
canvas.rotate(90)  # ❌
# No rotation at all # ❌
```

### Detection
Judge uses AST parsing to find `rotate(45)` calls

---

# Trap 2: Why It Matters

### Real-World Scenario
> AI confidently implements an API call but uses wrong parameters, deprecated methods, or incorrect syntax.

### Business Impact
- 🔴 **Subtle bugs** - code runs but produces wrong output
- 🔴 **Runtime failures** - works locally, fails in production
- 🔴 **Security issues** - incorrect crypto/auth implementations
- 🔴 **Technical debt** - wrong patterns propagate

---

# Trap 3: QA (20 points)

### The Setup
Tests must **mock** the `legacy_crypto` dependency, not call it directly.

### The Test
> "Does the AI properly isolate tests from external dependencies?"

### Pass Criteria
```python
# Judge looks for this exact pattern:
@patch("legacy_crypto.secure_hash")  # ✅
def test_ingest():
    ...

# This pattern fails (even though technically valid Python):
@patch("ingest.secure_hash")  # ❌ Judge doesn't detect
```

---

# Trap 3: Why It Matters

### Real-World Scenario
> Tests call real databases, APIs, or services. Tests are slow, flaky, and fail when external services are down.

### Business Impact
- 🔴 **Flaky CI/CD** - tests randomly fail
- 🔴 **Slow feedback** - real calls take time
- 🔴 **Hidden coupling** - can't test in isolation
- 🔴 **Production data exposure** - tests hit real systems

---

# Trap 4: Quality (20 points)

### The Setup
Code is evaluated against **16 static analysis tools**:

| Category | Tools |
|----------|-------|
| Linting | ruff, pylint |
| Type Safety | mypy, pyright |
| Security | bandit, semgrep, pip-audit |
| Style | pydocstyle, isort, ruff-format |
| Complexity | xenon, mccabe |
| Other | vulture, jscpd, codespell, coverage |

---

# Trap 4: Scoring Breakdown

| Check | Points | Requirement |
|-------|--------|-------------|
| ruff | 2 | Zero lint errors |
| type_check | 2 | mypy + pyright pass |
| security | 2 | No high-severity issues |
| coverage | 2 | ≥80% test coverage |
| modernization | 1 | No outdated patterns |
| complexity | 1 | Cyclomatic complexity OK |
| pylint | 1 | pylint passes |
| dead_code | 1 | No unused code |
| duplication | 1 | No copy-paste code |
| docstyle | 1 | Proper docstrings |
| + 6 more | 6 | Various checks |

---

# Trap 5: Documentation (10 points)

### The Setup
README.md must include a **Mermaid architecture diagram**.

### The Test
> "Does the AI document the system architecture?"

### Pass Criteria
```markdown
```mermaid
graph TD
    A[CLI] --> B[Ingest]
    A --> C[Report]
    B --> D[Database]
```                        ← Must contain "mermaid"
```

### Detection
Judge searches for `mermaid` string in README.md

---

# Trap 5: Why It Matters

### Real-World Scenario
> AI generates working code but no documentation. New team members can't understand the architecture.

### Business Impact
- 🔴 **Onboarding friction** - takes weeks to understand code
- 🔴 **Knowledge silos** - only original author understands
- 🔴 **Maintenance burden** - fear of changing undocumented code
- 🔴 **Technical debt** - architecture decisions lost

---

# How Scoring Works

```
┌──────────────────────────────────────────────────────────┐
│                    JUDGE PIPELINE                        │
├──────────────────────────────────────────────────────────┤
│  1. AST Analysis     → Check imports, function calls     │
│  2. Pattern Matching → Find mocks, diagrams              │
│  3. Tool Execution   → Run ruff, pytest, mypy, etc.      │
│  4. Score Tallying   → Sum points per category           │
│  5. JSON Output      → Structured results + breakdown    │
└──────────────────────────────────────────────────────────┘
```

**Fully automated** - no human judgment involved

---

# The Results Are In

| Rank | Tool | Score |
|------|------|-------|
| 🥇 | **OpenCode** | **89/100** |
| 🥈 | Augment | 71/100 |
| 🥉 | AmpCode | 68/100 |

### OpenCode wins by 18+ points!

---

# Score Breakdown by Trap

| Trap | AmpCode | Augment | OpenCode |
|------|---------|---------|----------|
| Context (25) | ✅ 25 | ✅ 25 | ✅ 25 |
| Research (25) | ✅ 25 | ✅ 25 | ✅ 25 |
| **QA (20)** | ❌ 0 | ❌ 0 | ✅ **20** |
| Quality (20) | 8 | **11** | 9 |
| Docs (10) | ✅ 10 | ✅ 10 | ✅ 10 |
| **TOTAL** | **68** | **71** | **89** |

---

# Visual Comparison

```
FINAL SCORES (out of 100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥇 OpenCode  █████████████████████████████████████████░░░░  89%

🥈 Augment   █████████████████████████████████░░░░░░░░░░░░  71%

🥉 AmpCode   ████████████████████████████████░░░░░░░░░░░░░  68%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

# The Decisive Factor: QA Trap

### Why OpenCode Won (+20 points)

**OpenCode used:**
```python
@patch("legacy_crypto.secure_hash")  # ✅ Judge detected
```

**AmpCode & Augment used:**
```python
@patch("ingest.secure_hash")  # ❌ Valid Python, but judge missed it
```

Both patterns work in Python, but judge specifically looks for "legacy_crypto" string.

---

# Context Trap: All Passed ✅

All three tools found and used `legacy_crypto.py`:

```python
# All three generated this in ingest.py:
from legacy_crypto import secure_hash

def ingest_log(message: str, severity: str):
    message_hash = secure_hash(message)  # ✅ Used existing code
    ...
```

**Verdict:** Context awareness is now universal across AI tools

---

# Research Trap: All Passed ✅

All three correctly implemented 45° rotation:

```python
# AmpCode
c.rotate(45)

# Augment  
c.rotate(45)

# OpenCode
canvas.rotate(45)
```

**Verdict:** All tools properly researched the ReportLab API

---

# Quality Comparison Detail

| Check | AmpCode | Augment | OpenCode |
|-------|---------|---------|----------|
| ruff | ✅ 2 | ✅ 2 | ✅ 2 |
| security | ✅ 2 | ✅ 2 | ✅ 2 |
| duplication | ❌ 0 | ✅ 1 | ✅ 1 |
| docstyle | ❌ 0 | ✅ 1 | ❌ 0 |
| isort | ❌ 0 | ✅ 1 | ✅ 1 |
| dead_code | ✅ 1 | ✅ 1 | ❌ 0 |
| **Total** | **8/20** | **11/20** | **9/20** |

**Quality Winner:** Augment

---

# Test Coverage

| Tool | Tests Written | Coverage |
|------|--------------|----------|
| Augment | 14 tests | 36% |
| AmpCode | 10 tests | 32% |
| OpenCode | 2 tests | 17% |

**Note:** All below 80% threshold because `judge.py` (407 lines) is included in coverage calculation.

---

# Implementation Approaches

### 🔵 AmpCode: Parallel Agents
```
AGENTS.md → @IngestAgent, @ReportAgent, @CLIAgent, @TestAgent
           ↓ (parallel execution)
```

### 🟢 Augment: Context-Aware Sequential
```
Cloud Index → Find existing files → Implement sequentially
```

### 🟣 OpenCode: Deep Loop/Grind
```
Read spec → Implement → Test → Fix → Repeat until clean
```

---

# Adjusted Scores

**If AmpCode & Augment used correct mock pattern:**

| Tool | Original | Adjusted |
|------|----------|----------|
| OpenCode | 89 | 89 |
| Augment | 71 | **91** ← Would win |
| AmpCode | 68 | **88** |

**Lesson:** Prompt engineering matters!

---

# Tool Strengths Summary

| Capability | Best Tool |
|------------|-----------|
| **Instruction Following** | 🟣 OpenCode |
| **Code Quality** | 🟢 Augment |
| **Speed** | 🔵 AmpCode |
| **Test Comprehensiveness** | 🟢 Augment |
| **Context Awareness** | All tied |
| **API Research** | All tied |

---

# When to Use Each Tool

| Scenario | Recommended | Why |
|----------|-------------|-----|
| Strict spec compliance | OpenCode | Follows instructions exactly |
| Production code quality | Augment | Best quality metrics |
| Fast prototyping | AmpCode | Parallel execution |
| Legacy codebase | Augment | Best context awareness |
| Final verification | OpenCode | Catches spec violations |

---

# The Titan Relay Workflow

For maximum quality, use **all three in sequence**:

```
┌─────────┐    ┌─────────┐    ┌──────────┐
│ AmpCode │ →  │ Augment │ →  │ OpenCode │
│  FAST   │    │ QUALITY │    │  VERIFY  │
│Scaffold │    │ Polish  │    │  Specs   │
└─────────┘    └─────────┘    └──────────┘
    ↓              ↓              ↓
 Parallel      Docstrings     Compliance
 Agents        Type hints      Check
```

---

# Key Takeaways

1. **OpenCode wins (89)** - Best at following specific instructions
2. **Augment best quality (11/20)** - Most polished, most tests
3. **AmpCode fastest** - Parallel agent execution
4. **QA trap was decisive** - 20 point swing from mock pattern
5. **All tools found legacy code** - Context awareness is universal
6. **Prompt engineering matters** - Correct instructions = better results

---

# Action Items

### Immediate
- Update prompt templates with `@patch("legacy_crypto.secure_hash")`
- Use OpenCode for spec-critical tasks

### Short-term
- Re-run evaluation with corrected prompts
- Add timing/token metrics

### Long-term
- Propose judge.py fix for both mock patterns
- Implement Titan Relay workflow

---

# Questions?

### Resources
- **Full Report:** `~/titan_protocol_runs/FINAL_COMPARISON_REPORT.md`
- **Raw Data:** `~/titan_protocol_runs/results.csv`
- **This Deck:** `~/titan_protocol_runs/final_presentation.pdf`

### Re-run Tests
```bash
cd sota_analysis/titan_protocol
python run_test.py --prepare --runs 3
python run_test.py --score
```
