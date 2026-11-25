"""Regression coverage for file-based OpenStudio run status handling."""

from __future__ import annotations

import json
from pathlib import Path

from garden.manifest import GardenManifest
from garden.run_energy import files


def _garden_with_osm(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "garden"
    root.mkdir()
    GardenManifest.new("OSM file run status test").write(root)
    osm_path = root / "model.osm"
    osm_path.write_text("OS:Version, {3.10.0};\n", encoding="utf-8")
    epw_path = root / "weather.epw"
    epw_path.write_text("weather fixture\n", encoding="utf-8")
    run_dir = root / "run"
    run_dir.mkdir()
    return root, osm_path, epw_path, run_dir


def test_osm_file_run_fails_on_osw_status_without_step_errors(
    tmp_path: Path, monkeypatch
) -> None:
    root, osm_path, epw_path, run_dir = _garden_with_osm(tmp_path)

    def fake_run_osw(osw_path: str, *, measures_only: bool, silent: bool) -> tuple[str, str]:
        del measures_only, silent
        workflow_dir = Path(osw_path).parent
        run_dir = workflow_dir / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        (workflow_dir / "out.osw").write_text(
            json.dumps({"completed_status": "Fail", "steps": []}),
            encoding="utf-8",
        )
        (run_dir / "in.osm").write_text("OS:Version, {3.10.0};\n", encoding="utf-8")
        (run_dir / "in.idf").write_text("Version, 25.1;\n", encoding="utf-8")
        (run_dir / "eplusout.sql").write_bytes(b"partial sql output")
        (run_dir / "eplusout.err").write_text("", encoding="utf-8")
        return str(run_dir / "in.osm"), str(run_dir / "in.idf")

    monkeypatch.setattr(files, "run_osw", fake_run_osw)
    result = files.run_osm_file(
        garden_root=str(root),
        osm_path=str(osm_path),
        epw_path=str(epw_path),
        run_id="engine_failure",
    )

    assert result["summary_view"]["status"] == "failed"
    assert result["report"]["status"] == "error"
    warnings = result["report"]["warnings"]
    assert any("completed_status is Fail" in warning for warning in warnings)
    assert not any("Could not parse out.osw" in warning for warning in warnings)
    outputs = result["summary_view"]["outputs"]
    assert outputs["sql"]["exists"] is True
    assert outputs["err"]["exists"] is True
    assert outputs["run_log"]["exists"] is False
    assert outputs["failed_job"]["exists"] is False


def test_osm_file_run_fails_on_energyplus_termination(
    tmp_path: Path, monkeypatch
) -> None:
    root, osm_path, epw_path, run_dir = _garden_with_osm(tmp_path)

    def fake_run_osw(osw_path: str, *, measures_only: bool, silent: bool) -> tuple[str, str]:
        del measures_only, silent
        workflow_dir = Path(osw_path).parent
        run_dir = workflow_dir / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        (workflow_dir / "out.osw").write_text(
            json.dumps({"completed_status": "Success", "steps": []}),
            encoding="utf-8",
        )
        (run_dir / "in.osm").write_text("OS:Version, {3.10.0};\n", encoding="utf-8")
        (run_dir / "in.idf").write_text("Version, 25.1;\n", encoding="utf-8")
        (run_dir / "eplusout.sql").write_bytes(b"partial sql output")
        (run_dir / "eplusout.err").write_text("", encoding="utf-8")
        (run_dir / "run.log").write_text(
            "[WARN] EnergyPlus returned a non-zero exit code (-1073741819).\n"
            "[FATAL] EnergyPlus Terminated with a Fatal Error.\n",
            encoding="utf-8",
        )
        (run_dir / "failed.job").write_text("Failed Workflow\n", encoding="utf-8")
        return str(run_dir / "in.osm"), str(run_dir / "in.idf")

    monkeypatch.setattr(files, "run_osw", fake_run_osw)
    result = files.run_osm_file(
        garden_root=str(root),
        osm_path=str(osm_path),
        epw_path=str(epw_path),
        run_id="engine_termination",
    )

    assert result["summary_view"]["status"] == "failed"
    assert result["report"]["status"] == "error"
    warnings = result["report"]["warnings"]
    assert any(
        "-1073741819" in warning and "run/run.log" in warning
        for warning in warnings
    )
    assert not any("completed_status is Fail" in warning for warning in warnings)
    outputs = result["summary_view"]["outputs"]
    assert outputs["sql"]["exists"] is True
    assert outputs["err"]["exists"] is True
    assert outputs["run_log"]["path"] == "run/run.log"
    assert outputs["failed_job"]["path"] == "run/failed.job"
    assert (run_dir / "run.log").is_file()


def test_osm_measures_only_success_ignores_stale_failure_markers(
    tmp_path: Path, monkeypatch
) -> None:
    root, osm_path, epw_path, run_dir = _garden_with_osm(tmp_path)
    (run_dir / "run.log").write_text(
        "EnergyPlus returned a non-zero exit code (-1).\n", encoding="utf-8"
    )
    (run_dir / "failed.job").write_text("Previous failed run\n", encoding="utf-8")
    stale_out_osw = osm_path.parent / "out.osw"
    stale_out_osw.write_text(
        json.dumps({"completed_status": "Fail", "steps": []}), encoding="utf-8"
    )

    def fake_run_osw(osw_path: str, *, measures_only: bool, silent: bool) -> tuple[str, None]:
        assert measures_only is True
        del silent
        workflow_dir = Path(osw_path).parent
        run_dir = workflow_dir / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        osm_result = run_dir / "in.osm"
        osm_result.write_text("OS:Version, {3.10.0};\n", encoding="utf-8")
        return str(osm_result), None

    monkeypatch.setattr(files, "run_osw", fake_run_osw)
    result = files.run_osm_file(
        garden_root=str(root),
        osm_path=str(osm_path),
        epw_path=str(epw_path),
        measures_only=True,
        run_id="measures_only_success",
    )

    assert result["summary_view"]["status"] == "completed"
    assert result["report"]["status"] == "ok"
    assert result["summary_view"]["outputs"]["osm"]["exists"] is True
    assert result["summary_view"]["outputs"]["run_log"]["exists"] is False
    assert result["summary_view"]["outputs"]["failed_job"]["exists"] is False
    assert not (run_dir / "run.log").exists()
    assert not (run_dir / "failed.job").exists()
    assert not stale_out_osw.exists()
