"""Radiance visual postprocess services."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from typing import Any

from honeybee_display.model import model_to_vis_set
from honeybee_radiance_command.falsecolor import Falsecolor
from honeybee_radiance_command.options.falsecolor import FalsecolorOptions
from honeybee_radiance_command.options.ra_gif import Ra_GIFOptions
from honeybee_radiance_command.ra_gif import Ra_GIF

from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report
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
RADIANCE_IMAGE_OUTPUT_SUBDIR = "artifacts/radiance/images"
GRID_DISPLAY_MODES = {"Surface", "SurfaceWithEdges", "Wireframe", "Points"}
MODEL_COLOR_BY = {"type", "boundary_condition", "none"}
MIN_FALSECOLOR_HDR_BYTES = 128


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


def _relative_path(garden_root: Path, path: Path) -> str:
    return to_posix_relative(path.resolve(), garden_root)


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
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (item.get("artifact_type") == artifact_type and item.get("path") == path)
    ]
    manifest.artifacts.append(record)
    return record


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
    artifact_path = _relative_path(garden_root, path)
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


def _run_radiance_command(command: Any, *, cwd: str | None = None) -> int:
    apply_ladybug_tools_runtime_to_path()
    return int(command.run(cwd=cwd))


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
                "path": _relative_path(garden_root_path, path),
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
    command = Falsecolor(options=options, output=str(output_path), input=str(input_path))
    rc = _run_radiance_command(command, cwd=str(garden_root_path))
    if rc != 0:
        raise ValueError(f"falsecolor command failed with exit code {rc}.")
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
        "producer": "radiance_hdr_to_falsecolor",
        "input_path": _relative_path(garden_root_path, input_path),
        "run_id": record.get("run_id") if record else None,
        "command": command.to_radiance(),
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
    command = Ra_GIF(options=options, output=str(output_path), input=str(input_path))
    rc = _run_radiance_command(command, cwd=str(garden_root_path))
    if rc != 0:
        raise ValueError(f"ra_gif command failed with exit code {rc}.")
    if not output_path.is_file():
        raise ValueError("ra_gif command completed without writing an output file.")

    source = {
        "producer": "radiance_hdr_to_gif",
        "input_path": _relative_path(garden_root_path, input_path),
        "run_id": record.get("run_id") if record else None,
        "command": command.to_radiance(),
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
        "path": _relative_path(garden_root, folder),
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
        path = _resolve_output_path(garden_root, record, output_name or "results")
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
        raise ValueError("radiance_grid_result_to_visualization_set requires a model target.")
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
            "producer": "radiance_grid_result_to_visualization_set",
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
