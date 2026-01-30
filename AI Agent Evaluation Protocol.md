Here is the comprehensive **Evaluation Kit for the "Titan Protocol"**.

This package includes the **Agent-Ready Specification**, the **Tool-Specific Execution Protocols** (crucial for fair testing), an **Automated Scoring Script**, and a **Decision Matrix** to interpret the results.

### ---

**Part 1: The Trap Setup (Do this first)**

Before running any agent, create a directory for the test and add this specific "Control File". This file serves as the litmus test for whether the agent is actually reading your context or just hallucinating standard code.

**File:** legacy\_crypto.py

Python

\# legacy\_crypto.py  
\# CRITICAL: This represents a rigid enterprise dependency.  
def secure\_hash(data: str) \-\> str:  
    """Proprietary legacy hashing algorithm. DO NOT MODIFY."""  
    return f"TITAN\_{hash(data)}\_ENCRYPTED"

### ---

**Part 2: The Master Specification**

Copy the content below. This is the "Product Requirement Document" you will feed to the agents. It contains three hidden "Traps" designed to break specific agent architectures.

**File:** TITAN\_SPEC.md

Markdown

\# Project Log-Titan: Implementation Specification

\#\# 1\. Mission Profile  
Build \`log-titan\`, a CLI tool to ingest sensitive server logs and generate confidential PDF reports.

\#\# 2\. Core Constraints (THE TRAPS)  
\*   **\*\*Context Trap (Security):\*\*** You MUST use the existing \`legacy\_crypto.py\` file found in the root directory for all hashing.  
    \*   ❌ DO NOT write your own hashing logic or import \`hashlib\`.  
    \*   ❌ DO NOT modify \`legacy\_crypto.py\`.  
\*   **\*\*Research Trap (Visuals):\*\*** The generated PDF must contain a "CONFIDENTIAL" watermark.  
    \*   *\*Requirement:\** This watermark must be **\*\*rotated exactly 45 degrees\*\*** across the center of the page. You must verify the \`reportlab\` API to ensure the rotation logic is correct.  
\*   **\*\*Architecture Trap (Parallelism):\*\*** The system must be modular to support parallel build speeds. The database logic (\`ingest.py\`) and reporting logic (\`report.py\`) must be decoupled.

\#\# 3\. Functional Requirements

\#\#\# Module A: Ingest (\`ingest.py\`)  
\*   **\*\*Function:\*\*** \`ingest\_log(message: str, severity: str)\`  
\*   **\*\*Logic:\*\*** Hash the message using \`legacy\_crypto.secure\_hash\` and store it in a local SQLite database (\`titan.db\`).

\#\#\# Module B: Report (\`report.py\`)  
\*   **\*\*Function:\*\*** \`generate\_pdf(output\_path: str)\`  
\*   **\*\*Logic:\*\*** Query \`titan.db\`, generate a PDF listing logs, and apply the 45-degree Red watermark.

\#\#\# Module C: CLI (\`main.py\`)  
\*   **\*\*Logic:\*\*** Use \`typer\` or \`argparse\` to expose \`ingest\` and \`report\` commands.

\#\# 4\. Definition of Done  
\*   **\*\*QA:\*\*** Write a \`pytest\` suite in \`tests/\`.  
\*   **\*\*Mocking Trap:\*\*** You MUST mock the \`legacy\_crypto\` dependency in your tests. Do not call the real legacy file during testing.  
\*   **\*\*Quality:\*\*** Code must pass \`ruff check .\` with zero errors.  
\*   **\*\*Docs:\*\*** A \`README.md\` containing a Mermaid architecture diagram.

### ---

**Part 3: The Execution Protocol**

You cannot use the same prompt for every tool. To evaluate them fairly, you must trigger their specific "Superpowers."

#### **1\. AmpCode (The "Parallel" Test)**

*Goal: specific test to see if the Dispatcher can split tasks effectively.*

* **Step 1:** Run amp init.  
* **Step 2 (The Prompt):**  
  "Read TITAN\_SPEC.md.  
  1. Create an AGENTS.md configuration. Assign @IngestAgent to ingest.py and @ReportAgent to report.py.  
  2. Once configured, execute the implementation of both modules in parallel."

#### **2\. Augment Code (The "Context" Test)**

*Goal: specific test to see if the Cloud Index finds the legacy file without you pasting it.*

* **Step 1:** Run auggie /index (Ensure legacy\_crypto.py is indexed).  
* **Step 2 (The Prompt):***(Press Ctrl+P to open Prompt Enhancer)*  
  "Implement the solution described in TITAN\_SPEC.md. Pay strict attention to the legacy\_crypto constraint and the PDF watermark rotation requirements."

#### **3\. OpenCode (The "Grinder" Test)**

*Goal: specific test to see if the Loop can self-heal errors.*

* **Step 1:** Enable the plugin.  
* **Step 2 (The Prompt):**"Read TITAN\_SPEC.md. Implement the code sequentially."  
* **Step 3 (The Grind):**"Now run opencode loop 'Run pytest. If tests fail or mock is missing, fix code.' \--limit 5"

### ---

**Part 4: The Automated Scorecard (judge.py)**

Do not manually review the code. Save this script as judge.py in the test folder and run python judge.py to objectively score the agent.

Python

import os  
import subprocess  
import sys

def check\_file\_content(filepath, keywords):  
    if not os.path.exists(filepath): return False  
    with open(filepath, 'r', encoding="utf-8") as f:  
        content \= f.read()  
        return any(k in content for k in keywords)

def score\_titan():  
    score \= 0  
    report \= \[\]  
    print("\\n⚔️  TITAN PROTOCOL JUDGEMENT  ⚔️\\n")

    \# TRAP 1: CONTEXT (25 pts)  
    \# Did it import the legacy file?  
    if check\_file\_content("ingest.py", \["legacy\_crypto", "secure\_hash"\]):  
        score \+= 25  
        report.append("✅ \[25/25\] Context Trap Passed (Used Legacy Crypto)")  
    else:  
        report.append("❌ \[0/25\] Context Trap Failed (Ignored/Rewrote Legacy File)")

    \# TRAP 2: RESEARCH (25 pts)  
    \# Did it find the rotate method?  
    if check\_file\_content("report.py", \["rotate(45)", "rotate=45"\]):  
        score \+= 25  
        report.append("✅ \[25/25\] Research Trap Passed (Watermark Rotated)")  
    else:  
        report.append("❌ \[0/25\] Research Trap Failed (No Rotation Logic)")

    \# TRAP 3: QA MOCKING (20 pts)  
    \# Did it mock the dependency?  
    mock\_found \= False  
    if os.path.exists("tests"):  
        for root, \_, files in os.walk("tests"):  
            for file in files:  
                if check\_file\_content(os.path.join(root, file), \["mock", "patch"\]):  
                    mock\_found \= True  
    if mock\_found:  
        score \+= 20  
        report.append("✅ \[20/20\] QA Trap Passed (Dependency Mocked)")  
    else:  
        report.append("❌ \[0/20\] QA Trap Failed (Real Code Called in Tests)")

    \# TRAP 4: QUALITY (20 pts)  
    \# Does it pass Ruff?  
    try:  
        res \= subprocess.run(\["ruff", "check", "."\], capture\_output=True, text=True)  
        if res.returncode \== 0:  
            score \+= 20  
            report.append("✅ \[20/20\] Linter Passed (Zero Errors)")  
        else:  
            err\_count \= len(res.stdout.splitlines())  
            points \= max(0, 20 \- (err\_count \* 2))  
            score \+= points  
            report.append(f"⚠️ \[{points}/20\] Linter Failed ({err\_count} errors)")  
    except FileNotFoundError:  
        report.append("⚠️ \[0/20\] Ruff not installed (Skipped)")

    \# TRAP 5: DOCS (10 pts)  
    if check\_file\_content("README.md", \["mermaid", "graph TD"\]):  
        score \+= 10  
        report.append("✅ \[10/10\] Documentation Passed (Mermaid Diagram)")  
    else:  
        report.append("❌ \[0/10\] Documentation Failed (No Diagram)")

    print("-" \* 40)  
    for line in report: print(line)  
    print("-" \* 40)  
    print(f"🏆 FINAL SCORE: {score}/100")

if \_\_name\_\_ \== "\_\_main\_\_":  
    score\_titan()

### ---

**Part 5: The Decision Matrix (How to Choose)**

Based on the scores and behavior, here is how you select your tool.

| Scenario | The "Trap" Failure | The Diagnosis | The Tool to Use |
| :---- | :---- | :---- | :---- |
| **Legacy Refactor** | **Failed "Context Trap"** (0/25) | The agent ignored legacy\_crypto because it wasn't pasted in the chat. | **Augment Code**. Use its Cloud Index to "see" files you don't mention. |
| **New Project (0-1)** | **Failed "Research Trap"** (0/25) | The agent hallucinated the PDF rotation API because it didn't check docs. | **AmpCode**. Its sub-agents are better at reading docs in parallel before coding. |
| **Maintenance** | **Failed "QA Trap"** (0/20) | The agent wrote tests that call the production DB (dangerous). | **OpenCode**. Use the "Loop" feature to grind on the test suite until it passes correctly. |

#### **The Ultimate Workflow: "The Titan Relay"**

Your analysis suggests (and this test will confirm) that no single tool is perfect. The winning strategy is:

1. **AmpCode:** Use to scaffold the project structure (parallel ingest/report creation).  
2. **Augment Code:** Use to implement the complex logic inside ingest.py (ensuring legacy\_crypto is used).  
3. **OpenCode:** Use to write the tests and fix linting errors in a loop until 100% green.