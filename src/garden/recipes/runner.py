"""Schema-driven generic Queenbee / lbt-recipes introspection and background runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import lbt_recipes
from lbt_recipes.recipe import Recipe

from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import simulation_folder_name, to_posix_relative
from garden.radiance.run import (
    RADIANCE_RUNS_DIR,
    _RADIANCE_RUNS,
    _clear_recipe_status_logs,
    _garden_root,
    _materialize_schedule_input,
    _missing_outputs,
    _normalize_grid_metrics,
    _normalize_run_id,
    _radiance_parameters_from_input,
    _read_index,
    _recipe_output_specs,
    _resolve_sky_input,
    _resolve_wea_path,
    _run_response,
    _run_target,
    _submit_radiance_background,
    _upsert_record,
    _write_text_input,
)
from garden.radiance.sky import _resolve_epw_path
from garden.run_ledger import serialized_run_start
from ladybug_tools_mcp.contracts import make_report


def _installed_recipe_dirs() -> dict[str, Path]:
    """Discover all installed lbt-recipes packages containing package.json."""
    pkg_dir = Path(lbt_recipes.__file__).resolve().parent
    found: dict[str, Path] = {}
    for pkg_json in sorted(pkg_dir.glob("*/package.json")):
        folder = pkg_json.parent
        name = folder.name.replace("_", "-")
        found[name] = folder
    return found


def resolve_recipe_source(recipe_or_path: str) -> tuple[str, str, bool]:
    """Resolve an installed recipe name or external Queenbee recipe folder path.

    Returns:
        (canonical_recipe_name, recipe_source_arg_for_Recipe, is_external)
    """
    raw = str(recipe_or_path or "").strip()
    if not raw:
        raise ValueError("recipe must be a non-empty lbt-recipes name or folder path.")
    candidate = Path(raw).expanduser()
    if candidate.is_dir() and (candidate / "package.json").is_file():
        resolved_dir = candidate.resolve()
        try:
            meta = json.loads((resolved_dir / "package.json").read_text(encoding="utf-8"))
            name = str((meta.get("metadata") or {}).get("name") or resolved_dir.name)
        except Exception:
            name = resolved_dir.name
        return name.replace("_", "-"), str(resolved_dir), True

    normalized = raw.lower().replace("_", "-")
    installed = _installed_recipe_dirs()
    if normalized in installed:
        return normalized, normalized, False
    # Also try loading directly in case lbt_recipes resolves another plugin location.
    try:
        Recipe(normalized)
        return normalized, normalized, False
    except Exception as exc:
        raise ValueError(
            f"Unknown recipe or missing Queenbee recipe folder '{recipe_or_path}'. "
            f"Installed recipes: {', '.join(sorted(installed))}."
        ) from exc


def _target_hint_for_input(name: str) -> str | None:
    hints = {
        "model": "model_target (HBJSON)",
        "epw": "weather_file_target / weather_target / epw_path",
        "ddy": "ddy_path or weather_file_target / epw_path",
        "wea": "wea_target / wea_path (or EPW)",
        "sky": "radiance_sky_file / sky string",
        "schedule": "schedule_target / csv path / inline CSV",
        "sim-par": "simulation_parameter_target / SimulationParameter JSON",
        "radiance-parameters": "RAD_Create_Parameters result or string",
    }
    return hints.get(name)


def _describe_recipe_obj(recipe: Recipe, *, recipe_name: str, is_external: bool) -> dict[str, Any]:
    recipe_path = Path(recipe.path)
    pkg_json_path = recipe_path / "package.json"
    pkg_meta: dict[str, Any] = {}
    if pkg_json_path.is_file():
        try:
            pkg_meta = json.loads(pkg_json_path.read_text(encoding="utf-8")).get("metadata") or {}
        except Exception:
            pkg_meta = {}

    inputs_meta: list[dict[str, Any]] = []
    for inp in recipe.inputs:
        handlers = [
            getattr(h, "__name__", repr(h))
            for h in (getattr(inp, "handlers", None) or [])
        ]
        inputs_meta.append(
            {
                "name": inp.name,
                "python_name": inp.name.replace("-", "_"),
                "required": bool(inp.is_required),
                "default_value": inp.default_value,
                "is_path": bool(inp.is_path),
                "description": inp.description,
                "handlers": handlers,
                "garden_hint": _target_hint_for_input(inp.name),
            }
        )

    outputs_meta: list[dict[str, Any]] = []
    for spec in _recipe_output_specs(recipe_path if is_external else recipe_name):
        from_ref = spec.get("from") or {}
        outputs_meta.append(
            {
                "name": spec.get("name"),
                "description": spec.get("description"),
                "required": bool(spec.get("required", True)),
                "from_path": from_ref.get("path"),
                "from_type": from_ref.get("type"),
            }
        )

    return {
        "name": recipe_name,
        "tag": pkg_meta.get("tag"),
        "description": pkg_meta.get("description") or recipe.description,
        "keywords": pkg_meta.get("keywords") or [],
        "is_external": is_external,
        "folder": str(recipe_path),
        "inputs": inputs_meta,
        "required_inputs": [item["name"] for item in inputs_meta if item["required"]],
        "optional_inputs": [item["name"] for item in inputs_meta if not item["required"]],
        "outputs": outputs_meta,
    }


def list_recipes() -> dict[str, Any]:
    """List all installed lbt-recipes packages and their key I/O summaries."""
    installed = _installed_recipe_dirs()
    entries: list[dict[str, Any]] = []
    for name, folder in installed.items():
        pkg_data = json.loads((folder / "package.json").read_text(encoding="utf-8"))
        meta = pkg_data.get("metadata") or {}
        raw_inputs = pkg_data.get("inputs") or []
        raw_outputs = pkg_data.get("outputs") or []
        required_inputs = [item["name"] for item in raw_inputs if item.get("required")]
        optional_inputs = [item["name"] for item in raw_inputs if not item.get("required")]
        entries.append(
            {
                "name": name,
                "tag": meta.get("tag"),
                "description": meta.get("description"),
                "keywords": meta.get("keywords") or [],
                "required_inputs": required_inputs,
                "optional_inputs": optional_inputs,
                "outputs": [item.get("name") for item in raw_outputs],
            }
        )
    return {
        "recipes": entries,
        "summary_view": {
            "count": len(entries),
            "recipe_names": [entry["name"] for entry in entries],
        },
        "report": make_report(
            status="ok",
            message=f"Discovered {len(entries)} installed lbt-recipes recipe(s).",
        ),
    }


def describe_recipe(recipe: str) -> dict[str, Any]:
    """Return full schema metadata (inputs, outputs, defaults, handlers) for any recipe."""
    canonical_name, recipe_source, is_external = resolve_recipe_source(recipe)
    recipe_obj = Recipe(recipe_source)
    schema = _describe_recipe_obj(
        recipe_obj,
        recipe_name=canonical_name,
        is_external=is_external,
    )
    return {
        "recipe": schema,
        "summary_view": schema,
        "report": make_report(
            status="ok",
            message=f"Described Queenbee recipe: {canonical_name}.",
        ),
    }


def _resolve_ddy_input(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    ddy_path: str | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> str | None:
    if ddy_path is not None:
        p = Path(ddy_path).expanduser()
        if not p.is_absolute():
            p = (garden_root / p).resolve()
        else:
            p = p.resolve()
        p.relative_to(garden_root)
        if not p.is_file():
            raise ValueError(f"ddy_path was not found inside the Garden: {ddy_path}")
        return str(p)
    if weather_target is not None:
        ddy_rel = weather_target.get("ddy_path")
        if isinstance(ddy_rel, str) and ddy_rel:
            candidate = (garden_root / ddy_rel).resolve()
            candidate.relative_to(garden_root)
            if candidate.is_file():
                return str(candidate)
        epw, _ = _resolve_epw_path(
            garden_root=garden_root,
            manifest=manifest,
            weather_target=weather_target,
            epw_path=None,
        )
        return str(epw)
    if epw_path is not None:
        epw, _ = _resolve_epw_path(
            garden_root=garden_root,
            manifest=manifest,
            weather_target=None,
            epw_path=epw_path,
        )
        return str(epw)
    return None


def _materialize_sim_par(
    *,
    garden_root: Path,
    run_dir: Path,
    sim_par: dict[str, Any] | str | None,
) -> Any:
    if sim_par is None:
        return None
    if isinstance(sim_par, str):
        p = Path(sim_par).expanduser()
        if not p.is_absolute():
            p = (garden_root / p).resolve()
        if p.is_file():
            return str(p)
        return sim_par
    if isinstance(sim_par, dict):
        if sim_par.get("target_type") == "garden_properties_library_object":
            from garden.libraries.properties import get_garden_properties_library_object

            sim_par = get_garden_properties_library_object(
                garden_root=str(garden_root),
                target=sim_par,
            )["object_dict"]
        elif isinstance(sim_par.get("object_dict"), dict):
            sim_par = sim_par["object_dict"]
        return _write_text_input(
            run_dir,
            "simulation_parameter.json",
            json.dumps(sim_par, indent=2),
        )
    return sim_par


def _materialize_data_or_file_input(
    *,
    garden_root: Path,
    run_dir: Path,
    input_name: str,
    value: Any,
) -> Any:
    if value is None:
        return None
    if isinstance(value, dict) and value.get("target_type") == "data_collection":
        rel = value.get("path")
        if isinstance(rel, str) and rel:
            from ladybug.datacollection import BaseCollection

            p = (garden_root / rel).resolve()
            p.relative_to(garden_root)
            dc = BaseCollection.from_dict(json.loads(p.read_text(encoding="utf-8")))
            lines = "\n".join(str(v) for v in dc.values)
            return _write_text_input(run_dir, f"{input_name.replace('-', '_')}.csv", lines)
    if isinstance(value, list):
        lines = "\n".join(str(v) for v in value)
        return _write_text_input(run_dir, f"{input_name.replace('-', '_')}.csv", lines)
    return value


def _calculation_metadata(recipe_name: str) -> tuple[str, str]:
    if "comfort-map" in recipe_name:
        return "comfort", recipe_name.replace("-", "_")
    if "energy" in recipe_name:
        return "energy", recipe_name.replace("-", "_")
    if "view" in recipe_name:
        return "view", "rpict"
    if "glare" in recipe_name:
        return "glare", "rfluxmtx"
    if any(k in recipe_name for k in ("leed", "well", "breeam", "en17037")):
        return "compliance", recipe_name.replace("-", "_")
    if any(k in recipe_name for k in ("annual", "cumulative", "direct-sun")):
        return "matrix", "rfluxmtx"
    return "recipe", "rtrace"


@serialized_run_start
def start_generic_recipe(
    *,
    garden_root: str,
    recipe: str,
    model_target: dict[str, Any] | None = None,
    weather_file_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    ddy_path: str | None = None,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    radiance_sky_file: dict[str, Any] | None = None,
    sky_file_target: dict[str, Any] | None = None,
    sky: str | None = None,
    schedule: Any = None,
    sim_par: dict[str, Any] | str | None = None,
    radiance_parameters: str | dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    recipe_options: dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    debug_folder: str | None = None,
) -> dict[str, Any]:
    """Start any lbt-recipes recipe or external local Queenbee recipe folder asynchronously."""
    canonical_name, recipe_source, is_external = resolve_recipe_source(recipe)
    recipe_obj = Recipe(recipe_source)
    schema_inputs = {inp.name: inp for inp in recipe_obj.inputs}

    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    eff_weather_target = weather_file_target if weather_file_target is not None else weather_target
    eff_sky_target = radiance_sky_file if radiance_sky_file is not None else sky_file_target

    merged_raw: dict[str, Any] = {}
    for source_dict in (recipe_options or {}, inputs or {}):
        if not isinstance(source_dict, dict):
            raise ValueError("inputs and recipe_options must be dictionaries.")
        for k, v in source_dict.items():
            merged_raw[str(k).strip().lower().replace("_", "-")] = v

    resolved_model_target: dict[str, Any] | None = None
    model_path: Path | None = None
    model_display_name = canonical_name
    if "model" in schema_inputs or model_target is not None:
        if "model" in schema_inputs or model_target is not None:
            try:
                manifest, resolved_model_target = resolve_model_target(
                    garden_root_path,
                    model_target,
                )
                rel_model = resolved_model_target.get("path")
                if isinstance(rel_model, str) and rel_model:
                    model_path = (garden_root_path / rel_model).resolve()
                    model_path.relative_to(garden_root_path)
                model_obj = load_honeybee_model(garden_root_path, resolved_model_target)
                model_display_name = getattr(model_obj, "display_name", None) or str(
                    resolved_model_target.get("model_identifier") or canonical_name
                )
            except Exception:
                if "model" in schema_inputs and schema_inputs["model"].is_required and "model" not in merged_raw:
                    raise

    normalized_run_id = _normalize_run_id(run_id)
    for record in _read_index(garden_root_path):
        if record.get("run_id") == normalized_run_id:
            existing_status = str(record.get("status", "unknown"))
            return _run_response(
                garden_root_path=garden_root_path,
                manifest=manifest,
                record=record,
                message=(
                    f"Radiance run already exists with status {existing_status}; "
                    "returning the existing run target."
                ),
                report_status="ok" if existing_status in {"running", "completed"} else "warning",
                warnings=[
                    "No new recipe was started because run_id already exists. "
                    "Use a different run_id for a fresh run."
                ],
            )

    run_dir = (
        garden_root_path
        / RADIANCE_RUNS_DIR
        / simulation_folder_name(f"{model_display_name}_{normalized_run_id}")
    ).resolve()
    run_dir.relative_to(garden_root_path)
    run_folder = to_posix_relative(run_dir, garden_root_path)
    _RADIANCE_RUNS.prepare_folder(
        garden_root_path,
        run_folder,
        recipe=canonical_name,
        model_target=resolved_model_target or {"model_identifier": model_display_name},
        preserve_other_recipes=True,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    _clear_recipe_status_logs(run_dir, canonical_name, simulation_id=normalized_run_id)

    resolved_inputs: dict[str, Any] = {}
    if "model" in schema_inputs and "model" not in merged_raw:
        if model_path is not None:
            resolved_inputs["model"] = str(model_path)

    if "epw" in schema_inputs and "epw" not in merged_raw:
        if eff_weather_target is not None or epw_path is not None:
            resolved_epw, _ = _resolve_epw_path(
                garden_root=garden_root_path,
                manifest=manifest,
                weather_target=eff_weather_target,
                epw_path=epw_path,
            )
            resolved_inputs["epw"] = str(resolved_epw)

    if "ddy" in schema_inputs and "ddy" not in merged_raw:
        ddy_val = _resolve_ddy_input(
            garden_root=garden_root_path,
            manifest=manifest,
            ddy_path=ddy_path,
            weather_target=eff_weather_target,
            epw_path=epw_path,
        )
        if ddy_val is not None:
            resolved_inputs["ddy"] = ddy_val

    if "wea" in schema_inputs and "wea" not in merged_raw:
        if wea_target is not None or wea_path is not None:
            resolved_inputs["wea"] = _resolve_wea_path(
                garden_root=garden_root_path,
                manifest=manifest,
                wea_target=wea_target,
                wea_path=wea_path,
            )
        elif eff_weather_target is not None or epw_path is not None:
            resolved_epw, _ = _resolve_epw_path(
                garden_root=garden_root_path,
                manifest=manifest,
                weather_target=eff_weather_target,
                epw_path=epw_path,
            )
            resolved_inputs["wea"] = str(resolved_epw)

    if "sky" in schema_inputs and "sky" not in merged_raw:
        if eff_sky_target is not None or sky is not None:
            resolved_inputs["sky"] = _resolve_sky_input(
                garden_root=garden_root_path,
                manifest=manifest,
                sky_file_target=eff_sky_target,
                sky=sky,
            )

    if "radiance-parameters" in schema_inputs and radiance_parameters is not None:
        rad_par = _radiance_parameters_from_input(radiance_parameters)
        if rad_par is not None:
            resolved_inputs["radiance-parameters"] = rad_par

    if "schedule" in schema_inputs and schedule is not None and "schedule" not in merged_raw:
        mat_sch = _materialize_schedule_input(
            garden_root_path=garden_root_path,
            manifest=manifest,
            run_dir=run_dir,
            schedule=schedule,
        )
        if mat_sch is not None:
            resolved_inputs["schedule"] = mat_sch

    if "sim-par" in schema_inputs and sim_par is not None and "sim-par" not in merged_raw:
        mat_sp = _materialize_sim_par(
            garden_root=garden_root_path,
            run_dir=run_dir,
            sim_par=sim_par,
        )
        if mat_sp is not None:
            resolved_inputs["sim-par"] = mat_sp

    for key, val in merged_raw.items():
        if val is None or key not in schema_inputs:
            continue
        if key == "schedule":
            resolved_inputs[key] = _materialize_schedule_input(
                garden_root_path=garden_root_path,
                manifest=manifest,
                run_dir=run_dir,
                schedule=val,
            )
        elif key == "grid-metrics":
            resolved_inputs[key] = _normalize_grid_metrics(val)
        elif key in {"air-speed", "clo-value", "met-rate"}:
            resolved_inputs[key] = _materialize_data_or_file_input(
                garden_root=garden_root_path,
                run_dir=run_dir,
                input_name=key,
                value=val,
            )
        elif key == "sim-par":
            resolved_inputs[key] = _materialize_sim_par(
                garden_root=garden_root_path,
                run_dir=run_dir,
                sim_par=val,
            )
        else:
            resolved_inputs[key] = val

    if workers is not None and "cpu-count" in schema_inputs and "cpu-count" not in resolved_inputs:
        resolved_inputs["cpu-count"] = workers

    missing_required = [
        name
        for name, inp in schema_inputs.items()
        if inp.is_required and (name not in resolved_inputs or resolved_inputs[name] is None)
    ]
    if missing_required:
        raise ValueError(
            f"Missing required input(s) for recipe '{canonical_name}': "
            + ", ".join(missing_required)
        )

    resolved_debug_folder: str | None = None
    if debug_folder:
        dbg_path = Path(debug_folder).expanduser()
        if not dbg_path.is_absolute():
            dbg_path = (garden_root_path / dbg_path).resolve()
        else:
            dbg_path = dbg_path.resolve()
        dbg_path.relative_to(garden_root_path)
        dbg_path.mkdir(parents=True, exist_ok=True)
        resolved_debug_folder = str(dbg_path)

    calc_family, calc_type = _calculation_metadata(canonical_name)
    target = _run_target(manifest.garden_id, normalized_run_id, canonical_name)
    record: dict[str, Any] = {
        "run_id": normalized_run_id,
        "simulation_id": normalized_run_id,
        "target": target,
        "recipe": canonical_name,
        "recipe_source": recipe_source,
        "is_external_recipe": is_external,
        "calculation_family": calc_family,
        "calculation_type": calc_type,
        "command_name": canonical_name if is_external else calc_type,
        "status": "running",
        "created_at": utc_now_iso(),
        "model_target": resolved_model_target,
        "model_display_name": model_display_name,
        "model_path": to_posix_relative(model_path, garden_root_path) if model_path else None,
        "run_folder": run_folder,
        "debug_folder": (
            to_posix_relative(Path(resolved_debug_folder), garden_root_path)
            if resolved_debug_folder
            else None
        ),
        "outputs": _missing_outputs(recipe_source, simulation_id=normalized_run_id),
        "workers": workers,
        "warnings": [],
    }
    _upsert_record(garden_root_path, record)

    try:
        proc = _submit_radiance_background(
            garden_root=str(garden_root_path),
            recipe_name=canonical_name,
            recipe_source=recipe_source,
            inputs=resolved_inputs,
            run_id=normalized_run_id,
            model_target=resolved_model_target or {},
            calculation_family=calc_family,
            calculation_type=calc_type,
            command_name=canonical_name,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=resolved_debug_folder,
        )
    except Exception as exc:
        record.update(
            {
                "status": "failed",
                "completed_at": utc_now_iso(),
                "outputs": _missing_outputs(recipe_source, simulation_id=normalized_run_id),
                "warnings": [f"Recipe could not be started: {exc}"],
            }
        )
        _upsert_record(garden_root_path, record)
        return _run_response(
            garden_root_path=garden_root_path,
            manifest=manifest,
            record=record,
            message="Recipe could not be started; run record was saved.",
            report_status="error",
        )

    worker_pid = getattr(proc, "pid", None)
    if worker_pid is not None:
        latest = _RADIANCE_RUNS.get(garden_root_path, normalized_run_id)
        if latest is not None:
            record = dict(latest)
        record["worker_pid"] = worker_pid
        _upsert_record(garden_root_path, record)

    return _run_response(
        garden_root_path=garden_root_path,
        manifest=manifest,
        record=record,
        message=(
            f"Started recipe '{canonical_name}' in background."
            if record.get("status") == "running"
            else f"Recipe '{canonical_name}' finished with status {record.get('status')}."
        ),
        report_status="error" if record.get("status") == "failed" else "ok",
    )


def manage_recipes(
    *,
    action: str,
    recipe: str | None = None,
    garden_root: str | None = None,
    model_target: dict[str, Any] | None = None,
    weather_file_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    ddy_path: str | None = None,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    radiance_sky_file: dict[str, Any] | None = None,
    sky_file_target: dict[str, Any] | None = None,
    sky: str | None = None,
    schedule: Any = None,
    sim_par: dict[str, Any] | str | None = None,
    radiance_parameters: str | dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    recipe_options: dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    debug_folder: str | None = None,
) -> dict[str, Any]:
    """Dispatch schema-driven recipe discovery, inspection, or execution."""
    normalized = str(action or "").strip().lower().replace("-", "_")
    if normalized == "list":
        return list_recipes()
    if normalized == "describe":
        if not recipe:
            raise ValueError("recipe is required when action='describe'.")
        return describe_recipe(recipe)
    if normalized == "start":
        if not garden_root:
            raise ValueError("garden_root is required when action='start'.")
        if not recipe:
            raise ValueError("recipe is required when action='start'.")
        return start_generic_recipe(
            garden_root=garden_root,
            recipe=recipe,
            model_target=model_target,
            weather_file_target=weather_file_target,
            weather_target=weather_target,
            epw_path=epw_path,
            ddy_path=ddy_path,
            wea_target=wea_target,
            wea_path=wea_path,
            radiance_sky_file=radiance_sky_file,
            sky_file_target=sky_file_target,
            sky=sky,
            schedule=schedule,
            sim_par=sim_par,
            radiance_parameters=radiance_parameters,
            inputs=inputs,
            recipe_options=recipe_options,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=debug_folder,
        )
    raise ValueError("action must be 'list', 'describe', or 'start'.")
