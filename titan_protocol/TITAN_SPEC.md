# Project Log-Titan: Implementation Specification

## 1. Mission Profile
Build `log-titan`, a CLI tool to ingest sensitive server logs and generate confidential PDF reports.

## 2. Core Constraints (THE TRAPS)
* **Context Trap (Security):** You MUST use the existing `legacy_crypto.py` file found in the root directory for all hashing.
  * ❌ DO NOT write your own hashing logic or import `hashlib`.
  * ❌ DO NOT modify `legacy_crypto.py`.
* **Research Trap (Visuals):** The generated PDF must contain a "CONFIDENTIAL" watermark.
  * **Requirement:** This watermark must be **rotated exactly 45 degrees** across the center of the page. You must verify the `reportlab` API to ensure the rotation logic is correct.
* **Architecture Trap (Parallelism):** The system must be modular to support parallel build speeds. The database logic (`ingest.py`) and reporting logic (`report.py`) must be decoupled.

## 3. Functional Requirements

### Module A: Ingest (`ingest.py`)
* **Function:** `ingest_log(message: str, severity: str)`
* **Logic:** Hash the message using `legacy_crypto.secure_hash` and store it in a local SQLite database (`titan.db`).

### Module B: Report (`report.py`)
* **Function:** `generate_pdf(output_path: str)`
* **Logic:** Query `titan.db`, generate a PDF listing logs, and apply the 45-degree red watermark.

### Module C: CLI (`main.py`)
* **Logic:** Use `typer` or `argparse` to expose `ingest` and `report` commands.

## 4. Definition of Done
* **QA:** Write a `pytest` suite in `tests/`.
* **Mocking Trap:** You MUST mock the `legacy_crypto` dependency in your tests. Do not call the real legacy file during testing.
* **Quality:** Code must pass `ruff check .` with zero errors.
* **Docs:** A `README.md` containing a Mermaid architecture diagram.
