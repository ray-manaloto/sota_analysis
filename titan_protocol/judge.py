import os
import subprocess
import sys


def check_file_content(filepath, keywords):
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return False
    return any(k in content for k in keywords)


def ensure_tool(command, package, allow_install):
    try:
        subprocess.run([command, "--version"], capture_output=True, text=True, check=False)
        return True
    except FileNotFoundError:
        if not allow_install:
            return False
        print(f"Missing tool: {command}. Attempting install via pip ({package})...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            return False
        return True


def score_titan():
    score = 0
    report = []
    print("\n⚔️  TITAN PROTOCOL JUDGEMENT  ⚔️\n")

    # TRAP 1: CONTEXT (25 pts)
    # Did it import the legacy file?
    if check_file_content("ingest.py", ["legacy_crypto", "secure_hash"]):
        score += 25
        report.append("✅ [25/25] Context Trap Passed (Used Legacy Crypto)")
    else:
        report.append("❌ [0/25] Context Trap Failed (Ignored/Rewrote Legacy File)")

    # TRAP 2: RESEARCH (25 pts)
    # Did it find the rotate method?
    if check_file_content("report.py", ["rotate(45)", "rotate=45"]):
        score += 25
        report.append("✅ [25/25] Research Trap Passed (Watermark Rotated)")
    else:
        report.append("❌ [0/25] Research Trap Failed (No Rotation Logic)")

    # TRAP 3: QA MOCKING (20 pts)
    # Did it mock the dependency?
    mock_found = False
    if os.path.exists("tests"):
        for root, _, files in os.walk("tests"):
            for file in files:
                if not file.endswith(".py"):
                    continue
                if check_file_content(os.path.join(root, file), ["mock", "patch"]):
                    mock_found = True
    if mock_found:
        score += 20
        report.append("✅ [20/20] QA Trap Passed (Dependency Mocked)")
    else:
        report.append("❌ [0/20] QA Trap Failed (Real Code Called in Tests)")

    # TRAP 4: QUALITY (20 pts)
    # Does it pass Ruff?
    allow_install = os.getenv("TITAN_NO_INSTALL") not in {"1", "true", "TRUE", "yes", "YES"}
    if ensure_tool("ruff", "ruff", allow_install):
        res = subprocess.run(["ruff", "check", "."], capture_output=True, text=True)
        if res.returncode == 0:
            score += 20
            report.append("✅ [20/20] Linter Passed (Zero Errors)")
        else:
            err_count = len(res.stdout.splitlines())
            points = max(0, 20 - (err_count * 2))
            score += points
            report.append(f"⚠️ [{points}/20] Linter Failed ({err_count} errors)")
    else:
        report.append("⚠️ [0/20] Ruff not installed (Skipped)")

    # TRAP 5: DOCS (10 pts)
    if check_file_content("README.md", ["mermaid", "graph TD"]):
        score += 10
        report.append("✅ [10/10] Documentation Passed (Mermaid Diagram)")
    else:
        report.append("❌ [0/10] Documentation Failed (No Diagram)")

    print("-" * 40)
    for line in report:
        print(line)
    print("-" * 40)
    print(f"🏆 FINAL SCORE: {score}/100")


if __name__ == "__main__":
    score_titan()
