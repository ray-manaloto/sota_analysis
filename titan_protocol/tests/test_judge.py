import json
from pathlib import Path
import importlib.util


def load_judge_module():
    judge_path = Path(__file__).resolve().parents[1] / "judge.py"
    spec = importlib.util.spec_from_file_location("titan_judge", judge_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_has_rotate_45_detects_constant(tmp_path):
    judge = load_judge_module()
    report_path = tmp_path / "report.py"
    report_path.write_text("""
from reportlab.pdfgen import canvas
c = canvas.Canvas('x')
c.rotate(45)
""", encoding="utf-8")
    assert judge.has_rotate_45(report_path)


def test_has_rotate_45_detects_variable(tmp_path):
    judge = load_judge_module()
    report_path = tmp_path / "report.py"
    report_path.write_text("""
from reportlab.pdfgen import canvas
c = canvas.Canvas('x')
angle = 45
c.rotate(angle)
""", encoding="utf-8")
    assert judge.has_rotate_45(report_path)


def test_has_rotate_45_rejects_other(tmp_path):
    judge = load_judge_module()
    report_path = tmp_path / "report.py"
    report_path.write_text("""
from reportlab.pdfgen import canvas
c = canvas.Canvas('x')
angle = 90
c.rotate(angle)
""", encoding="utf-8")
    assert judge.has_rotate_45(report_path) is False


def test_mocks_legacy_crypto_detects_patch(tmp_path):
    judge = load_judge_module()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_ingest.py"
    test_file.write_text("""
from unittest.mock import patch

def test_ingest():
    with patch('legacy_crypto.secure_hash') as mock_hash:
        mock_hash.return_value = 'x'
        assert mock_hash('hi') == 'x'
""", encoding="utf-8")
    assert judge.mocks_legacy_crypto(tests_dir)


def test_mocks_legacy_crypto_rejects_comment(tmp_path):
    judge = load_judge_module()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_ingest.py"
    test_file.write_text("""
# mock legacy_crypto here

def test_ingest():
    assert True
""", encoding="utf-8")
    assert judge.mocks_legacy_crypto(tests_dir) is False


def test_score_titan_writes_json(tmp_path):
    judge = load_judge_module()
    (tmp_path / "ingest.py").write_text("import legacy_crypto\n", encoding="utf-8")
    (tmp_path / "report.py").write_text("""
from reportlab.pdfgen import canvas
c = canvas.Canvas('x')
c.rotate(45)
""", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_stub = "from unittest.mock import patch\n"
    (tests_dir / "test_stub.py").write_text(test_stub, encoding="utf-8")
    (tmp_path / "README.md").write_text("```mermaid\ngraph TD\n```", encoding="utf-8")

    result = judge.score_titan(run_dir=tmp_path, run_exec=False, write_json=True)
    assert result["score"] >= 60
    judge_json = tmp_path / "judge.json"
    assert judge_json.exists()
    data = json.loads(judge_json.read_text(encoding="utf-8"))
    assert data["score"] == result["score"]
    assert "context" in data
    assert "research" in data
    assert "qa" in data
    assert "docs" in data
    assert "quality_breakdown" in data
    quality_checks = data["quality_breakdown"].get("checks", {})
    expected = {
        "ruff",
        "modernization",
        "complexity",
        "pylint",
        "dead_code",
        "duplication",
        "type_check",
        "security",
        "coverage",
        "docstyle",
        "semgrep",
        "pip_audit",
        "codespell",
        "ruff_format",
        "isort",
        "license",
    }
    assert expected.issubset(set(quality_checks.keys()))
