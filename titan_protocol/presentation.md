---
marp: true
theme: default
class: lead
paginate: true
---

# Titan Protocol Results
## Choosing the right agent workflow

**Audience:** Devs, CTO, CEO
**Goal:** Decision + next actions

<!--
Notes: Open with the decision we need today and why speed matters.
-->

---

# Outcome (Today)
- Decide default workflow for agent tasks
- Agree on 2 follow-up experiments

<!--
Notes: We are not picking a "winner" for all tasks. We are matching tools to task types.
-->

---

# Why We Ran This
- Reduce time lost to tool mismatch
- Cut token/iteration waste
- Establish a repeatable evaluation

<!--
Notes: This is about reliability and speed, not hype.
-->

---

# Test Setup (Titan Protocol)
- Spec with 5 scoring traps
  - Context, Research, QA Mocking, Lint, Docs
- Automated judge + CSV logging
- Repeatable runs per tool

<!--
Notes: Standardized scoring removes opinion.
-->

---

# Fairness Controls
- Same spec, same files, same scoring
- Run multiple times to account for variance
- Optional: neutral prompt vs tool-optimized prompt

<!--
Notes: If we only did tool-optimized prompts, results are directional.
-->

---

# Results Overview

![Results](summary.png)

<!--
Notes: Walk through averages + spread. Focus on major failures.
-->

---

# What the Failures Mean
- **Context Trap fails** → risk with legacy constraints
- **Research Trap fails** → risk with external API correctness
- **QA Trap fails** → brittle tests, hidden regression risk

<!--
Notes: Translate scores to real-world consequences.
-->

---

# Decision Proposal
**Recommended default workflow:**
1. **AmpCode** for scaffolding
2. **Augment** for legacy-sensitive logic
3. **OpenCode** for tests + polish

**If choosing one default tool:**
- [Fill in based on results]

<!--
Notes: The relay workflow minimizes risk by leveraging strengths.
-->

---

# Actions (Next 2 Weeks)
- Update repo docs with workflow
- Run 3 more neutral-prompt rounds
- Add a real repo task benchmark

**Owners:**
- [Assign]

<!--
Notes: Make this executable and time-bound.
-->

---

# Q&A (15 min)
- Bring up `results.csv` and `judge.log` as needed

<!--
Notes: Validate concerns with data, not opinion.
-->
