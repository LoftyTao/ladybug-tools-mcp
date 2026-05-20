"""Garden-managed UWG run ledger and execution services."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import dragonfly_uwg._extend_dragonfly  # noqa: F401
from dragonfly_uwg.writer import model_to_uwg as sdk_model_to_uwg
from honeybee.config import folders as hb_folders
from ladybug.epw import EPW

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from garden.run_energy.config import make_garden_weather_target
from garden.run_uwg import UWG_DOMAIN, UWG_RUN_RECIPE, UWG_RUN_TARGET_TYPE
from garden.run_uwg.parameters import load_uwg_simulation_parameter
from garden.run_uwg.writer import resolve_epw_path
from ladybug_tools_mcp.contracts.report import make_report

UWG_RUNS_DIR = Path("runs") / "uwg"
UWG_RUN_INDEX = UWG_RUNS_DIR / "index.json"
OUTPUT_NAMES = ("uwg_json", "morphed_epw", "weather_target", "stdio_log")
UWG_CLI_TIMEOUT_SECONDS = 900

_uwg_index_lock = threading.Lock()


def run_uwg(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    run_id: str | None = None,
    reload_old: bool = False,
    silent: bool = True,
    validate_weather: bool = True,
) -> dict[str, Any]:
    """Run UWG synchronously and register the morphed EPW as a weather target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    normalized_run_id = _normalize_run_id(run_id, resolved_model_target)
    existing = _run_record_by_id(garden_root_path, normalized_run_id)
    if reload_old and existing and existing.get("status") == "completed":
        return _result_from_record(
            existing,
            "Reloaded completed UWG run.",
            garden_root=str(garden_root_path),
        )

    target = _run_target(manifest.garden_id, normalized_run_id)
    run_dir = garden_root_path / UWG_RUNS_DIR / normalized_run_id
    outputs_dir = run_dir / "outputs"
    inputs_dir = run_dir / "inputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    stdio_log = run_dir / "uwg_stdio.log"
    started_at = _utc_now()

    try:
        model = load_dragonfly_model(garden_root_path, resolved_model_target)
        resolved_epw = resolve_epw_path(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        preflight = (
            _preflight_epw(resolved_epw)
            if validate_weather
            else {"status": "skipped", "issues": []}
        )
        if preflight["status"] == "failed":
            raise ValueError("; ".join(preflight["issues"]))
        parameter, parameter_target, parameter_dict = load_uwg_simulation_parameter(
            garden_root=garden_root_path,
            simulation_parameter_target=simulation_parameter_target,
            simulation_parameter=simulation_parameter,
        )
        if parameter_dict is not None:
            (inputs_dir / "simulation_parameter.json").write_text(
                json.dumps(parameter_dict, indent=2) + "\n",
                encoding="utf-8",
            )
        uwg_json_path, morphed_epw_path = _run_uwg_cli(
            model=model,
            epw_file_path=resolved_epw,
            simulation_parameter=parameter,
            directory=outputs_dir,
            stdio_log=stdio_log,
            timeout_seconds=UWG_CLI_TIMEOUT_SECONDS,
        )
        weather = _register_morphed_weather_target(
            garden_root=garden_root_path,
            manifest=manifest,
            run_target=target,
            run_id=normalized_run_id,
            epw_path=morphed_epw_path,
            source_weather_target=weather_target,
        )
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            status="completed",
            model_target=resolved_model_target,
            weather_target=weather_target,
            simulation_parameter_target=parameter_target,
            run_dir=run_dir,
            started_at=started_at,
            completed_at=_utc_now(),
            preflight=preflight,
            outputs={
                "uwg_json": _output("uwg_json", garden_root_path, uwg_json_path),
                "morphed_epw": _output("morphed_epw", garden_root_path, morphed_epw_path),
                "weather_target": weather,
                "stdio_log": _output("stdio_log", garden_root_path, stdio_log),
            },
        )
    except Exception as exc:
        traceback_text = traceback.format_exc()
        stdio_log.parent.mkdir(parents=True, exist_ok=True)
        with stdio_log.open("a", encoding="utf-8") as handle:
            handle.write(traceback_text)
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            status="failed",
            model_target=resolved_model_target,
            weather_target=weather_target,
            simulation_parameter_target=simulation_parameter_target,
            run_dir=run_dir,
            started_at=started_at,
            completed_at=_utc_now(),
            preflight={"status": "failed", "issues": [str(exc)]},
            error=str(exc),
            outputs={"stdio_log": _output("stdio_log", garden_root_path, stdio_log)},
        )
    _upsert_record(garden_root_path, record)
    return _result_from_record(
        record,
        f"UWG run {record['status']}: {normalized_run_id}",
        garden_root=str(garden_root_path),
    )


def _run_uwg_cli(
    *,
    model: Any,
    epw_file_path: Path,
    simulation_parameter: Any,
    directory: Path,
    stdio_log: Path,
    timeout_seconds: int,
) -> tuple[Path, Path]:
    """Write UWG JSON and run the UWG CLI with bounded, captured stdio."""
    directory.mkdir(parents=True, exist_ok=True)
    stdio_log.parent.mkdir(parents=True, exist_ok=True)
    uwg_json_path = directory / f"{model.identifier}_uwg.json"
    morphed_epw_path = directory / f"{model.identifier}.epw"
    uwg_dict = sdk_model_to_uwg(
        model,
        str(epw_file_path),
        simulation_parameter=simulation_parameter,
    )
    uwg_json_path.write_text(
        json.dumps(uwg_dict, indent=4) + "\n",
        encoding="utf-8",
    )
    python_exe = str(hb_folders.python_exe_path or sys.executable)
    cmd = [
        python_exe,
        "-m",
        "uwg",
        "simulate",
        "model",
        str(uwg_json_path),
        str(epw_file_path),
        "--new-epw-dir",
        str(directory),
        "--new-epw-name",
        morphed_epw_path.name,
    ]
    env = os.environ.copy()
    env["PYTHONHOME"] = ""
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(directory),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _write_uwg_stdio_log(stdio_log, cmd, exc.stdout, exc.stderr)
        raise RuntimeError(
            f"UWG CLI timed out after {timeout_seconds} seconds."
        ) from exc
    _write_uwg_stdio_log(stdio_log, cmd, completed.stdout, completed.stderr)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"The UWG failed to run:\n{message}")
    if not morphed_epw_path.is_file():
        raise RuntimeError(f"UWG did not produce morphed EPW: {morphed_epw_path}")
    return uwg_json_path, morphed_epw_path


def _write_uwg_stdio_log(
    path: Path,
    cmd: list[str],
    stdout: str | bytes | None,
    stderr: str | bytes | None,
) -> None:
    """Persist UWG subprocess diagnostics without writing to MCP stdio."""
    def _text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    path.write_text(
        "command: " + " ".join(cmd) + "\n"
        + "\n[stdout]\n"
        + _text(stdout)
        + "\n[stderr]\n"
        + _text(stderr),
        encoding="utf-8",
    )


def start_uwg_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    run_id: str | None = None,
    reload_old: bool = False,
    silent: bool = True,
    validate_weather: bool = True,
) -> dict[str, Any]:
    """Start UWG in the background and return a run target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    normalized_run_id = _normalize_run_id(run_id, resolved_model_target)
    existing = _run_record_by_id(garden_root_path, normalized_run_id)
    if reload_old and existing and existing.get("status") == "completed":
        return _result_from_record(
            existing,
            "Reloaded completed UWG run.",
            garden_root=str(garden_root_path),
        )

    target = _run_target(manifest.garden_id, normalized_run_id)
    run_dir = garden_root_path / UWG_RUNS_DIR / normalized_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    try:
        resolved_epw = resolve_epw_path(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        preflight = (
            _preflight_epw(resolved_epw)
            if validate_weather
            else {"status": "skipped", "issues": []}
        )
    except Exception as exc:
        preflight = {"status": "failed", "issues": [str(exc)]}

    if preflight["status"] == "failed":
        record = _record(
            garden_root=garden_root_path,
            run_id=normalized_run_id,
            target=target,
            status="failed",
            model_target=resolved_model_target,
            weather_target=weather_target,
            simulation_parameter_target=simulation_parameter_target,
            run_dir=run_dir,
            started_at=started_at,
            completed_at=_utc_now(),
            preflight=preflight,
            error="; ".join(preflight["issues"]),
            outputs={},
        )
        _upsert_record(garden_root_path, record)
        return _result_from_record(
            record,
            f"UWG preflight failed: {normalized_run_id}",
            garden_root=str(garden_root_path),
        )

    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=target,
        status="running",
        model_target=resolved_model_target,
        weather_target=weather_target,
        simulation_parameter_target=simulation_parameter_target,
        run_dir=run_dir,
        started_at=started_at,
        preflight=preflight,
        outputs={},
    )
    _upsert_record(garden_root_path, record)
    _BACKGROUND_EXECUTOR.submit(
        run_uwg,
        garden_root=str(garden_root_path),
        model_target=resolved_model_target,
        weather_target=weather_target,
        simulation_parameter_target=simulation_parameter_target,
        simulation_parameter=simulation_parameter,
        run_id=normalized_run_id,
        reload_old=False,
        silent=silent,
        validate_weather=False,
    )
    return _result_from_record(
        record,
        f"UWG run started: {normalized_run_id}",
        garden_root=str(garden_root_path),
    )


def get_uwg_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Return a UWG run record."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    resolved_id = _run_id_from_target_or_value(run_target, run_id)
    record = _run_record_by_id(garden_root_path, resolved_id)
    if record is None:
        raise ValueError(f"UWG run not found: {resolved_id}")
    return {
        "target": record["target"],
        "uwg_run_target": record["target"],
        "summary_view": {"run": _public_run(record)},
        "report": make_report(status="ok", message=f"Read UWG run: {resolved_id}"),
    }


def list_uwg_runs(
    *,
    garden_root: str,
    status: str | None = None,
) -> dict[str, Any]:
    """List UWG run records."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    records = _read_index(garden_root_path).get("runs", [])
    if status is not None:
        records = [record for record in records if record.get("status") == status]
    matches = [_public_run(record) for record in records]
    return {
        "matches": matches,
        "summary_view": {"count": len(matches), "status": status},
        "report": make_report(status="ok", message=f"Found {len(matches)} UWG run(s)."),
    }


def list_uwg_run_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List UWG run outputs."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    resolved_id = _run_id_from_target_or_value(run_target, run_id)
    record = _run_record_by_id(garden_root_path, resolved_id)
    if record is None:
        raise ValueError(f"UWG run not found: {resolved_id}")
    outputs = record.get("outputs") or {}
    matches = []
    for name in OUTPUT_NAMES:
        value = outputs.get(name)
        if value is None:
            continue
        if isinstance(value, dict) and value.get("target_type") == "weather_file":
            matches.append({"name": name, "target": value, "exists": True})
        else:
            matches.append(value)
    return {
        "matches": matches,
        "summary_view": {"run_id": resolved_id, "count": len(matches), "outputs": outputs},
        "report": make_report(
            status="ok",
            message=f"Listed UWG outputs: {resolved_id}",
        ),
    }


class _BackgroundExecutor:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="uwg")

    def submit(self, fn, **kwargs):
        return self._executor.submit(fn, **kwargs)


_BACKGROUND_EXECUTOR = _BackgroundExecutor()


def _record(
    *,
    garden_root: Path,
    run_id: str,
    target: dict[str, Any],
    status: str,
    model_target: dict[str, Any],
    weather_target: dict[str, Any] | None,
    simulation_parameter_target: dict[str, Any] | None,
    run_dir: Path,
    started_at: str,
    completed_at: str | None = None,
    preflight: dict[str, Any] | None = None,
    error: str | None = None,
    outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "run_id": run_id,
        "target": target,
        "recipe": UWG_RUN_RECIPE,
        "status": status,
        "created_at": started_at,
        "started_at": started_at,
        "run_folder": to_posix_relative(run_dir, garden_root),
        "model_target": model_target,
        "weather_target": weather_target or {},
        "simulation_parameter_target": simulation_parameter_target or {},
        "preflight": preflight or {"status": "skipped", "issues": []},
        "outputs": outputs or {},
    }
    if completed_at is not None:
        record["completed_at"] = completed_at
    if error:
        record["error"] = error
    return record


def _normalize_run_id(
    run_id: str | None,
    model_target: dict[str, Any],
) -> str:
    if run_id:
        return slugify_name(run_id)
    return slugify_name(f"{model_target['model_identifier']}_uwg_{uuid4().hex[:8]}")


def _run_target(garden_id: str, run_id: str) -> dict[str, Any]:
    return {
        "target_type": UWG_RUN_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": UWG_DOMAIN,
        "recipe": UWG_RUN_RECIPE,
        "run_id": run_id,
    }


def _run_id_from_target_or_value(
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    if run_target is not None:
        if run_target.get("target_type") != UWG_RUN_TARGET_TYPE:
            raise ValueError("run_target must be a uwg_run target.")
        value = run_target.get("run_id")
        if not value:
            raise ValueError("uwg_run target requires run_id.")
        return str(value)
    if run_id:
        return slugify_name(run_id)
    raise ValueError("Pass run_target or run_id.")


def _read_index(garden_root: Path) -> dict[str, Any]:
    path = garden_root / UWG_RUN_INDEX
    if not path.is_file():
        return {"runs": []}
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if text.strip() else {"runs": []}


def _write_index(garden_root: Path, payload: dict[str, Any]) -> None:
    path = garden_root / UWG_RUN_INDEX
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    with _uwg_index_lock:
        index = _read_index(garden_root)
        index["runs"] = [
            item for item in index.get("runs", []) if item.get("run_id") != record["run_id"]
        ]
        index["runs"].append(record)
        _write_index(garden_root, index)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any] | None:
    for record in _read_index(garden_root).get("runs", []):
        if record.get("run_id") == run_id:
            return record
    return None


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record.get("run_id"),
        "target": record.get("target"),
        "recipe": record.get("recipe"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "started_at": record.get("started_at"),
        "completed_at": record.get("completed_at"),
        "run_folder": record.get("run_folder"),
        "model_target": record.get("model_target"),
        "weather_target": record.get("weather_target"),
        "simulation_parameter_target": record.get("simulation_parameter_target"),
        "preflight": record.get("preflight"),
        "outputs": record.get("outputs") or {},
        "error": record.get("error"),
    }


def _result_from_record(
    record: dict[str, Any],
    message: str,
    *,
    garden_root: str | None = None,
) -> dict[str, Any]:
    target = record["target"]
    public = _public_run(record)
    return {
        "target": target,
        "uwg_run_target": target,
        "run_target": target,
        "summary_view": {
            "status": record["status"],
            "run": public,
            "outputs": record.get("outputs") or {},
            "poll_next": {
                "tool": "get_uwg_run",
                "arguments": {"garden_root": garden_root, "run_target": target},
            },
        },
        "report": make_report(status="ok", message=message),
    }


def _preflight_epw(path: Path) -> dict[str, Any]:
    try:
        epw = EPW(str(path))
        if len(epw.dry_bulb_temperature.values) != 8760:
            raise ValueError("EPW dry-bulb temperature series is not 8760 hours.")
    except Exception as exc:
        return {"status": "failed", "issues": [f"Invalid EPW: {exc}"]}
    return {"status": "ok", "issues": []}


def _register_morphed_weather_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    run_target: dict[str, Any],
    run_id: str,
    epw_path: Path,
    source_weather_target: dict[str, Any] | None,
) -> dict[str, Any]:
    ddy_path = None
    stat_path = None
    if source_weather_target:
        if source_weather_target.get("ddy_path"):
            candidate = garden_root / str(source_weather_target["ddy_path"])
            ddy_path = candidate.resolve() if candidate.exists() else None
        if source_weather_target.get("stat_path"):
            candidate = garden_root / str(source_weather_target["stat_path"])
            stat_path = candidate.resolve() if candidate.exists() else None
    target = make_garden_weather_target(
        garden_root=garden_root,
        manifest=manifest,
        identifier=f"{run_id}_uwg_weather",
        epw_path=epw_path,
        ddy_path=ddy_path,
        stat_path=stat_path,
        metadata={
            "source": "uwg",
            "source_run_target": run_target,
            "search_terms": ["uwg", "urban", "morphed", run_id],
        },
    )
    manifest.weather_files = [
        item
        for item in manifest.weather_files
        if item.get("identifier") != target["identifier"]
    ]
    manifest.weather_files.append(target)
    manifest.write(garden_root)
    return target


def _output(name: str, garden_root: Path, path: Path) -> dict[str, Any]:
    return {
        "name": name,
        "path": to_posix_relative(path, garden_root),
        "exists": path.exists(),
    }


@contextlib.contextmanager
def _capture_stdio(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    saved_fds: list[tuple[int, int]] = []
    with path.open("a", encoding="utf-8", errors="replace") as handle:
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
            try:
                stream.flush()
            except Exception:
                pass
        for fd in (1, 2):
            try:
                saved_fd = os.dup(fd)
                os.dup2(handle.fileno(), fd)
            except OSError:
                continue
            saved_fds.append((fd, saved_fd))
        try:
            with contextlib.redirect_stdout(handle), contextlib.redirect_stderr(handle):
                yield
        finally:
            for stream in (sys.stdout, sys.stderr):
                try:
                    stream.flush()
                except Exception:
                    pass
            handle.flush()
            for fd, saved_fd in reversed(saved_fds):
                try:
                    os.dup2(saved_fd, fd)
                finally:
                    os.close(saved_fd)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
