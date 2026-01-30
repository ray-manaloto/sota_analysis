import json
from pathlib import Path
import importlib.util


def load_run_test_module():
    run_test_path = Path(__file__).resolve().parents[1] / "run_test.py"
    spec = importlib.util.spec_from_file_location("titan_run_test", run_test_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_load_judge_json(tmp_path):
    rt = load_run_test_module()
    judge_json = tmp_path / "judge.json"
    payload = {
        "score": 88,
        "context": 25,
        "research": 25,
        "qa": 20,
        "quality": 8,
        "docs": 10,
        "ruff_errors": 1,
        "quality_breakdown": {
            "checks": {
                "ruff": {"points": 2, "ok": True},
                "modernization": {"points": 2, "ok": False},
                "semgrep": {"points": 1, "ok": True},
            }
        },
    }
    judge_json.write_text(json.dumps(payload), encoding="utf-8")
    parsed = rt.load_judge_json(tmp_path)
    assert parsed["score"] == 88
    assert parsed["quality"] == 8
    assert parsed["ruff_errors"] == 1
    assert parsed["quality_breakdown"]["checks"]["ruff"]["ok"] is True


def test_apply_pytest_failure_caps_quality():
    rt = load_run_test_module()
    score = {
        "context": 25,
        "research": 25,
        "qa": 20,
        "quality": 20,
        "docs": 10,
        "final": 100,
        "ruff_errors": None,
        "quality_breakdown": {
            "score": 20,
            "checks": {"ruff": {"earned": 2}, "pylint": {"earned": 2}},
        },
    }
    payload = {"execution": {"pytest": {"ok": False}}}
    capped = rt.apply_pytest_cap(score, payload)
    assert capped["quality"] == 0
    assert capped["final"] == 80
    assert capped["quality_breakdown"]["score"] == 0
    assert capped["quality_breakdown"]["checks"]["ruff"]["earned"] == 0
