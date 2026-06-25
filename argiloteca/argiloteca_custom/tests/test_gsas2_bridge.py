from pathlib import Path

from argiloteca.services import drx_gsas2_bridge


def test_gsas2_status_missing_python(monkeypatch, tmp_path):
    monkeypatch.setenv("ARGILOTECA_GSAS2_PYTHON", str(tmp_path / "missing-python"))
    payload = drx_gsas2_bridge.gsas2_status(timeout_seconds=1)
    assert payload["engine"] == "gsas2"
    assert payload["policy"] == "auxiliary_not_confirmatory"
    assert payload["available"] is False
    assert payload["warnings"]


def test_compare_argiloteca_to_gsas2_compatible(tmp_path):
    pattern = tmp_path / "synthetic.xy"
    rows = [f"{5 + index * 0.1:.1f} {100 + index}\n" for index in range(101)]
    pattern.write_text("".join(rows), encoding="utf-8")
    payload = drx_gsas2_bridge.compare_argiloteca_to_gsas2(
        pattern,
        {
            "histogram_summary": {
                "number_of_points": 101,
                "x_min": 5.0,
                "x_max": 15.0,
                "y_max": 200.0,
            }
        },
    )
    assert payload["policy"] == "auxiliary_not_confirmatory"
    assert payload["comparison"]["status"] == "compatible"


def test_submit_gsas2_pattern_validation_registers_job(monkeypatch, tmp_path):
    pattern = tmp_path / "synthetic.xy"
    rows = [f"{5 + index * 0.1:.1f} {100 + index}\n" for index in range(101)]
    pattern.write_text("".join(rows), encoding="utf-8")
    monkeypatch.setenv("ARGILOTECA_DRX_JOBS_DIR", str(tmp_path / "jobs"))
    payload = drx_gsas2_bridge.submit_gsas2_pattern_validation({"pattern_path": str(pattern)})
    assert payload["policy"] == "auxiliary_not_confirmatory"
    assert payload["success"] is True
    assert payload["job"]["engine"] == "gsas2"
    assert payload["job"]["request"]["pattern_path"] == str(pattern)
