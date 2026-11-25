"""Garden-backed Honeybee and Dragonfly model export services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import dragonfly_designbuilder._extend_dragonfly  # noqa: F401
import dragonfly_doe2._extend_dragonfly  # noqa: F401
import dragonfly_radiance  # noqa: F401
import honeybee_designbuilder._extend_honeybee  # noqa: F401
import honeybee_doe2._extend_honeybee  # noqa: F401
import honeybee_gbas._extend_honeybee  # noqa: F401
from dragonfly_designbuilder.writer import model_to_dsbxml as dragonfly_model_to_dsbxml
from dragonfly_doe2.writer import model_to_inp as dragonfly_model_to_inp
from dragonfly_energy.gbxml.parameters import GBXMLParameters
from dragonfly_energy.writer import model_to_gbxml as dragonfly_model_to_gbxml
from honeybee_designbuilder.writer import model_to_dsbxml as honeybee_model_to_dsbxml
from honeybee_doe2.writer import model_to_inp as honeybee_model_to_inp
from honeybee_gbas.writer import model_to_dwg as honeybee_model_to_gbas_dwg
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.writer import _preprocess_model_for_trace_3dplus
from honeybee_openstudio.openstudio import openstudio
from honeybee_openstudio.simulation import simulation_parameter_to_openstudio
from honeybee_openstudio.writer import (
    model_to_epjson as honeybee_model_to_epjson,
    model_to_gbxml as honeybee_openstudio_model_to_gbxml,
    model_to_idf as honeybee_openstudio_model_to_idf,
    model_to_openstudio,
    model_to_osm as honeybee_model_to_osm,
)
from honeybee_radiance.writer import (
    model_to_rad as honeybee_model_to_rad,
    model_to_rad_folder as honeybee_model_to_rad_folder,
)

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    normalize_dragonfly_model_target,
)
from garden.dragonfly_core.targets import is_dragonfly_model_target
from garden.honeybee_core.model_io import load_honeybee_model
from garden.honeybee_core.targets import (
    is_honeybee_model_target,
    normalize_honeybee_model_target,
)
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

DOE_INP_EXPORT_FORMAT = "doe_inp"
DESIGNBUILDER_DSBXML_EXPORT_FORMAT = "designbuilder_dsbxml"
FORMAT_GBAS_DWG = "gbas_dwg"
FORMAT_OSM = "osm"
FORMAT_IDF = "idf"
FORMAT_EPJSON = "epjson"
FORMAT_GBXML = "gbxml"
FORMAT_TRACE_GBXML = "trace_gbxml"
FORMAT_SDD = "sdd"
FORMAT_RAD = "rad"
FORMAT_RAD_FOLDER = "rad_folder"
FORMAT_HBPKL = "hbpkl"
FORMAT_STL = "stl"

MODEL_EXPORT_ARTIFACT_DIR = Path("artifacts") / "model_export"

_EXPORT_EXTENSIONS = {
    DOE_INP_EXPORT_FORMAT: ".inp",
    DESIGNBUILDER_DSBXML_EXPORT_FORMAT: ".dsbxml",
    FORMAT_GBAS_DWG: ".dwg",
    FORMAT_OSM: ".osm",
    FORMAT_IDF: ".idf",
    FORMAT_EPJSON: ".epjson",
    FORMAT_GBXML: ".xml",
    FORMAT_TRACE_GBXML: ".xml",
    FORMAT_SDD: ".xml",
    FORMAT_RAD: ".rad",
    FORMAT_RAD_FOLDER: "",
    FORMAT_HBPKL: ".hbpkl",
    FORMAT_STL: ".stl",
}

_BINARY_OR_DIR_FORMATS = {FORMAT_HBPKL, FORMAT_RAD_FOLDER, FORMAT_GBAS_DWG}


def export_model_file(
    *,
    garden_root: str,
    export_format: str,
    model_target: dict[str, Any],
    name: str | None = None,
    include_body: bool = False,
    export_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export a Garden Honeybee or Dragonfly model to a supported file or folder artifact."""
    normalized_format = _normalize_export_format(export_format)
    options = _normalize_export_options(export_options)
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    model_domain, resolved_model_target = _normalize_model_target(model_target)
    _validate_model_target_path(
        garden_root=garden_root_path,
        manifest=manifest,
        model_domain=model_domain,
        model_target=resolved_model_target,
    )

    model = (
        load_honeybee_model(garden_root_path, resolved_model_target)
        if model_domain == "honeybee"
        else load_dragonfly_model(garden_root_path, resolved_model_target)
    )

    identifier = slugify_name(name or f"{model.identifier}_{normalized_format}")
    extension = _EXPORT_EXTENSIONS[normalized_format]
    output_dir = garden_root_path / MODEL_EXPORT_ARTIFACT_DIR / normalized_format
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        output_dir / identifier
        if normalized_format == FORMAT_RAD_FOLDER
        else output_dir / f"{identifier}{extension}"
    )
    gbas_report_path = (
        _resolve_gbas_report_path(
            options,
            garden_root_path=garden_root_path,
            output_dir=output_dir,
            output_path=output_path,
            identifier=identifier,
        )
        if normalized_format == FORMAT_GBAS_DWG
        else None
    )

    stored_text, extra_summary = _perform_export(
        model=model,
        model_domain=model_domain,
        export_format=normalized_format,
        output_dir=output_dir,
        output_path=output_path,
        identifier=identifier,
        options=options,
        garden_root_path=garden_root_path,
        gbas_report_path=gbas_report_path,
    )

    artifact_path = to_posix_relative(output_path, garden_root_path)
    target = make_model_export_artifact_target(
        manifest=manifest,
        export_format=normalized_format,
        identifier=identifier,
        path=artifact_path,
    )
    manifest.upsert_artifact(target, key_fields=("artifact_type", "identifier"))

    report_target: dict[str, Any] | None = None
    if (
        normalized_format == FORMAT_GBAS_DWG
        and gbas_report_path is not None
        and gbas_report_path.is_file()
    ):
        report_rel_path = to_posix_relative(gbas_report_path, garden_root_path)
        report_target = {
            **make_model_export_artifact_target(
                manifest=manifest,
                export_format="gbas_selfcheck_report",
                identifier=identifier,
                path=report_rel_path,
            ),
            "dwg_identifier": identifier,
            "dwg_target": target,
            "model_domain": model_domain,
            "model_target": resolved_model_target,
        }
        manifest.upsert_artifact(report_target, key_fields=("artifact_type", "identifier"))

    manifest.write(garden_root_path)

    warnings: list[str] = []
    if include_body and normalized_format in _BINARY_OR_DIR_FORMATS:
        warnings.append(
            f"include_body is not supported for {normalized_format}; use target path {artifact_path}."
        )
    for item in extra_summary.get("self_check_warnings") or []:
        if isinstance(item, dict):
            code = str(item.get("code") or "unknown")
            followup = str(item.get("followup") or "").strip()
            warnings.append(
                f"GBAS pre-import warning ({code}): {followup}"
                if followup
                else f"GBAS pre-import warning ({code})."
            )
        elif item:
            warnings.append(str(item))

    summary_view: dict[str, Any] = {
        "target": target,
        "export_format": normalized_format,
        "model_domain": model_domain,
        "model_target": resolved_model_target,
        "path": artifact_path,
        "extension": extension,
        "export_options": options,
        **extra_summary,
    }
    if report_target is not None:
        summary_view["report_artifact"] = report_target
        summary_view["report_target"] = report_target
    result: dict[str, Any] = {
        "target": target,
        "model_export_artifact_target": target,
        "summary_view": summary_view,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=normalized_format,
            artifact_path=artifact_path,
            absolute_path=str(output_path),
            source={
                "export_format": normalized_format,
                "model_domain": model_domain,
                "model_target": resolved_model_target,
                "export_options": options,
            },
        ),
        "report": make_report(
            status="warning" if warnings else "ok",
            message=(
                f"Wrote {normalized_format} export artifact from "
                f"{model_domain} model: {identifier}"
            ),
            warnings=warnings,
        ),
    }
    if include_body and stored_text is not None:
        result["file_body"] = stored_text
    return result


def make_model_export_artifact_target(
    *,
    manifest: GardenManifest,
    export_format: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a model export artifact target."""
    return {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "domain": "model_export",
        "artifact_type": export_format,
        "identifier": identifier,
        "path": path,
    }


def _normalize_export_format(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in _EXPORT_EXTENSIONS:
        allowed = ", ".join(sorted(_EXPORT_EXTENSIONS))
        raise ValueError(f"export_format must be one of: {allowed}.")
    return normalized


def _normalize_export_options(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("export_options must be a dictionary when provided.")
    return dict(value)


def _normalize_model_target(value: Any) -> tuple[str, dict[str, Any]]:
    if value is None:
        raise ValueError("model_target is required.")
    if is_honeybee_model_target(value):
        return "honeybee", normalize_honeybee_model_target(value)
    if is_dragonfly_model_target(value):
        return "dragonfly", normalize_dragonfly_model_target(value)
    raise ValueError("model_target must be a Honeybee Model or Dragonfly Model target.")


def _validate_model_target_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    model_domain: str,
    model_target: dict[str, Any],
) -> None:
    if model_target.get("garden_id") != manifest.garden_id:
        raise ValueError("model_target belongs to a different Garden.")
    path_value = model_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("model_target requires a Garden-relative path.")
    path = Path(path_value)
    if path.is_absolute():
        raise ValueError("model_target path must be Garden-relative.")
    resolved = (garden_root / path).resolve()
    try:
        resolved.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("model_target path must stay inside the Garden.") from exc
    expected_suffix = ".hbjson" if model_domain == "honeybee" else ".dfjson"
    if resolved.suffix.lower() != expected_suffix:
        raise ValueError(f"model_target path must point to a {expected_suffix} file.")
    if not resolved.is_file():
        raise ValueError(f"Model file not found: {path_value}")


def _pick_kwargs(options: dict[str, Any], allowed_keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: options[key] for key in allowed_keys if key in options and options[key] is not None}


def _resolve_gbas_report_path(
    options: dict[str, Any],
    *,
    garden_root_path: Path,
    output_dir: Path,
    output_path: Path,
    identifier: str,
) -> Path | None:
    """Resolve and validate an optional Garden-local GBAS JSON report path."""
    raw_report_path = options.get("report_path")
    write_report = bool(options.get("write_report", False))
    report_name = options.get("report_name")

    if isinstance(raw_report_path, bool):
        write_report = write_report or raw_report_path
        raw_report_path = None

    if raw_report_path is not None:
        if not isinstance(raw_report_path, str) or not raw_report_path.strip():
            raise ValueError("export_options.report_path must be a non-empty Garden-relative path.")
        candidate_input = Path(raw_report_path)
        if candidate_input.is_absolute():
            raise ValueError("export_options.report_path must be Garden-relative.")
        resolved_garden_root = garden_root_path.resolve()
        candidate = (resolved_garden_root / candidate_input).resolve()
        try:
            candidate.relative_to(resolved_garden_root)
        except ValueError as exc:
            raise ValueError("export_options.report_path must stay inside the Garden.") from exc
        if candidate.suffix.lower() != ".json":
            raise ValueError("export_options.report_path must end with .json.")
        if candidate == output_path.resolve():
            raise ValueError("export_options.report_path must differ from the output DWG path.")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    if write_report or report_name:
        report_stem = slugify_name(str(report_name)) if report_name else identifier
        return output_dir / f"{report_stem}.report.json"

    return None


def _dragonfly_to_honeybee(model: Any, options: dict[str, Any]) -> Any:
    df_copy = model.duplicate()
    if getattr(df_copy, "units", "Meters") != "Meters":
        df_copy.convert_to_units("Meters")
    use_multiplier = options.get("use_multiplier")
    if use_multiplier is None and "full_geometry" in options:
        use_multiplier = not bool(options["full_geometry"])
    if use_multiplier is None:
        use_multiplier = True
    exclude_plenums = bool(
        options.get("exclude_plenums", options.get("no_plenum", False))
    )
    solve_ceiling_adjacencies = bool(
        options.get("solve_ceiling_adjacencies", options.get("ceil_adjacency", False))
    )
    hb_models = df_copy.to_honeybee(
        object_per_model=options.get("object_per_model", "District"),
        shade_distance=options.get("shade_distance"),
        use_multiplier=bool(use_multiplier),
        exclude_plenums=exclude_plenums,
        solve_ceiling_adjacencies=solve_ceiling_adjacencies,
        merge_method=options.get("merge_method"),
        tolerance=options.get("tolerance"),
        enforce_adj=bool(options.get("enforce_adj", False)),
    )
    if not hb_models:
        raise RuntimeError("Dragonfly model produced no Honeybee models during export.")
    return hb_models[0]


def _build_dragonfly_gbxml_parameters(options: dict[str, Any], *, trace_3d_plus: bool = False) -> GBXMLParameters:
    params = GBXMLParameters.for_trace_3d_plus() if trace_3d_plus else GBXMLParameters()
    if "ip_units" in options:
        params.ip_units = bool(options["ip_units"])
    geo = params.geometry_format
    if "full_geometry" in options:
        geo.ignore_multipliers = not bool(options["full_geometry"])
    if "use_multiplier" in options:
        geo.ignore_multipliers = not bool(options["use_multiplier"])
    if "ignore_multipliers" in options:
        geo.ignore_multipliers = bool(options["ignore_multipliers"])
    if "exclude_plenums" in options:
        geo.exclude_plenums = bool(options["exclude_plenums"])
    elif "plenum" in options:
        geo.exclude_plenums = not bool(options["plenum"])
    if "ignore_ceiling_adjacencies" in options:
        geo.ignore_ceiling_adjacencies = bool(options["ignore_ceiling_adjacencies"])
    elif "no_ceil_adjacency" in options:
        geo.ignore_ceiling_adjacencies = bool(options["no_ceil_adjacency"])
    for key in (
        "include_shell_geometry",
        "include_space_boundaries",
        "triangulate_non_planar",
        "merge_method",
        "rect_geo_format",
        "explicit_holes",
        "exclude_roofs",
        "exclude_shades",
        "opening_simplification",
    ):
        if key in options and options[key] is not None:
            setattr(geo, key, options[key])
    if "triangulate_subfaces" in options:
        geo.triangulate_openings = bool(options["triangulate_subfaces"])
    if "triangulate_openings" in options:
        geo.triangulate_openings = bool(options["triangulate_openings"])
    if trace_3d_plus and options.get("detailed_windows"):
        geo.opening_simplification = "Rectangularized"

    name_fmt = params.name_format
    for key in (
        "interior_face_type",
        "ground_face_type",
        "reset_geometry_ids",
        "reset_resource_ids",
        "face_rename_format",
        "subface_rename_format",
    ):
        if key in options and options[key] is not None:
            setattr(name_fmt, key, options[key])

    ver_fmt = params.version_format
    for key in ("program_name", "program_version", "gbxml_schema_version"):
        if key in options and options[key] is not None:
            setattr(ver_fmt, key, options[key])

    return params


def _export_sdd_file(*, hb_model: Any, output_path: Path, options: dict[str, Any]) -> str:
    working = hb_model.duplicate()
    if options.get("geometry_names") or options.get("use_geometry_names"):
        working.reset_ids()
        for room in working.rooms:
            room.display_name = None
            for face in room.faces:
                face.display_name = None
                for ap in face.apertures:
                    ap.display_name = None
                for dr in face.doors:
                    dr.display_name = None
            room.rename_faces_by_attribute()
            room.rename_apertures_by_attribute()
            room.rename_doors_by_attribute()
        working.reset_ids()

    os_model = openstudio.model.Model()
    sim_par_data = options.get("simulation_par")
    if isinstance(sim_par_data, dict):
        sim_par = SimulationParameter.from_dict(sim_par_data)
        simulation_parameter_to_openstudio(sim_par, os_model)
    project_info_data = options.get("project_info")
    if isinstance(project_info_data, dict):
        from ladybug.projectinfo import ProjectInfo

        proj = ProjectInfo.from_dict(project_info_data)
        sim_par = SimulationParameter()
        sim_par.assign_from_project_info(proj, overwrite=True)
        simulation_parameter_to_openstudio(sim_par, os_model)

    os_model = model_to_openstudio(
        working,
        os_model,
        use_simple_window_constructions=bool(options.get("use_simple_window_constructions", True)),
        use_resource_names=bool(
            options.get("use_resource_names", options.get("resource_names", False))
        ),
    )
    translator = openstudio.sdd.SddForwardTranslator()
    translator.modelToSDD(os_model, str(output_path))
    if not output_path.is_file():
        raise RuntimeError(f"SddForwardTranslator did not produce output file: {output_path}")
    return output_path.read_text(encoding="utf-8")


def _perform_export(
    *,
    model: Any,
    model_domain: str,
    export_format: str,
    output_dir: Path,
    output_path: Path,
    identifier: str,
    options: dict[str, Any],
    garden_root_path: Path,
    gbas_report_path: Path | None = None,
) -> tuple[str | None, dict[str, Any]]:
    try:
        if export_format == DOE_INP_EXPORT_FORMAT:
            kwargs = _pick_kwargs(
                options,
                ("hvac_mapping", "exclude_interior_walls", "exclude_interior_ceilings", "equest_version"),
            )
            if isinstance(options.get("simulation_par"), dict):
                from honeybee_doe2.simulation import SimulationPar

                kwargs["simulation_par"] = SimulationPar.from_dict(options["simulation_par"])
            writer = honeybee_model_to_inp if model_domain == "honeybee" else dragonfly_model_to_inp
            text = writer(model, **kwargs)
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        if export_format == DESIGNBUILDER_DSBXML_EXPORT_FORMAT:
            kwargs = _pick_kwargs(options, ("xml_template", "sub_face_type", "program_name"))
            writer = honeybee_model_to_dsbxml if model_domain == "honeybee" else dragonfly_model_to_dsbxml
            text = writer(model, **kwargs)
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        if export_format == FORMAT_GBXML:
            if model_domain == "dragonfly":
                gbxml_par = _build_dragonfly_gbxml_parameters(options, trace_3d_plus=False)
                text = dragonfly_model_to_gbxml(
                    model,
                    gbxml_parameters=gbxml_par,
                    room_order=options.get("room_order"),
                )
            else:
                direct_keys = {
                    "ip_units",
                    "include_shell_geometry",
                    "include_space_boundaries",
                    "rect_geo_format",
                    "explicit_holes",
                    "total_ventilation",
                    "face_rename_format",
                    "subface_rename_format",
                    "triangulate_non_planar",
                }
                if options.get("use_openstudio") is False or any(k in options for k in direct_keys):
                    kwargs = _pick_kwargs(
                        options,
                        (
                            "ip_units",
                            "include_shell_geometry",
                            "include_space_boundaries",
                            "interior_face_type",
                            "ground_face_type",
                            "face_rename_format",
                            "subface_rename_format",
                            "reset_geometry_ids",
                            "reset_resource_ids",
                            "triangulate_subfaces",
                            "triangulate_non_planar",
                            "rect_geo_format",
                            "explicit_holes",
                            "total_ventilation",
                            "program_name",
                            "program_version",
                            "gbxml_schema_version",
                        ),
                    )
                    text = model.to_gbxml(**kwargs)
                else:
                    kwargs = _pick_kwargs(
                        options,
                        (
                            "triangulate_non_planar_orphaned",
                            "triangulate_subfaces",
                            "full_geometry",
                            "interior_face_type",
                            "ground_face_type",
                            "reset_geometry_ids",
                            "reset_resource_ids",
                            "program_name",
                            "program_version",
                            "gbxml_schema_version",
                            "print_progress",
                        ),
                    )
                    text = honeybee_openstudio_model_to_gbxml(model, **kwargs)
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        if export_format == FORMAT_TRACE_GBXML:
            if model_domain == "dragonfly":
                gbxml_par = _build_dragonfly_gbxml_parameters(options, trace_3d_plus=True)
                text = dragonfly_model_to_gbxml(model, gbxml_parameters=gbxml_par)
            else:
                detailed_windows = bool(options.get("detailed_windows", False))
                single_window = bool(options.get("single_window", not detailed_windows))
                preprocessed = _preprocess_model_for_trace_3dplus(
                    model.duplicate(),
                    single_window=single_window,
                    rect_sub_distance=options.get("rect_sub_distance", "0.15m"),
                    frame_merge_distance=options.get("frame_merge_distance", "0.2m"),
                )
                text = preprocessed.to_gbxml(
                    ip_units=True,
                    program_name=options.get("program_name"),
                    program_version=options.get("program_version"),
                )
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        hb_model = model if model_domain == "honeybee" else _dragonfly_to_honeybee(model, options)

        if export_format == FORMAT_GBAS_DWG:
            overwrite = bool(options.get("overwrite", True))
            report_path = (
                gbas_report_path
                if gbas_report_path is not None
                else _resolve_gbas_report_path(
                    options,
                    garden_root_path=garden_root_path,
                    output_dir=output_dir,
                    output_path=output_path,
                    identifier=identifier,
                )
            )
            written_path, gbas_report = honeybee_model_to_gbas_dwg(
                hb_model,
                output_path,
                report_path=report_path,
                overwrite=overwrite,
            )
            report_dict = gbas_report if isinstance(gbas_report, dict) else {}
            self_check = report_dict.get("self_check")
            self_check_dict = self_check if isinstance(self_check, dict) else {}
            extra_summary: dict[str, Any] = {
                "size_bytes": Path(written_path).stat().st_size,
                "gbas_status": report_dict.get("status"),
                "gbas_format": report_dict.get("format"),
                "source_units": report_dict.get("source_units"),
                "drawing_units": report_dict.get("drawing_units"),
                "counts": report_dict.get("counts", {}),
                "self_check_status": self_check_dict.get("status"),
                "self_check_passed": self_check_dict.get("passed"),
                "self_check_warnings": self_check_dict.get("warnings", []),
                "automatic_repairs": self_check_dict.get("automatic_repairs", {}),
            }
            if report_path is not None:
                extra_summary["report_path"] = to_posix_relative(report_path, garden_root_path)
                extra_summary["report_absolute_path"] = str(report_path)
            return None, extra_summary

        if export_format == FORMAT_OSM:
            kwargs = _pick_kwargs(
                options,
                ("use_geometry_names", "use_resource_names", "openstudio_version", "print_progress"),
            )
            text = honeybee_model_to_osm(hb_model, **kwargs)
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        if export_format == FORMAT_IDF:
            if options.get("direct_to_idf"):
                kwargs = _pick_kwargs(
                    options,
                    ("use_ideal_air_equivalent", "patch_missing_adjacencies", "timestep"),
                )
                text = hb_model.to_idf(**kwargs)
            else:
                kwargs = _pick_kwargs(
                    options,
                    ("use_geometry_names", "use_resource_names", "print_progress"),
                )
                text = honeybee_openstudio_model_to_idf(hb_model, **kwargs)
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        if export_format == FORMAT_EPJSON:
            kwargs = _pick_kwargs(
                options,
                ("use_geometry_names", "use_resource_names", "print_progress"),
            )
            text = honeybee_model_to_epjson(hb_model, **kwargs)
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        if export_format == FORMAT_SDD:
            text = _export_sdd_file(hb_model=hb_model, output_path=output_path, options=options)
            return text, {}

        if export_format == FORMAT_RAD:
            kwargs = _pick_kwargs(options, ("blk", "minimal"))
            model_str, modifier_str = honeybee_model_to_rad(hb_model, **kwargs)
            text = (
                f"{modifier_str.rstrip()}\n\n{model_str.lstrip()}"
                if modifier_str.strip()
                else model_str
            )
            return _write_export_file(output_path=output_path, export_format=export_format, text=text), {}

        if export_format == FORMAT_RAD_FOLDER:
            kwargs = _pick_kwargs(options, ("minimal", "grids", "views", "full_match"))
            honeybee_model_to_rad_folder(hb_model, folder=str(output_path), **kwargs)
            generated = sorted(
                to_posix_relative(p, garden_root_path)
                for p in output_path.rglob("*")
                if p.is_file()
            )
            return None, {"generated_files": generated, "generated_file_count": len(generated)}

        if export_format == FORMAT_HBPKL:
            kwargs = _pick_kwargs(options, ("included_prop", "triangulate_sub_faces"))
            written = Path(hb_model.to_hbpkl(name=identifier, folder=str(output_dir), **kwargs))
            return None, {"size_bytes": written.stat().st_size}

        if export_format == FORMAT_STL:
            written = Path(hb_model.to_stl(name=identifier, folder=str(output_dir)))
            return written.read_text(encoding="utf-8"), {}

        raise ValueError(f"Unsupported model export path: {model_domain} {export_format}.")
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(
            f"Failed to export {model_domain} model as {export_format}: {exc}"
        ) from exc


def _write_export_file(*, output_path: Path, export_format: str, text: str) -> str:
    if export_format == DESIGNBUILDER_DSBXML_EXPORT_FORMAT:
        encoded = text.encode("iso-8859-15", errors="ignore")
        output_path.write_bytes(encoded)
        return encoded.decode("iso-8859-15")
    output_path.write_text(text, encoding="utf-8", newline="\n")
    return text


__all__ = [
    "DESIGNBUILDER_DSBXML_EXPORT_FORMAT",
    "DOE_INP_EXPORT_FORMAT",
    "FORMAT_EPJSON",
    "FORMAT_GBAS_DWG",
    "FORMAT_GBXML",
    "FORMAT_HBPKL",
    "FORMAT_IDF",
    "FORMAT_OSM",
    "FORMAT_RAD",
    "FORMAT_RAD_FOLDER",
    "FORMAT_SDD",
    "FORMAT_STL",
    "FORMAT_TRACE_GBXML",
    "MODEL_EXPORT_ARTIFACT_DIR",
    "export_model_file",
]
