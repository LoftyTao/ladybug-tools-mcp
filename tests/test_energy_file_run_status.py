"""Regression coverage for file-based OpenStudio run status handling."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from garden.manifest import GardenManifest
from garden.run_energy import files, results
from garden.run_energy.annual import _absolute_output_path, _run_record_by_id


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


@pytest.mark.parametrize(
    ("suffix", "contents", "engine", "old_version"),
    [
        (
            ".osm",
            "OS:Version,\n {751cdc50-66f8-4f8f-ad43-1b184ceb7656}, !- Handle\n 3.11.0;",
            "OpenStudio",
            "3.10.0",
        ),
        (".idf", "! VERSION, 24.1;\nTimestep, 6;\nVersion, 25.2; !- Version", "EnergyPlus", "25.1.0"),
    ],
)
def test_newer_export_is_blocked_before_engine_or_run_directory_changes(
    tmp_path, monkeypatch, suffix, contents, engine, old_version
) -> None:
    root, _, epw, run_dir = _garden_with_osm(tmp_path)
    model = root / f"new{suffix}"
    model.write_text(contents, encoding="utf-8")
    previous_sql = run_dir / "eplusout.sql"
    previous_sql.write_bytes(b"previous run evidence")
    monkeypatch.setattr(
        files, "energy_folders",
        SimpleNamespace(openstudio_version_str="3.10.0", energyplus_version_str="25.1.0"),
    )

    def unexpected_run(*args, **kwargs):
        pytest.fail("Engine was invoked after a blocked version preflight")

    monkeypatch.setattr(files, "run_osw", unexpected_run)
    monkeypatch.setattr(files, "run_idf", unexpected_run)
    reply = files.run_simulation_file(
        garden_root=str(root), file_path=str(model), epw_path=str(epw), run_id="blocked_version"
    )

    info = reply["summary_view"]["preflight"]
    assert (info["status"], info["engine"], info["runtime_version"]) == ("blocked", engine, old_version)
    assert info["code"] == "input_version_newer_than_runtime"
    assert reply["summary_view"]["status"] == "failed"
    assert reply["summary_view"]["run_folder"] is None
    stored = _run_record_by_id(root, "blocked_version")
    assert stored["preflight"] == info
    assert previous_sql.read_bytes() == b"previous run evidence"
    with pytest.raises(ValueError, match="no owned sql output"):
        _absolute_output_path(root, stored, "sql")
    with pytest.raises(ValueError, match="has not completed successfully"):
        results.read_energy_result_data(garden_root=str(root), run_id="blocked_version")


@pytest.mark.parametrize(
    ("err_text", "valid_sql", "expected"),
    [
        ("", True, "failed"),
        ("** Fatal ** Invalid input\nEnergyPlus Terminated.", True, "failed"),
        ("EnergyPlus Completed Successfully", False, "failed"),
        ("EnergyPlus Completed Successfully", True, "completed"),
    ],
)
def test_idf_status_requires_real_completion_evidence(tmp_path, monkeypatch, err_text, valid_sql, expected):
    root, _, _, _ = _garden_with_osm(tmp_path)
    model = root / "model.idf"
    model.write_text("Version, 25.1;", encoding="utf-8")
    monkeypatch.setattr(files, "energy_folders", SimpleNamespace(energyplus_version_str="25.1.0"))

    def fake_run_idf(idf_path, *args, **kwargs):
        run_dir = Path(idf_path).parent
        sql = run_dir / "eplusout.sql"
        err = run_dir / "eplusout.err"
        if valid_sql:
            with sqlite3.connect(sql) as conn:
                conn.execute("CREATE TABLE simulation (id INTEGER)")
        else:
            sql.write_text("unreadable SQL", encoding="utf-8")
        err.write_text(err_text, encoding="utf-8")
        return str(sql), None, None, None, str(err)

    monkeypatch.setattr(files, "run_idf", fake_run_idf)
    reply = files.run_idf_file(garden_root=str(root), idf_path=str(model))
    assert reply["summary_view"]["status"] == expected
    assert reply["summary_view"]["outputs"]["err"]["exists"]
