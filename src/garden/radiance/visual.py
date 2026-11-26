"""Radiance visual postprocess services."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from typing import Any

from honeybee_display.model import model_to_vis_set
from honeybee_radiance.config import folders as rad_folders
from honeybee_radiance_command.evalglare import Evalglare
from honeybee_radiance_command.falsecolor import Falsecolor
from honeybee_radiance_command.getinfo import Getinfo
from honeybee_radiance_command.options.evalglare import EvalglareOptions
from honeybee_radiance_command.options.falsecolor import FalsecolorOptions
from honeybee_radiance_command.options.getinfo import GetinfoOptions
from honeybee_radiance_command.options.pcomb import PcombOptions
from honeybee_radiance_command.options.pcond import PcondOptions
from honeybee_radiance_command.options.pfilt import PfiltOptions
from honeybee_radiance_command.options.ra_gif import Ra_GIFOptions
from honeybee_radiance_command.pcomb import Pcomb
from honeybee_radiance_command.pcond import Pcond
from honeybee_radiance_command.pfilt import Pfilt
from honeybee_radiance_command.ra_gif import Ra_GIF

from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report
from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.ladybug_tools_config import apply_ladybug_tools_runtime_to_path
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.radiance.run import (
    RADIANCE_RUN_DOMAIN,
    RADIANCE_RUN_TARGET_TYPE,
    _read_index,
    _reconcile_running_record,
    _run_id_from_target_or_value,
)
from garden.visualize.artifacts import save_visualization_set

RADIANCE_IMAGE_TARGET_TYPE = "radiance_image"
RADIANCE_HDR_ARTIFACT_TYPE = "radiance_hdr_image"
RADIANCE_GIF_ARTIFACT_TYPE = "radiance_gif_image"
RADIANCE_PNG_ARTIFACT_TYPE = "radiance_png_image"
RADIANCE_BMP_ARTIFACT_TYPE = "radiance_bmp_image"
RADIANCE_IMAGE_OUTPUT_SUBDIR = "artifacts/radiance/images"
GRID_DISPLAY_MODES = {"Surface", "SurfaceWithEdges", "Wireframe", "Points"}
MODEL_COLOR_BY = {"type", "boundary_condition", "none"}
MIN_FALSECOLOR_HDR_BYTES = 128

_DEFAULT_GRID_OUTPUT_NAMES: dict[str, tuple[str, ...]] = {
    "direct-sun-hours": ("cumulative-sun-hours", "direct-sun-hours", "results"),
    "cumulative-radiation": ("cumulative-radiation", "average-irradiance", "results"),
    "annual-irradiance": ("results", "cumulative-radiation", "average-irradiance", "peak-irradiance"),
    "pmv-comfort-map": ("tcp", "hsp", "csp", "temperature", "condition", "pmv"),
    "utci-comfort-map": ("tcp", "hsp", "csp", "temperature", "condition", "utci"),
    "adaptive-comfort-map": ("tcp", "hsp", "csp", "temperature", "condition", "degrees-from-neutral"),
}


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _run_record(
    garden_root: Path,
    *,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    resolved_run_id = _run_id_from_target_or_value(
        run_target=run_target,
        run_id=run_id,
    )
    for record in _read_index(garden_root):
        if record.get("run_id") == resolved_run_id:
            return _reconcile_running_record(garden_root_path=garden_root, record=record)
    raise ValueError(f"Radiance run was not found: {resolved_run_id}")


def _latest_completed_view_run(garden_root: Path) -> dict[str, Any]:
    records = [
        _reconcile_running_record(garden_root_path=garden_root, record=record)
        for record in _read_index(garden_root)
        if record.get("recipe") == "point-in-time-view"
    ]
    records = [record for record in records if record.get("status") == "completed"]
    if not records:
        raise ValueError(
            "Provide run_target or run_id, or complete a point-in-time-view "
            "Radiance run first."
        )
    return sorted(
        records,
        key=lambda item: (
            str(item.get("completed_at") or ""),
            str(item.get("created_at") or ""),
            str(item.get("run_id") or ""),
        ),
    )[-1]


def _validate_run_target_garden(record: dict[str, Any], manifest: GardenManifest) -> None:
    target = record.get("target") or {}
    if target.get("target_type") != RADIANCE_RUN_TARGET_TYPE:
        raise ValueError("Radiance run record has an invalid target_type.")
    if target.get("domain") != RADIANCE_RUN_DOMAIN:
        raise ValueError("Radiance run record has an invalid domain.")
    garden_id = target.get("garden_id")
    if garden_id != manifest.garden_id:
        raise ValueError("Radiance run belongs to a different Garden.")


def _require_completed(record: dict[str, Any]) -> None:
    if record.get("status") != "completed":
        raise ValueError("Radiance visual postprocess requires a completed radiance_run.")


def _output_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("name")): item for item in record.get("outputs", [])}


def _resolve_output_path(
    garden_root: Path,
    record: dict[str, Any],
    output_name: str,
) -> Path:
    output = _output_map(record).get(output_name)
    if not output or not output.get("path"):
        raise ValueError(f"Radiance run output was not found: {output_name}")
    path = (garden_root / str(output["path"])).resolve()
    path.relative_to(garden_root)
    if not path.exists():
        raise ValueError(f"Radiance run output path does not exist: {output['path']}")
    return path


def _image_target(
    *,
    manifest: GardenManifest,
    identifier: str,
    path: str,
    image_format: str,
) -> dict[str, Any]:
    return {
        "target_type": RADIANCE_IMAGE_TARGET_TYPE,
        "garden_id": manifest.garden_id,
        "domain": "honeybee_radiance",
        "identifier": identifier,
        "path": path,
        "format": image_format,
    }


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "artifact_type": artifact_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    return manifest.upsert_artifact(record)


def _save_image_artifact(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    path: Path,
    name: str,
    image_format: str,
    artifact_type: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    artifact_path = to_posix_relative(path, garden_root)
    artifact = _register_artifact(
        manifest,
        artifact_type=artifact_type,
        name=name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root)
    target = _image_target(
        manifest=manifest,
        identifier=name,
        path=artifact_path,
        image_format=image_format,
    )
    return {
        "target": target,
        "radiance_image_target": target,
        "artifact": artifact,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=artifact_type,
            artifact_path=artifact_path,
            absolute_path=str(path),
            source=source,
        ),
    }


def _option_update(options: Any, additional_options: str | None) -> None:
    if additional_options:
        options.update_from_string(additional_options)


def _view_results_folder(garden_root: Path, record: dict[str, Any]) -> Path:
    if record.get("recipe") != "point-in-time-view":
        raise ValueError("HDR image tools only support point-in-time-view Radiance runs.")
    output_path = _resolve_output_path(garden_root, record, "results")
    if output_path.is_file():
        return output_path.parent
    return output_path


def list_radiance_hdr_images(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List .hdr images in a completed view Radiance run."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    record = (
        _run_record(garden_root_path, run_target=run_target, run_id=run_id)
        if run_target is not None or run_id is not None
        else _latest_completed_view_run(garden_root_path)
    )
    _validate_run_target_garden(record, manifest)
    if record.get("status") != "completed":
        return {
            "matches": [],
            "hdr_images": [],
            "images": [],
            "summary_view": {
                "garden_target": manifest.target(),
                "run_id": record.get("run_id"),
                "recipe": record.get("recipe"),
                "run_status": record.get("status"),
                "count": 0,
                "supported_extensions": [".hdr"],
                "unsupported_extensions": [".pic", ".unf"],
            },
            "report": make_report(
                status="ok",
                message=(
                    "Radiance run is not completed yet; no HDR images are listed."
                ),
            ),
        }
    results_folder = _view_results_folder(garden_root_path, record)
    matches = []
    for path in sorted(results_folder.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".hdr":
            continue
        matches.append(
            {
                "name": path.name,
                "path": to_posix_relative(path, garden_root_path),
                "absolute_path": str(path),
                "extension": ".hdr",
                "size_bytes": path.stat().st_size,
                "run_id": record.get("run_id"),
                "recipe": record.get("recipe"),
            }
        )
    return {
        "matches": matches,
        "hdr_images": matches,
        "images": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": record.get("recipe"),
            "count": len(matches),
            "supported_extensions": [".hdr"],
            "unsupported_extensions": [".pic", ".unf"],
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Radiance HDR image(s).",
        ),
    }


def _resolve_hdr_input(
    garden_root: Path,
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
    image_path: str | None,
    image_name: str | None,
) -> tuple[Path, dict[str, Any] | None]:
    has_path = image_path is not None
    has_run = run_target is not None or run_id is not None
    record = None
    if has_path:
        path = (garden_root / str(image_path)).resolve()
        path.relative_to(garden_root)
    else:
        record = (
            _run_record(garden_root, run_target=run_target, run_id=run_id)
            if has_run
            else _latest_completed_view_run(garden_root)
        )
        _require_completed(record)
        results_folder = _view_results_folder(garden_root, record)
        images = [path for path in results_folder.rglob("*") if path.suffix.lower() == ".hdr"]
        if image_name:
            images = [path for path in images if path.name == image_name]
        if len(images) > 1 and not image_name:
            images = images[:1]
        if len(images) != 1:
            raise ValueError(
                "Expected exactly one HDR image. Provide image_name to disambiguate."
            )
        path = images[0]
    if path.suffix.lower() != ".hdr":
        raise ValueError("Radiance image postprocess tools only accept .hdr input.")
    if not path.is_file():
        raise ValueError(f"Radiance HDR image was not found: {path}")
    return path, record


def _image_output_path(
    garden_root: Path,
    *,
    name: str | None,
    input_path: Path,
    suffix: str,
    output_subdir: str,
) -> tuple[str, Path]:
    identifier = slugify_name(name or input_path.stem)
    output_dir = (garden_root / output_subdir).resolve()
    output_dir.relative_to(garden_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    return identifier, (output_dir / f"{identifier}{suffix}").resolve()


def radiance_hdr_to_falsecolor(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_name: str | None = None,
    name: str | None = None,
    scale: str | float | None = None,
    legend_label: str | None = None,
    legend_multiplier: float | None = None,
    contour_lines: bool | None = None,
    contour_bands: bool | None = None,
    palette: str | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a falsecolor .hdr artifact from a Radiance .hdr image."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    input_path, record = _resolve_hdr_input(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    if record is not None:
        _validate_run_target_garden(record, manifest)
    identifier, output_path = _image_output_path(
        garden_root_path,
        name=name,
        input_path=input_path,
        suffix=".hdr",
        output_subdir=output_subdir,
    )

    options = FalsecolorOptions()
    if scale is not None:
        options.s = str(scale)
    if legend_label is not None:
        options.l = legend_label
    if legend_multiplier is not None:
        options.m = legend_multiplier
    if contour_lines is not None:
        options.cl = contour_lines
    if contour_bands is not None:
        options.cb = contour_bands
    if palette is not None:
        options.pal = palette
    _option_update(options, additional_options)
    command = Falsecolor(
        options=options,
        output=_relative_cmd_arg(output_path, garden_root_path, quote_spaces=False),
        input=_relative_cmd_arg(input_path, garden_root_path),
    )
    cmd_str = command.to_radiance()
    _run_radiance_shell(cmd_str, cwd=garden_root_path, tool_name="falsecolor")
    if not output_path.is_file():
        raise ValueError("falsecolor command completed without writing an output file.")
    output_size = output_path.stat().st_size
    if output_size < MIN_FALSECOLOR_HDR_BYTES:
        try:
            output_path.unlink()
        except OSError:
            pass
        raise ValueError(
            "falsecolor command wrote an output that is too small to be a usable "
            f"HDR image ({output_size} bytes)."
        )

    source = {
        "producer": "RAD_Process_HDR_Image",
        "operation": "falsecolor",
        "input_path": to_posix_relative(input_path, garden_root_path),
        "run_id": record.get("run_id") if record else None,
        "command": cmd_str,
    }
    saved = _save_image_artifact(
        garden_root=garden_root_path,
        manifest=manifest,
        path=output_path,
        name=identifier,
        image_format="hdr",
        artifact_type=RADIANCE_HDR_ARTIFACT_TYPE,
        source=source,
    )
    saved["summary_view"] = {
        "garden_target": manifest.target(),
        "target": saved["target"],
        "input_path": source["input_path"],
        "output_path": saved["target"]["path"],
        "format": "hdr",
        "artifact_type": RADIANCE_HDR_ARTIFACT_TYPE,
    }
    saved["report"] = make_report(
        status="ok",
        message="Radiance falsecolor HDR artifact created.",
    )
    return saved


def radiance_hdr_to_gif(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_name: str | None = None,
    name: str | None = None,
    exposure: int | None = None,
    gamma: float | None = None,
    black_and_white: bool | None = None,
    colors: int | None = None,
    sampling_factor: int | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a .gif artifact from a Radiance .hdr image."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    input_path, record = _resolve_hdr_input(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    if record is not None:
        _validate_run_target_garden(record, manifest)
    identifier, output_path = _image_output_path(
        garden_root_path,
        name=name,
        input_path=input_path,
        suffix=".gif",
        output_subdir=output_subdir,
    )

    options = Ra_GIFOptions()
    if exposure is not None:
        options.e = exposure
    if gamma is not None:
        options.g = gamma
    if black_and_white is not None:
        options.b = black_and_white
    if colors is not None:
        options.c = colors
    if sampling_factor is not None:
        options.n = sampling_factor
    _option_update(options, additional_options)
    command = Ra_GIF(
        options=options,
        output=_relative_cmd_arg(output_path, garden_root_path, quote_spaces=False),
        input=_relative_cmd_arg(input_path, garden_root_path),
    )
    cmd_str = command.to_radiance()
    _run_radiance_shell(cmd_str, cwd=garden_root_path, tool_name="ra_gif")
    if not output_path.is_file():
        raise ValueError("ra_gif command completed without writing an output file.")

    source = {
        "producer": "RAD_Process_HDR_Image",
        "operation": "gif",
        "input_path": to_posix_relative(input_path, garden_root_path),
        "run_id": record.get("run_id") if record else None,
        "command": cmd_str,
    }
    saved = _save_image_artifact(
        garden_root=garden_root_path,
        manifest=manifest,
        path=output_path,
        name=identifier,
        image_format="gif",
        artifact_type=RADIANCE_GIF_ARTIFACT_TYPE,
        source=source,
    )
    saved["summary_view"] = {
        "garden_target": manifest.target(),
        "target": saved["target"],
        "input_path": source["input_path"],
        "output_path": saved["target"]["path"],
        "format": "gif",
        "artifact_type": RADIANCE_GIF_ARTIFACT_TYPE,
    }
    saved["report"] = make_report(
        status="ok",
        message="Radiance GIF artifact created.",
    )
    return saved


def _grid_data_dirs(root: Path) -> list[Path]:
    if root.is_file():
        return []
    dirs = []
    if (root / "grids_info.json").is_file():
        dirs.append(root)
    for info in sorted(root.rglob("grids_info.json")):
        folder = info.parent
        if folder not in dirs:
            dirs.append(folder)
    return dirs


def _grid_folder_summary(garden_root: Path, folder: Path) -> dict[str, Any]:
    info_path = folder / "grids_info.json"
    grids = json.loads(info_path.read_text(encoding="utf-8"))
    result_files = [
        path
        for path in sorted(folder.iterdir())
        if path.is_file() and path.name not in {"grids_info.json", "vis_metadata.json"}
    ]
    sensor_count = sum(int(grid.get("count", 0)) for grid in grids)
    return {
        "path": to_posix_relative(folder, garden_root),
        "absolute_path": str(folder),
        "grid_count": len(grids),
        "sensor_count": sensor_count,
        "grid_identifiers": [grid.get("full_id") or grid.get("name") for grid in grids],
        "result_file_count": len(result_files),
        "result_files": [path.name for path in result_files],
        "has_vis_metadata": (folder / "vis_metadata.json").is_file(),
    }


def list_radiance_grid_results(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List SensorGrid result folders in a completed Radiance run."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    record = _run_record(garden_root_path, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)
    matches = []
    for output in record.get("outputs", []):
        if not output.get("path"):
            continue
        output_path = (garden_root_path / str(output["path"])).resolve()
        output_path.relative_to(garden_root_path)
        if not output_path.exists():
            continue
        for folder in _grid_data_dirs(output_path):
            summary = _grid_folder_summary(garden_root_path, folder)
            summary.update(
                {
                    "run_id": record.get("run_id"),
                    "recipe": record.get("recipe"),
                    "output_name": output.get("name"),
                }
            )
            matches.append(summary)
    return {
        "matches": matches,
        "grids": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": record.get("recipe"),
            "count": len(matches),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Radiance grid result folder(s).",
        ),
    }


def _resolve_grid_data_path(
    garden_root: Path,
    record: dict[str, Any] | None,
    *,
    grid_data_path: str | None,
    output_name: str | None,
    result_subfolder: str | None,
) -> Path:
    if grid_data_path is not None:
        path = (garden_root / grid_data_path).resolve()
        path.relative_to(garden_root)
    else:
        if record is None:
            raise ValueError("Provide grid_data_path or run_target/run_id.")
        recipe_name = str(record.get("recipe") or "").strip().lower()
        candidates_to_try: list[str] = []
        if output_name:
            candidates_to_try.append(output_name)
        else:
            candidates_to_try.extend(_DEFAULT_GRID_OUTPUT_NAMES.get(recipe_name, ()))
            if "results" not in candidates_to_try:
                candidates_to_try.append("results")

        resolved_base: Path | None = None
        output_map = _output_map(record)
        for candidate_name in candidates_to_try:
            item = output_map.get(candidate_name)
            if not item or not item.get("path"):
                continue
            candidate_path = (garden_root / str(item["path"])).resolve()
            candidate_path.relative_to(garden_root)
            if not candidate_path.exists():
                continue
            check_path = (
                (candidate_path / result_subfolder).resolve()
                if result_subfolder
                else candidate_path
            )
            check_path.relative_to(garden_root)
            if _grid_data_dirs(check_path):
                resolved_base = check_path
                break

        if resolved_base is None and not output_name:
            for item in record.get("outputs", []):
                if not item.get("path"):
                    continue
                candidate_path = (garden_root / str(item["path"])).resolve()
                candidate_path.relative_to(garden_root)
                if not candidate_path.exists():
                    continue
                check_path = (
                    (candidate_path / result_subfolder).resolve()
                    if result_subfolder
                    else candidate_path
                )
                check_path.relative_to(garden_root)
                if _grid_data_dirs(check_path):
                    resolved_base = check_path
                    break

        if resolved_base is not None:
            path = _grid_data_dirs(resolved_base)[0]
        else:
            fallback_name = output_name or (candidates_to_try[0] if candidates_to_try else "results")
            path = _resolve_output_path(garden_root, record, fallback_name)
            if result_subfolder:
                path = (path / result_subfolder).resolve()
                path.relative_to(garden_root)
            candidates = _grid_data_dirs(path)
            if not candidates:
                raise ValueError("No Radiance grid result folders with grids_info.json found.")
            path = candidates[0]
    if not path.is_dir() or not (path / "grids_info.json").is_file():
        raise ValueError("grid_data_path must be a folder containing grids_info.json.")
    return path


def radiance_grid_result_to_visualization_set(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    grid_data_path: str | None = None,
    output_name: str | None = None,
    result_subfolder: str | None = None,
    model_target: dict[str, Any] | None = None,
    color_by: str | None = "none",
    include_wireframe: bool = True,
    use_mesh: bool = False,
    hide_color_by: bool = True,
    grid_data_display_mode: str = "Surface",
    active_grid_data: str | None = None,
    name: str = "radiance_grid_result",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate Radiance SensorGrid result folders into a VisualizationSet."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    record = None
    if run_target is not None or run_id is not None:
        record = _run_record(
            garden_root_path,
            run_target=run_target,
            run_id=run_id,
        )
        _validate_run_target_garden(record, manifest)
        _require_completed(record)
    grid_folder = _resolve_grid_data_path(
        garden_root_path,
        record,
        grid_data_path=grid_data_path,
        output_name=output_name,
        result_subfolder=result_subfolder,
    )
    normalized_color_by = (color_by or "none").strip().lower()
    if normalized_color_by not in MODEL_COLOR_BY:
        allowed = ", ".join(sorted(MODEL_COLOR_BY))
        raise ValueError(f"Unsupported color_by: {color_by}. Allowed values: {allowed}.")
    if grid_data_display_mode not in GRID_DISPLAY_MODES:
        allowed = ", ".join(sorted(GRID_DISPLAY_MODES))
        raise ValueError(
            f"Unsupported grid_data_display_mode: {grid_data_display_mode}. "
            f"Allowed values: {allowed}."
        )

    resolved_model_target = model_target or (
        record.get("model_target") if record else None
    )
    if not resolved_model_target:
        raise ValueError("RAD_Grid_Result_To_Visualization_Set requires a model target.")
    _, resolved_model_target = resolve_model_target(garden_root_path, resolved_model_target)
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    safe_name = slugify_name(name)
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        vis_set = model_to_vis_set(
            model,
            color_by=normalized_color_by,
            include_wireframe=include_wireframe,
            use_mesh=use_mesh,
            hide_color_by=hide_color_by,
            grid_display_mode="Default",
            hide_grid=True,
            grid_data_path=str(grid_folder),
            grid_data_display_mode=grid_data_display_mode,
            active_grid_data=active_grid_data,
        )
    vis_set.identifier = safe_name
    vis_set.display_name = name
    visualization_set = vis_set.to_dict()
    grid_summary = _grid_folder_summary(garden_root_path, grid_folder)
    summary = {
        "garden_target": manifest.target(),
        "model_target": resolved_model_target,
        "run_id": record.get("run_id") if record else None,
        "recipe": record.get("recipe") if record else None,
        "grid_data": grid_summary,
        "use_mesh": use_mesh,
        "visualization_set": {
            "identifier": visualization_set.get("identifier"),
            "display_name": visualization_set.get("display_name"),
            "units": visualization_set.get("units"),
            "geometry_count": len(visualization_set.get("geometry", [])),
            "geometry_identifiers": [
                item.get("identifier")
                for item in visualization_set.get("geometry", [])
                if isinstance(item, dict)
            ],
        },
        "body_returned": return_visualization_set,
    }
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message="Radiance grid result VisualizationSet created.",
        ),
    }
    saved = save_visualization_set(
        garden_root=str(garden_root_path),
        visualization_set=visualization_set,
        name=safe_name,
        source={
            "producer": "RAD_Grid_Result_To_Visualization_Set",
            "run_id": record.get("run_id") if record else None,
            "grid_data_path": grid_summary["path"],
        },
    )
    result["target"] = saved["target"]
    result["visualization_set_target"] = saved["visualization_set_target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["visualization_set_target"] = saved["visualization_set_target"]
    if not return_visualization_set:
        result.pop("visualization_set", None)
    return result


def _subprocess_env() -> dict[str, str]:
    apply_ladybug_tools_runtime_to_path()
    env = dict(os.environ)
    for key, value in (rad_folders.env or {}).items():
        if key.upper() == "PATH":
            existing = [p for p in env.get("PATH", "").split(os.pathsep) if p]
            extra = [p for p in str(value).split(os.pathsep) if p]
            merged: list[str] = []
            seen: set[str] = set()
            for entry in [*extra, *existing]:
                norm = os.path.normcase(os.path.normpath(entry))
                if norm not in seen:
                    seen.add(norm)
                    merged.append(entry)
            env["PATH"] = os.pathsep.join(merged)
        else:
            env[key] = value
    return env


def _relative_cmd_arg(path: Path, cwd: Path, *, quote_spaces: bool = True) -> str:
    rel = to_posix_relative(path, cwd)
    if quote_spaces and (" " in rel or "\t" in rel):
        return f'"{rel}"'
    return rel


def _run_radiance_shell(
    cmd: str,
    *,
    cwd: Path,
    tool_name: str,
) -> subprocess.CompletedProcess[str]:
    env = _subprocess_env()
    temp_val = env.get("TEMP") or env.get("TMP") or ""
    if not temp_val or not temp_val.isascii():
        from ladybug_tools_mcp.runtime_home import safe_ascii_temp_dir

        ascii_temp = str(safe_ascii_temp_dir(cwd, f"rad_{tool_name}"))
        env["TEMP"] = ascii_temp
        env["TMP"] = ascii_temp
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        shell=True,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise ValueError(
            f"{tool_name} command failed with exit code {proc.returncode}"
            + (f": {detail}" if detail else ".")
        )
    return proc


def _resolve_pcomb_inputs(
    garden_root: Path,
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
    image_path: str | None,
    image_paths: list[str] | None,
    image_name: str | None,
) -> tuple[list[Path], dict[str, Any] | None]:
    if image_paths:
        paths: list[Path] = []
        for raw in image_paths:
            path = (garden_root / str(raw)).resolve()
            path.relative_to(garden_root)
            if path.suffix.lower() != ".hdr":
                raise ValueError("pcomb only accepts .hdr input files.")
            if not path.is_file():
                raise ValueError(f"Radiance HDR image was not found: {path}")
            paths.append(path)
        return paths, None
    single, record = _resolve_hdr_input(
        garden_root,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    return [single], record


def _run_hdr_transform(
    *,
    garden_root: str,
    operation: str,
    input_paths: list[Path],
    record: dict[str, Any] | None,
    manifest: GardenManifest,
    name: str | None,
    command: Any,
    output_path: Path,
    output_subdir: str,
) -> dict[str, Any]:
    garden_root_path = _garden_root(garden_root)
    if record is not None:
        _validate_run_target_garden(record, manifest)
    cmd_str = command.to_radiance()
    _run_radiance_shell(cmd_str, cwd=garden_root_path, tool_name=operation)
    if not output_path.is_file():
        raise ValueError(f"{operation} completed without writing output file: {output_path}")
    if output_path.stat().st_size == 0:
        try:
            output_path.unlink()
        except OSError:
            pass
        raise ValueError(f"{operation} produced an empty HDR file.")

    identifier = slugify_name(name or output_path.stem)
    rel_inputs = [to_posix_relative(p, garden_root_path) for p in input_paths]
    source: dict[str, Any] = {
        "producer": "RAD_Process_HDR_Image",
        "operation": operation,
        "input_path": rel_inputs[0],
        "run_id": record.get("run_id") if record else None,
        "command": cmd_str,
    }
    if len(rel_inputs) > 1:
        source["input_paths"] = rel_inputs
    saved = _save_image_artifact(
        garden_root=garden_root_path,
        manifest=manifest,
        path=output_path,
        name=identifier,
        image_format="hdr",
        artifact_type=RADIANCE_HDR_ARTIFACT_TYPE,
        source=source,
    )
    saved["summary_view"] = {
        "garden_target": manifest.target(),
        "target": saved["target"],
        "input_path": rel_inputs[0],
        "output_path": saved["target"]["path"],
        "format": "hdr",
        "artifact_type": RADIANCE_HDR_ARTIFACT_TYPE,
        "operation": operation,
    }
    saved["report"] = make_report(
        status="ok",
        message=f"Radiance HDR {operation} artifact created.",
    )
    return saved


def _parse_evalglare_output(stdout: str) -> dict[str, Any]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    metrics: dict[str, float] = {}
    glare_sources: list[dict[str, float | int]] = []
    source_headers: list[str] = []

    for line in lines:
        lower = line.lower()
        if lower.startswith("glare source"):
            tokens = line.split()
            # Header after "glare source" keywords
            source_headers = [t.strip(",") for t in tokens[2:]]
            continue
        if ":" in line and ("dgp" in lower or "dgi" in lower or "ugr" in lower):
            key_part, val_part = line.split(":", 1)
            keys = [k.strip() for k in key_part.split(",") if k.strip()]
            vals = [v.strip() for v in re.split(r"[,\s]+", val_part.strip()) if v.strip()]
            for key, raw_val in zip(keys, vals):
                try:
                    metrics[key.lower()] = float(raw_val)
                except ValueError:
                    continue
            continue
        if re.match(r"^\d+\s+[-+0-9.eE]+", line):
            parts = line.split()
            try:
                nums = [float(p) for p in parts]
            except ValueError:
                continue
            row: dict[str, float | int] = {"index": int(nums[0])}
            if source_headers and len(source_headers) >= len(nums) - 1:
                for hdr_name, num_val in zip(source_headers, nums[1:]):
                    row[hdr_name] = num_val
            else:
                default_cols = ("x", "y", "z", "dirx", "diry", "dirz", "omega", "lum", "pos_idx")
                for col_idx, num_val in enumerate(nums[1:]):
                    col_name = default_cols[col_idx] if col_idx < len(default_cols) else f"col_{col_idx + 1}"
                    row[col_name] = num_val
            glare_sources.append(row)

    ev_val = metrics.get("e_v")
    if ev_val is None:
        ev_val = metrics.get("ev")
    return {
        "dgp": metrics.get("dgp"),
        "dgi": metrics.get("dgi"),
        "ugr": metrics.get("ugr"),
        "vcp": metrics.get("vcp"),
        "cgi": metrics.get("cgi"),
        "ev": ev_val,
        "av_lum": metrics.get("av_lum"),
        "lveil": metrics.get("lveil"),
        "lveil_cie": metrics.get("lveil_cie"),
        "dgr": metrics.get("dgr"),
        "metrics": metrics,
        "glare_source_count": len(glare_sources),
        "glare_sources": glare_sources,
    }


def radiance_hdr_evalglare(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_name: str | None = None,
    detailed: bool = True,
    threshold_factor: float | None = None,
    correction_mode: str | None = None,
    check_image: bool = False,
    check_image_name: str | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Evaluate glare metrics (DGP, DGI, UGR, VCP, CGI, Ev) on a Radiance .hdr image."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    input_path, record = _resolve_hdr_input(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    if record is not None:
        _validate_run_target_garden(record, manifest)

    options = EvalglareOptions()
    options.d = bool(detailed)
    if threshold_factor is not None:
        options.b = float(threshold_factor)
    if correction_mode is not None:
        options.C = str(correction_mode)

    check_path: Path | None = None
    check_identifier: str | None = None
    if check_image:
        check_identifier, check_path = _image_output_path(
            garden_root_path,
            name=check_image_name or f"{input_path.stem}_glare_check",
            input_path=input_path,
            suffix=".hdr",
            output_subdir=output_subdir,
        )
        options.c = _relative_cmd_arg(check_path, garden_root_path, quote_spaces=False)
    _option_update(options, additional_options)

    command = Evalglare(
        options=options,
        input=_relative_cmd_arg(input_path, garden_root_path),
    )
    cmd_str = command.to_radiance()
    proc = _run_radiance_shell(cmd_str, cwd=garden_root_path, tool_name="evalglare")
    parsed = _parse_evalglare_output(proc.stdout)
    rel_input = to_posix_relative(input_path, garden_root_path)

    result: dict[str, Any] = {
        **parsed,
        "input_path": rel_input,
        "command": cmd_str,
        "raw_output": proc.stdout,
    }
    if check_path is not None and check_path.is_file() and check_identifier is not None:
        saved = _save_image_artifact(
            garden_root=garden_root_path,
            manifest=manifest,
            path=check_path,
            name=check_identifier,
            image_format="hdr",
            artifact_type=RADIANCE_HDR_ARTIFACT_TYPE,
            source={
                "producer": "RAD_Process_HDR_Image",
                "operation": "evalglare",
                "input_path": rel_input,
                "run_id": record.get("run_id") if record else None,
                "command": cmd_str,
            },
        )
        result["target"] = saved["target"]
        result["radiance_image_target"] = saved["target"]
        result["artifact"] = saved["artifact"]
        result["artifact_receipt"] = saved["artifact_receipt"]
        result["check_image_path"] = saved["target"]["path"]

    result["summary_view"] = {
        "garden_target": manifest.target(),
        "operation": "evalglare",
        "input_path": rel_input,
        "dgp": parsed["dgp"],
        "dgi": parsed["dgi"],
        "ugr": parsed["ugr"],
        "vcp": parsed["vcp"],
        "cgi": parsed["cgi"],
        "ev": parsed["ev"],
        "glare_source_count": parsed["glare_source_count"],
        "check_image_path": result.get("check_image_path"),
    }
    result["report"] = make_report(
        status="ok",
        message="evalglare analysis completed.",
    )
    return result


def radiance_hdr_pcond(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_name: str | None = None,
    name: str | None = None,
    human_vision: bool | None = None,
    exposure: float | int | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Tone-map a Radiance .hdr image using pcond."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    input_path, record = _resolve_hdr_input(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    identifier, output_path = _image_output_path(
        garden_root_path,
        name=name or f"{input_path.stem}_pcond",
        input_path=input_path,
        suffix=".hdr",
        output_subdir=output_subdir,
    )
    options = PcondOptions()
    if human_vision is not None:
        options.h = bool(human_vision)
    if exposure is not None:
        options.e = str(exposure)
    _option_update(options, additional_options)
    command = Pcond(
        options=options,
        output=_relative_cmd_arg(output_path, garden_root_path, quote_spaces=False),
        input=_relative_cmd_arg(input_path, garden_root_path),
    )
    return _run_hdr_transform(
        garden_root=garden_root,
        operation="pcond",
        input_paths=[input_path],
        record=record,
        manifest=manifest,
        name=identifier,
        command=command,
        output_path=output_path,
        output_subdir=output_subdir,
    )


def radiance_hdr_pfilt(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_name: str | None = None,
    name: str | None = None,
    x_res: int | str | None = None,
    y_res: int | str | None = None,
    exposure: float | int | None = None,
    radius: float | None = None,
    pixel_aspect: float | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Filter or resize a Radiance .hdr image using pfilt."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    input_path, record = _resolve_hdr_input(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    identifier, output_path = _image_output_path(
        garden_root_path,
        name=name or f"{input_path.stem}_pfilt",
        input_path=input_path,
        suffix=".hdr",
        output_subdir=output_subdir,
    )
    options = PfiltOptions()
    if x_res is not None:
        options.x = str(x_res)
    if y_res is not None:
        options.y = str(y_res)
    if exposure is not None:
        options.e = float(exposure)
    if radius is not None:
        options.r = float(radius)
    if pixel_aspect is not None:
        options.p = float(pixel_aspect)
    _option_update(options, additional_options)
    command = Pfilt(
        options=options,
        output=_relative_cmd_arg(output_path, garden_root_path, quote_spaces=False),
        input=_relative_cmd_arg(input_path, garden_root_path),
    )
    return _run_hdr_transform(
        garden_root=garden_root,
        operation="pfilt",
        input_paths=[input_path],
        record=record,
        manifest=manifest,
        name=identifier,
        command=command,
        output_path=output_path,
        output_subdir=output_subdir,
    )


def radiance_hdr_pcomb(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_paths: list[str] | None = None,
    image_name: str | None = None,
    name: str | None = None,
    expression: str | None = None,
    x_res: int | None = None,
    y_res: int | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Combine or apply pixel expressions on Radiance .hdr image(s) using pcomb."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    inputs, record = _resolve_pcomb_inputs(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_paths=image_paths,
        image_name=image_name,
    )
    identifier, output_path = _image_output_path(
        garden_root_path,
        name=name or f"{inputs[0].stem}_pcomb",
        input_path=inputs[0],
        suffix=".hdr",
        output_subdir=output_subdir,
    )
    options = PcombOptions()
    if expression is not None:
        options.e = str(expression)
    if x_res is not None:
        options.x = int(x_res)
    if y_res is not None:
        options.y = int(y_res)
    _option_update(options, additional_options)
    command = Pcomb(
        options=options,
        output=_relative_cmd_arg(output_path, garden_root_path, quote_spaces=False),
        input=[_relative_cmd_arg(p, garden_root_path) for p in inputs],
    )
    return _run_hdr_transform(
        garden_root=garden_root,
        operation="pcomb",
        input_paths=inputs,
        record=record,
        manifest=manifest,
        name=identifier,
        command=command,
        output_path=output_path,
        output_subdir=output_subdir,
    )


def radiance_hdr_getinfo(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_name: str | None = None,
    dimensions_only: bool | None = None,
    additional_options: str | None = None,
) -> dict[str, Any]:
    """Inspect Radiance .hdr header metadata and image dimensions using getinfo."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    input_path, record = _resolve_hdr_input(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    if record is not None:
        _validate_run_target_garden(record, manifest)

    options = GetinfoOptions()
    if dimensions_only is not None:
        options.d = bool(dimensions_only)
    _option_update(options, additional_options)
    command = Getinfo(
        options=options,
        input=_relative_cmd_arg(input_path, garden_root_path),
    )
    cmd_str = command.to_radiance()
    proc = _run_radiance_shell(cmd_str, cwd=garden_root_path, tool_name="getinfo")
    header_text = proc.stdout.strip()
    dims_match = re.search(r"-Y\s+(\d+)\s+\+X\s+(\d+)", header_text)
    width = int(dims_match.group(2)) if dims_match else None
    height = int(dims_match.group(1)) if dims_match else None
    rel_input = to_posix_relative(input_path, garden_root_path)
    return {
        "input_path": rel_input,
        "command": cmd_str,
        "header": header_text,
        "raw_output": proc.stdout,
        "width": width,
        "height": height,
        "dimensions_only": bool(dimensions_only),
        "summary_view": {
            "garden_target": manifest.target(),
            "operation": "getinfo",
            "input_path": rel_input,
            "width": width,
            "height": height,
        },
        "report": make_report(
            status="ok",
            message="getinfo header retrieved.",
        ),
    }


def _format_ra_bmp_exposure(exposure: str | float | int) -> str:
    if isinstance(exposure, (int, float)) and not isinstance(exposure, bool):
        return f"+{exposure}" if exposure >= 0 else str(exposure)
    raw = str(exposure).strip()
    if raw in {"auto", "human", "linear"} or raw.startswith(("+", "-")):
        return raw
    try:
        val = float(raw)
        return f"+{raw}" if val >= 0 else raw
    except ValueError:
        return raw


def radiance_hdr_to_bitmap_preview(
    *,
    garden_root: str,
    output_format: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_name: str | None = None,
    name: str | None = None,
    exposure: str | float | int | None = None,
    gamma: float | None = None,
    black_and_white: bool | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Convert a Radiance .hdr image into a BMP (ra_bmp) or PNG (ra_bmp + Pillow) preview."""
    fmt = output_format.strip().lower()
    if fmt not in {"bmp", "png"}:
        raise ValueError("output_format must be 'bmp' or 'png'.")

    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    input_path, record = _resolve_hdr_input(
        garden_root_path,
        run_target=run_target,
        run_id=run_id,
        image_path=image_path,
        image_name=image_name,
    )
    if record is not None:
        _validate_run_target_garden(record, manifest)

    identifier, output_path = _image_output_path(
        garden_root_path,
        name=name,
        input_path=input_path,
        suffix=f".{fmt}",
        output_subdir=output_subdir,
    )
    bmp_path = output_path if fmt == "bmp" else output_path.with_suffix(".tmp_ra_bmp.bmp")

    args: list[str] = ["ra_bmp"]
    if black_and_white:
        args.append("-b")
    if gamma is not None:
        args.extend(["-g", str(float(gamma))])
    if exposure is not None:
        args.extend(["-e", _format_ra_bmp_exposure(exposure)])
    if additional_options:
        args.extend(shlex.split(additional_options))
    args.extend(
        [
            to_posix_relative(input_path, garden_root_path),
            to_posix_relative(bmp_path, garden_root_path),
        ]
    )

    try:
        proc = subprocess.run(
            args,
            cwd=str(garden_root_path),
            env=_subprocess_env(),
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if proc.returncode != 0 or not bmp_path.is_file():
            detail = (proc.stderr or proc.stdout or "").strip()
            raise ValueError(
                f"ra_bmp failed with exit code {proc.returncode}"
                + (f": {detail}" if detail else ".")
            )
        if fmt == "png":
            from PIL import Image

            with Image.open(bmp_path) as img:
                img.save(output_path, format="PNG")
    finally:
        if fmt == "png" and bmp_path.exists():
            try:
                bmp_path.unlink()
            except OSError:
                pass

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise ValueError(f"Failed to produce {fmt.upper()} preview from HDR image.")

    artifact_type = RADIANCE_PNG_ARTIFACT_TYPE if fmt == "png" else RADIANCE_BMP_ARTIFACT_TYPE
    rel_input = to_posix_relative(input_path, garden_root_path)
    source = {
        "producer": "RAD_Process_HDR_Image",
        "operation": fmt,
        "input_path": rel_input,
        "run_id": record.get("run_id") if record else None,
        "command": " ".join(args),
    }
    saved = _save_image_artifact(
        garden_root=garden_root_path,
        manifest=manifest,
        path=output_path,
        name=identifier,
        image_format=fmt,
        artifact_type=artifact_type,
        source=source,
    )
    saved["summary_view"] = {
        "garden_target": manifest.target(),
        "target": saved["target"],
        "input_path": rel_input,
        "output_path": saved["target"]["path"],
        "format": fmt,
        "artifact_type": artifact_type,
    }
    saved["report"] = make_report(
        status="ok",
        message=f"Radiance {fmt.upper()} preview artifact created.",
    )
    return saved


def process_radiance_hdr_image(
    *,
    garden_root: str,
    operation: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    image_path: str | None = None,
    image_paths: list[str] | None = None,
    image_name: str | None = None,
    name: str | None = None,
    scale: str | float | None = None,
    legend_label: str | None = None,
    legend_multiplier: float | None = None,
    contour_lines: bool | None = None,
    contour_bands: bool | None = None,
    palette: str | None = None,
    exposure: float | int | None = None,
    gamma: float | None = None,
    black_and_white: bool | None = None,
    colors: int | None = None,
    sampling_factor: int | None = None,
    detailed: bool = True,
    threshold_factor: float | None = None,
    correction_mode: str | None = None,
    check_image: bool = False,
    check_image_name: str | None = None,
    human_vision: bool | None = None,
    x_res: int | str | None = None,
    y_res: int | str | None = None,
    radius: float | None = None,
    pixel_aspect: float | None = None,
    expression: str | None = None,
    dimensions_only: bool | None = None,
    additional_options: str | None = None,
    output_subdir: str = RADIANCE_IMAGE_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Process, analyze, or convert a Radiance .hdr image artifact."""
    normalized = operation.strip().lower().replace("-", "_")
    if normalized == "falsecolor":
        return radiance_hdr_to_falsecolor(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            scale=scale,
            legend_label=legend_label,
            legend_multiplier=legend_multiplier,
            contour_lines=contour_lines,
            contour_bands=contour_bands,
            palette=palette,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
    if normalized == "gif":
        return radiance_hdr_to_gif(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            exposure=int(exposure) if exposure is not None else None,
            gamma=gamma,
            black_and_white=black_and_white,
            colors=colors,
            sampling_factor=sampling_factor,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
    if normalized in {"png", "bmp"}:
        return radiance_hdr_to_bitmap_preview(
            garden_root=garden_root,
            output_format=normalized,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            exposure=exposure,
            gamma=gamma,
            black_and_white=black_and_white,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
    if normalized == "evalglare":
        return radiance_hdr_evalglare(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            detailed=detailed,
            threshold_factor=threshold_factor,
            correction_mode=correction_mode,
            check_image=check_image,
            check_image_name=check_image_name,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
    if normalized == "pcond":
        return radiance_hdr_pcond(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            human_vision=human_vision,
            exposure=exposure,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
    if normalized == "pfilt":
        return radiance_hdr_pfilt(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            x_res=x_res,
            y_res=y_res,
            exposure=exposure,
            radius=radius,
            pixel_aspect=pixel_aspect,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
    if normalized == "pcomb":
        return radiance_hdr_pcomb(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_paths=image_paths,
            image_name=image_name,
            name=name,
            expression=expression,
            x_res=int(x_res) if x_res is not None else None,
            y_res=int(y_res) if y_res is not None else None,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
    if normalized == "getinfo":
        return radiance_hdr_getinfo(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            dimensions_only=dimensions_only,
            additional_options=additional_options,
        )
    raise ValueError(
        "operation must be one of: falsecolor, gif, png, bmp, evalglare, pcond, pfilt, pcomb, getinfo."
    )
