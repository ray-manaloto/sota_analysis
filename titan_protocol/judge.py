"""Titan Protocol judge with static analysis scoring."""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

TRUTHY = {"1", "true", "TRUE", "yes", "YES"}
QUALITY_CHECKS = {
    "ruff": 2,
    "modernization": 1,
    "complexity": 1,
    "pylint": 1,
    "dead_code": 1,
    "duplication": 1,
    "type_check": 2,
    "security": 2,
    "coverage": 2,
    "docstyle": 1,
    "semgrep": 1,
    "pip_audit": 1,
    "codespell": 1,
    "ruff_format": 1,
    "isort": 1,
    "license": 1,
}
COVERAGE_MIN = 80.0
VULTURE_MIN_CONFIDENCE = 80
QUALITY_TIMEOUT = 60
EXEC_TIMEOUT = 20
SKIP_DIRS = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pyright",
    ".jscpd-report",
}


def read_text(filepath: Path) -> str:
    """Return UTF-8 text content or empty string if unreadable."""
    try:
        return filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        return ""


def check_file_content(filepath: Path, keywords: list[str]) -> bool:
    """Return True if any keyword appears in the file content."""
    content = read_text(filepath)
    if not content:
        return False
    return any(k in content for k in keywords)


def parse_python(filepath: Path) -> Optional[ast.AST]:
    """Parse a Python file into an AST or return None on failure."""
    content = read_text(filepath)
    if not content:
        return None
    try:
        return ast.parse(content)
    except SyntaxError:
        return None


def dotted_name(node: ast.AST) -> Optional[str]:
    """Return a dotted name for Name/Attribute nodes."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr
    return None


def is_constant_45(node: ast.AST) -> bool:
    """Return True if node is literal 45."""
    return isinstance(node, ast.Constant) and node.value == 45


def has_rotate_45(report_path: Path) -> bool:
    """Return True if report.py rotates by 45 degrees."""
    tree = parse_python(report_path)
    if tree is None:
        return False

    def check_scope(scope: ast.AST) -> bool:
        assignments: dict[str, bool] = {}
        for stmt in getattr(scope, "body", []):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and is_constant_45(stmt.value):
                    assignments[target.id] = True

        for node in ast.walk(scope):
            if not isinstance(node, ast.Call):
                continue
            func_name = dotted_name(node.func)
            if func_name and func_name.endswith("rotate"):
                args = list(node.args)
                if node.keywords:
                    keyword_values = [
                        kw.value for kw in node.keywords if kw.value is not None
                    ]
                    args.extend(keyword_values)
                for arg in args:
                    if is_constant_45(arg):
                        return True
                    if isinstance(arg, ast.Name) and assignments.get(arg.id):
                        return True
        return False

    if check_scope(tree):
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and check_scope(node):
            return True
    return False


def _node_mentions_legacy_crypto(node: ast.AST) -> bool:
    """Return True if node references legacy_crypto."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return "legacy_crypto" in node.value
    if isinstance(node, ast.Name) and node.id == "legacy_crypto":
        return True
    if isinstance(node, ast.Attribute):
        return _node_mentions_legacy_crypto(node.value)
    return False


def mocks_legacy_crypto(tests_dir: Path) -> bool:
    """Return True if tests patch legacy_crypto usage."""
    if not tests_dir.exists():
        return False

    for path in tests_dir.rglob("*.py"):
        tree = parse_python(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = dotted_name(node.func) or ""
            if not func_name:
                continue
            if func_name.endswith("patch") or func_name.endswith("patch.object"):
                for arg in node.args:
                    if _node_mentions_legacy_crypto(arg):
                        return True
                for kw in node.keywords:
                    if kw.value and _node_mentions_legacy_crypto(kw.value):
                        return True
            if func_name.endswith("setattr"):
                for arg in node.args:
                    if _node_mentions_legacy_crypto(arg):
                        return True
    return False


def iter_python_files(root: Path) -> list[Path]:
    """Return Python files under root excluding caches."""
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def run_command(args: list[str], cwd: Path, timeout_seconds: int) -> dict:
    """Run a command and capture structured output."""
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
        }


def run_pytest(run_dir: Path, timeout_seconds: int) -> dict:
    """Run pytest with coverage and capture percent."""
    args = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-q",
        "--cov=.",
        "--cov-report=term",
    ]
    result = run_command(args, run_dir, timeout_seconds)
    result["coverage_percent"] = parse_coverage_percent(result["stdout"])
    return result


def run_smoke(run_dir: Path, timeout_seconds: int) -> dict:
    """Run a basic smoke test without touching the CLI."""
    script = (
        "import ingest, report; "
        "ingest.ingest_log('smoke test', 'INFO'); "
        "report.generate_pdf('smoke_report.pdf'); "
        "print('ok')"
    )
    return run_command([sys.executable, "-c", script], run_dir, timeout_seconds)


def parse_coverage_percent(output: str) -> Optional[float]:
    """Parse pytest-cov TOTAL percent from output."""
    for line in output.splitlines():
        if not line.strip().startswith("TOTAL"):
            continue
        tokens = line.split()
        for token in tokens:
            if token.endswith("%"):
                try:
                    return float(token.rstrip("%"))
                except ValueError:
                    return None
    return None


def ensure_tool(
    command: str,
    package: str,
    allow_install: bool,
    installer: str = "pip",
) -> bool:
    """Ensure a tool exists, optionally installing it."""
    if shutil.which(command):
        return True
    if not allow_install:
        return False
    if installer == "npm":
        if not shutil.which("npm"):
            return False
        print(f"Missing tool: {command}. Attempting install via npm ({package})...")
        result = subprocess.run(
            ["npm", "install", "-g", package],
            capture_output=True,
            text=True,
        )
    else:
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


def init_quality_breakdown() -> dict:
    """Return an empty quality breakdown payload."""
    return {
        "max_points": sum(QUALITY_CHECKS.values()),
        "score": 0,
        "checks": {},
    }


def add_quality_check(
    breakdown: dict,
    name: str,
    ok: bool,
    details: Optional[dict] = None,
    skipped: bool = False,
) -> None:
    """Add a quality check result to the breakdown."""
    points = QUALITY_CHECKS[name]
    earned = points if ok else 0
    breakdown["checks"][name] = {
        "points": points,
        "earned": earned,
        "ok": ok,
        "skipped": skipped,
        "details": details or {},
    }
    breakdown["score"] += earned


def run_ruff_check(run_dir: Path, select: Optional[str] = None) -> dict:
    """Run ruff with optional selector."""
    args = ["ruff", "check", "."]
    if select:
        args.extend(["--select", select])
    result = run_command(args, run_dir, QUALITY_TIMEOUT)
    result["errors"] = len(result["stdout"].splitlines())
    return result


def run_pylint_check(run_dir: Path) -> dict:
    """Run pylint against project Python files."""
    files = [str(path) for path in iter_python_files(run_dir)]
    if not files:
        return {
            "ok": True,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "timeout": False,
        }
    args = ["pylint", "--rcfile", ".pylintrc", *files]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_xenon_check(run_dir: Path) -> dict:
    """Run xenon complexity gates."""
    args = [
        "xenon",
        "--max-absolute",
        "B",
        "--max-modules",
        "B",
        "--max-average",
        "A",
        ".",
    ]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_vulture_check(run_dir: Path) -> dict:
    """Run vulture dead-code detection."""
    files = [str(path) for path in iter_python_files(run_dir)]
    if not files:
        return {
            "ok": True,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "timeout": False,
        }
    args = ["vulture", "--min-confidence", str(VULTURE_MIN_CONFIDENCE), *files]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_jscpd_check(run_dir: Path) -> dict:
    """Run jscpd duplication detection and parse report."""
    output_dir = run_dir / ".jscpd-report"
    output_dir.mkdir(exist_ok=True)
    args = [
        "jscpd",
        "--config",
        ".jscpd.json",
        ".",
    ]
    result = run_command(args, run_dir, QUALITY_TIMEOUT)
    report = parse_jscpd_report(output_dir)
    if report:
        result["duplicates"] = report.get("duplicates")
        result["percentage"] = report.get("percentage")
    return result


def parse_jscpd_report(output_dir: Path) -> dict:
    """Parse jscpd JSON report into summary stats."""
    candidates = [
        output_dir / "jscpd-report.json",
        output_dir / "report.json",
        output_dir / "jscpd.json",
    ]
    report_path = next((path for path in candidates if path.exists()), None)
    if not report_path:
        return {}
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, list):
        return {"duplicates": len(data), "percentage": None}
    if isinstance(data, dict):
        stats = data.get("statistics", {}) or {}
        total = stats.get("total", {}) or {}
        duplicates = (
            total.get("clones")
            or total.get("duplicates")
            or total.get("duplicatedLines")
        )
        percentage = total.get("percentage") or total.get("percentageOfDuplication")
        return {"duplicates": duplicates, "percentage": percentage}
    return {}


def run_mypy_check(run_dir: Path) -> dict:
    """Run mypy with config file."""
    args = ["mypy", "--config-file", "mypy.ini", "."]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_pyright_check(run_dir: Path) -> dict:
    """Run pyright with config file."""
    args = ["pyright", "--project", "pyrightconfig.json"]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_bandit_check(run_dir: Path) -> dict:
    """Run bandit security scan."""
    args = ["bandit", "-r", ".", "-c", "bandit.yaml"]
    result = run_command(args, run_dir, QUALITY_TIMEOUT)
    high_issues = sum(
        1 for line in result["stdout"].splitlines() if "Severity: HIGH" in line
    )
    result["high_issues"] = high_issues
    return result


def run_semgrep_check(run_dir: Path) -> dict:
    """Run semgrep with auto ruleset."""
    args = [
        "semgrep",
        "--config",
        "auto",
        "--severity",
        "ERROR",
        "--metrics",
        "off",
        ".",
    ]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_pip_audit_check(run_dir: Path) -> dict:
    """Run pip-audit against current environment."""
    args = ["pip-audit", "--format", "json"]
    result = run_command(args, run_dir, QUALITY_TIMEOUT)
    vulnerabilities = None
    try:
        payload = json.loads(result["stdout"])
        vulnerabilities = len(payload)
    except json.JSONDecodeError:
        vulnerabilities = None
    result["vulnerabilities"] = vulnerabilities
    return result


def run_codespell_check(run_dir: Path) -> dict:
    """Run codespell for spelling issues."""
    args = ["codespell", "--config", ".codespellrc", "."]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_ruff_format_check(run_dir: Path) -> dict:
    """Run ruff format check."""
    args = ["ruff", "format", "--check", "."]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_isort_check(run_dir: Path) -> dict:
    """Run isort check."""
    args = ["isort", ".", "--check-only"]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def run_license_check(run_dir: Path) -> dict:
    """Run pip-licenses to capture dependency license info."""
    args = ["pip-licenses", "--format", "json"]
    result = run_command(args, run_dir, QUALITY_TIMEOUT)
    package_count = None
    try:
        payload = json.loads(result["stdout"])
        package_count = len(payload)
    except json.JSONDecodeError:
        package_count = None
    result["packages"] = package_count
    return result


def run_pydocstyle_check(run_dir: Path) -> dict:
    """Run pydocstyle docstring check."""
    args = ["pydocstyle", "--config", ".pydocstyle"]
    return run_command(args, run_dir, QUALITY_TIMEOUT)


def evaluate_quality(
    run_dir: Path,
    allow_install: bool,
    run_exec: bool,
    exec_results: dict,
) -> tuple[dict, Optional[int]]:
    """Evaluate quality checks and return breakdown plus ruff errors."""
    breakdown = init_quality_breakdown()
    ruff_errors = None
    if not run_exec:
        for name in QUALITY_CHECKS:
            add_quality_check(
                breakdown,
                name,
                ok=False,
                skipped=True,
                details={"reason": "execution disabled"},
            )
        return breakdown, ruff_errors

    if ensure_tool("ruff", "ruff", allow_install):
        res = run_ruff_check(run_dir)
        ruff_errors = res.get("errors")
        add_quality_check(
            breakdown,
            "ruff",
            ok=res["ok"],
            details={"errors": ruff_errors},
        )
        res_mod = run_ruff_check(run_dir, select="UP")
        add_quality_check(
            breakdown,
            "modernization",
            ok=res_mod["ok"],
            details={"errors": res_mod.get("errors")},
        )
        res_c90 = run_ruff_check(run_dir, select="C90")
        ruff_complexity_ok = res_c90["ok"]
    else:
        ruff_complexity_ok = None
        for name in ("ruff", "modernization"):
            add_quality_check(
                breakdown,
                name,
                ok=False,
                skipped=True,
                details={"reason": "ruff missing"},
            )

    if ensure_tool("xenon", "xenon", allow_install):
        xenon_res = run_xenon_check(run_dir)
        if ruff_complexity_ok is None:
            add_quality_check(
                breakdown,
                "complexity",
                ok=False,
                skipped=True,
                details={"reason": "ruff missing"},
            )
        else:
            complexity_ok = xenon_res["ok"] and ruff_complexity_ok
            add_quality_check(
                breakdown,
                "complexity",
                ok=complexity_ok,
                details={
                    "xenon_ok": xenon_res["ok"],
                    "ruff_c90_ok": ruff_complexity_ok,
                },
            )
    else:
        add_quality_check(
            breakdown,
            "complexity",
            ok=False,
            skipped=True,
            details={"reason": "xenon missing"},
        )

    if ensure_tool("pylint", "pylint", allow_install):
        pylint_res = run_pylint_check(run_dir)
        add_quality_check(
            breakdown,
            "pylint",
            ok=pylint_res["ok"],
            details={"returncode": pylint_res["returncode"]},
        )
    else:
        add_quality_check(
            breakdown,
            "pylint",
            ok=False,
            skipped=True,
            details={"reason": "pylint missing"},
        )

    if ensure_tool("vulture", "vulture", allow_install):
        vulture_res = run_vulture_check(run_dir)
        add_quality_check(
            breakdown,
            "dead_code",
            ok=vulture_res["ok"],
            details={"returncode": vulture_res["returncode"]},
        )
    else:
        add_quality_check(
            breakdown,
            "dead_code",
            ok=False,
            skipped=True,
            details={"reason": "vulture missing"},
        )

    if ensure_tool("jscpd", "jscpd", allow_install, installer="npm"):
        jscpd_res = run_jscpd_check(run_dir)
        duplicates = jscpd_res.get("duplicates")
        if isinstance(duplicates, int):
            ok = duplicates == 0
        else:
            ok = jscpd_res["ok"]
        add_quality_check(
            breakdown,
            "duplication",
            ok=ok,
            details={"duplicates": duplicates},
        )
    else:
        add_quality_check(
            breakdown,
            "duplication",
            ok=False,
            skipped=True,
            details={"reason": "jscpd missing"},
        )

    if ensure_tool("mypy", "mypy", allow_install) and ensure_tool(
        "pyright",
        "pyright",
        allow_install,
    ):
        mypy_res = run_mypy_check(run_dir)
        pyright_res = run_pyright_check(run_dir)
        add_quality_check(
            breakdown,
            "type_check",
            ok=mypy_res["ok"] and pyright_res["ok"],
            details={"mypy_ok": mypy_res["ok"], "pyright_ok": pyright_res["ok"]},
        )
    else:
        add_quality_check(
            breakdown,
            "type_check",
            ok=False,
            skipped=True,
            details={"reason": "mypy or pyright missing"},
        )

    if ensure_tool("bandit", "bandit", allow_install):
        bandit_res = run_bandit_check(run_dir)
        add_quality_check(
            breakdown,
            "security",
            ok=bandit_res.get("high_issues", 0) == 0,
            details={
                "returncode": bandit_res["returncode"],
                "high_issues": bandit_res.get("high_issues"),
            },
        )
    else:
        add_quality_check(
            breakdown,
            "security",
            ok=False,
            skipped=True,
            details={"reason": "bandit missing"},
        )

    pytest_res = exec_results.get("pytest") if exec_results else None
    coverage_percent = None
    if pytest_res:
        coverage_percent = pytest_res.get("coverage_percent")
    coverage_ok = coverage_percent is not None and coverage_percent >= COVERAGE_MIN
    add_quality_check(
        breakdown,
        "coverage",
        ok=coverage_ok,
        details={"coverage_percent": coverage_percent, "min": COVERAGE_MIN},
    )

    if ensure_tool("pydocstyle", "pydocstyle", allow_install):
        doc_res = run_pydocstyle_check(run_dir)
        add_quality_check(
            breakdown,
            "docstyle",
            ok=doc_res["ok"],
            details={"returncode": doc_res["returncode"]},
        )
    else:
        add_quality_check(
            breakdown,
            "docstyle",
            ok=False,
            skipped=True,
            details={"reason": "pydocstyle missing"},
        )

    if ensure_tool("semgrep", "semgrep", allow_install):
        semgrep_res = run_semgrep_check(run_dir)
        add_quality_check(
            breakdown,
            "semgrep",
            ok=semgrep_res["ok"],
            details={"returncode": semgrep_res["returncode"]},
        )
    else:
        add_quality_check(
            breakdown,
            "semgrep",
            ok=False,
            skipped=True,
            details={"reason": "semgrep missing"},
        )

    if ensure_tool("pip-audit", "pip-audit", allow_install):
        audit_res = run_pip_audit_check(run_dir)
        add_quality_check(
            breakdown,
            "pip_audit",
            ok=audit_res["ok"],
            details={
                "returncode": audit_res["returncode"],
                "vulnerabilities": audit_res.get("vulnerabilities"),
            },
        )
    else:
        add_quality_check(
            breakdown,
            "pip_audit",
            ok=False,
            skipped=True,
            details={"reason": "pip-audit missing"},
        )

    if ensure_tool("codespell", "codespell", allow_install):
        codespell_res = run_codespell_check(run_dir)
        add_quality_check(
            breakdown,
            "codespell",
            ok=codespell_res["ok"],
            details={"returncode": codespell_res["returncode"]},
        )
    else:
        add_quality_check(
            breakdown,
            "codespell",
            ok=False,
            skipped=True,
            details={"reason": "codespell missing"},
        )

    if ensure_tool("ruff", "ruff", allow_install):
        format_res = run_ruff_format_check(run_dir)
        add_quality_check(
            breakdown,
            "ruff_format",
            ok=format_res["ok"],
            details={"returncode": format_res["returncode"]},
        )
    else:
        add_quality_check(
            breakdown,
            "ruff_format",
            ok=False,
            skipped=True,
            details={"reason": "ruff missing"},
        )

    if ensure_tool("isort", "isort", allow_install):
        isort_res = run_isort_check(run_dir)
        add_quality_check(
            breakdown,
            "isort",
            ok=isort_res["ok"],
            details={"returncode": isort_res["returncode"]},
        )
    else:
        add_quality_check(
            breakdown,
            "isort",
            ok=False,
            skipped=True,
            details={"reason": "isort missing"},
        )

    if ensure_tool("pip-licenses", "pip-licenses", allow_install):
        license_res = run_license_check(run_dir)
        add_quality_check(
            breakdown,
            "license",
            ok=license_res["ok"],
            details={
                "returncode": license_res["returncode"],
                "packages": license_res.get("packages"),
            },
        )
    else:
        add_quality_check(
            breakdown,
            "license",
            ok=False,
            skipped=True,
            details={"reason": "pip-licenses missing"},
        )

    return breakdown, ruff_errors


def score_titan(
    run_dir: Path | None = None,
    run_exec: bool = True,
    write_json: bool = True,
) -> dict:
    """Score a run directory against Titan Protocol criteria."""
    run_dir = Path(run_dir) if run_dir else Path(".")
    score = 0
    report: list[str] = []
    details: dict[str, int] = {}
    print("\n⚔️  TITAN PROTOCOL JUDGEMENT  ⚔️\n")

    ingest_path = run_dir / "ingest.py"
    if check_file_content(ingest_path, ["legacy_crypto", "secure_hash"]):
        score += 25
        details["context"] = 25
        report.append("✅ [25/25] Context Trap Passed (Used Legacy Crypto)")
    else:
        details["context"] = 0
        report.append("❌ [0/25] Context Trap Failed (Ignored/Rewrote Legacy File)")

    report_path = run_dir / "report.py"
    if has_rotate_45(report_path):
        score += 25
        details["research"] = 25
        report.append("✅ [25/25] Research Trap Passed (Watermark Rotated)")
    else:
        details["research"] = 0
        report.append("❌ [0/25] Research Trap Failed (No Rotation Logic)")

    tests_dir = run_dir / "tests"
    if mocks_legacy_crypto(tests_dir):
        score += 20
        details["qa"] = 20
        report.append("✅ [20/20] QA Trap Passed (Dependency Mocked)")
    else:
        details["qa"] = 0
        report.append("❌ [0/20] QA Trap Failed (Real Code Called in Tests)")

    exec_results = {"pytest": None, "smoke": None, "skipped": not run_exec}
    if run_exec:
        exec_results["pytest"] = run_pytest(run_dir, timeout_seconds=EXEC_TIMEOUT)
        exec_results["smoke"] = run_smoke(run_dir, timeout_seconds=EXEC_TIMEOUT)

    allow_install = os.getenv("TITAN_NO_INSTALL") not in TRUTHY
    quality_breakdown, ruff_errors = evaluate_quality(
        run_dir=run_dir,
        allow_install=allow_install,
        run_exec=run_exec,
        exec_results=exec_results,
    )
    quality_score = quality_breakdown["score"]
    score += quality_score
    details["quality"] = quality_score
    report.append(f"⚠️ [{quality_score}/20] Quality Checks (see judge.json)")

    readme_path = run_dir / "README.md"
    if check_file_content(readme_path, ["mermaid", "graph TD"]):
        score += 10
        details["docs"] = 10
        report.append("✅ [10/10] Documentation Passed (Mermaid Diagram)")
    else:
        details["docs"] = 0
        report.append("❌ [0/10] Documentation Failed (No Diagram)")

    print("-" * 40)
    for line in report:
        print(line)
    print("-" * 40)
    print(f"🏆 FINAL SCORE: {score}/100")

    payload = {
        "score": score,
        "context": details.get("context", 0),
        "research": details.get("research", 0),
        "qa": details.get("qa", 0),
        "quality": details.get("quality", 0),
        "docs": details.get("docs", 0),
        "ruff_errors": ruff_errors,
        "execution": exec_results,
        "quality_breakdown": quality_breakdown,
    }
    if write_json:
        (run_dir / "judge.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    return payload


if __name__ == "__main__":
    skip_exec = os.getenv("TITAN_SKIP_EXEC") in TRUTHY
    score_titan(run_exec=not skip_exec)
