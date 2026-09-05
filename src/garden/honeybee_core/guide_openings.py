"""Honeybee aperture creation from Ladybug Geometry guide surfaces."""

from __future__ import annotations

import math
from typing import Any

from honeybee.aperture import Aperture
from honeybee.boundarycondition import Outdoors
from honeybee.face import Face

from garden.honeybee_core.creation import (
    _load_target_model,
    _model_object_identifiers,
    _resolve_object_target_for_model,
    _save_changed_model,
    _save_receipt,
)
from garden.honeybee_core.geometry import (
    face3d_from_dict,
    validate_face_sub_faces,
    validate_honeybee_aperture,
)
from garden.honeybee_core.locate import ensure_face_host, find_object
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.targets import make_honeybee_object_target, object_summary
from ladybug_tools_mcp.contracts.report import make_report


def create_honeybee_apertures_by_guide_surface(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    guide_surfaces: list[dict[str, Any]],
    model_target: dict[str, Any] | None = None,
    tolerance: float = 0.01,
    identifier_prefix: str | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create apertures from Face3D guide surfaces on a Honeybee Face."""
    if not isinstance(guide_surfaces, list) or not guide_surfaces:
        raise ValueError("guide_surfaces must contain at least one Face3D dictionary.")
    if tolerance <= 0:
        raise ValueError("tolerance must be greater than 0.")

    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    host_target = _resolve_object_target_for_model(host_target)
    host = ensure_face_host(find_object(model, host_target))
    if not isinstance(host.boundary_condition, Outdoors):
        raise ValueError(
            "host_target must identify a Honeybee Face with an Outdoors "
            "boundary condition."
        )
    validate_face_sub_faces(host)

    angle_tolerance = model.angle_tolerance
    angle_tolerance_radians = math.radians(angle_tolerance)
    known_subfaces = [*host.apertures, *host.doors]
    model_identifiers = _model_object_identifiers(model)
    prefix = (identifier_prefix or f"{host.identifier}_GuideAperture").strip()
    if not prefix:
        raise ValueError("identifier_prefix must not be empty.")

    created: list[Aperture] = []
    created_targets: list[dict[str, Any]] = []
    reused_targets: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    parent = {**host_target.get("parent", {}), "face_identifier": host.identifier}

    for index, guide_surface in enumerate(guide_surfaces):
        try:
            guide_geometry = face3d_from_dict(guide_surface)
            guide_aperture = Aperture(
                f"{prefix}_{index + 1}",
                guide_geometry,
            )
            validate_honeybee_aperture(guide_aperture)
        except Exception as exc:
            skipped.append(
                _skip_detail(index, "invalid_geometry", f"Could not read guide surface: {exc}")
            )
            continue

        if not host.geometry.plane.is_coplanar_tolerance(
            guide_geometry.plane,
            tolerance,
            angle_tolerance_radians,
        ):
            normal_angle = guide_geometry.normal.angle(host.geometry.normal)
            parallel_angle = min(normal_angle, math.pi - normal_angle)
            reason = (
                "non_coplanar"
                if parallel_angle > angle_tolerance_radians
                else "outside_tolerance"
            )
            message = (
                "Guide surface is not coplanar with the host Face within the "
                f"{tolerance} geometry tolerance."
            )
            skipped.append(_skip_detail(index, reason, message))
            continue

        try:
            test_host = host.duplicate()
            test_aperture = Aperture(
                "_guide_surface_test",
                guide_geometry,
            )
            before_count = len(test_host.apertures)
            test_host.project_and_add_sub_face(
                test_aperture,
                angle_tolerance=angle_tolerance,
            )
        except Exception as exc:
            skipped.append(
                _skip_detail(
                    index,
                    "projection_failed",
                    f"Honeybee SDK could not project the guide surface: {exc}.",
                )
            )
            continue

        if len(test_host.apertures) != before_count + 1:
            skipped.append(
                _skip_detail(
                    index,
                    "projection_failed",
                    "Honeybee SDK could not project the guide surface onto the host Face.",
                )
            )
            continue

        projected_geometry = test_aperture.geometry
        if not test_host.geometry.is_sub_face(
            projected_geometry,
            tolerance,
            angle_tolerance_radians,
        ):
            skipped.append(
                _skip_detail(
                    index,
                    "outside_host_face",
                    "Projected guide surface is not fully inside the host Face.",
                )
            )
            continue

        equivalent = next(
            (
                subface
                for subface in known_subfaces
                if isinstance(subface, Aperture)
                and projected_geometry.is_geometrically_equivalent(
                    subface.geometry,
                    tolerance,
                )
            ),
            None,
        )
        if equivalent is not None:
            reused_targets.append(
                make_honeybee_object_target(
                    garden_id=manifest.garden_id,
                    model_identifier=str(model_target["model_identifier"]),
                    object_type="aperture",
                    object_identifier=equivalent.identifier,
                    parent=parent,
                )
            )
            continue

        if any(
            projected_geometry.is_overlapping(subface.geometry, tolerance)
            for subface in known_subfaces
        ):
            skipped.append(
                _skip_detail(
                    index,
                    "overlaps_existing_subface",
                    "Projected guide surface overlaps an existing Aperture, Door, "
                    "or another guide surface.",
                )
            )
            continue

        identifier = _guide_identifier(prefix, index + 1, len(guide_surfaces))
        if identifier in model_identifiers:
            skipped.append(
                _skip_detail(
                    index,
                    "duplicate_identifier",
                    f"Honeybee object identifier already exists: {identifier}.",
                )
            )
            continue

        try:
            validate_face_sub_faces(test_host)
        except Exception as exc:
            skipped.append(
                _skip_detail(
                    index,
                    "invalid_subface",
                    f"Projected guide surface failed Honeybee validation: {exc}",
                )
            )
            continue

        aperture = Aperture(identifier, guide_geometry)
        host.project_and_add_sub_face(
            aperture,
            angle_tolerance=angle_tolerance,
        )
        validate_honeybee_aperture(aperture)
        validate_face_sub_faces(host)
        created.append(aperture)
        known_subfaces.append(aperture)
        model_identifiers.add(identifier)
        target = make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=str(model_target["model_identifier"]),
            object_type="aperture",
            object_identifier=identifier,
            parent=parent,
        )
        created_targets.append(target)

    object_summaries = [
        object_summary(target, aperture.to_dict())
        for target, aperture in zip(created_targets, created, strict=True)
    ]
    if created:
        model, postprocess = apply_honeybee_postprocess(
            model=model,
            garden_id=manifest.garden_id,
            model_identifier=str(model_target["model_identifier"]),
            operation="create_honeybee_apertures_by_guide_surface",
            target=host_target,
            object_type="aperture",
            strategy=postprocess_strategy,
        )
        updated_target, persisted_path = _save_changed_model(
            garden_root,
            manifest,
            model_target,
            model,
        )
        receipt = _save_receipt(
            garden_id=manifest.garden_id,
            model_target=updated_target,
            persisted_path=persisted_path,
            operation="create_honeybee_apertures_by_guide_surface",
            object_target=host_target,
            change_details={
                "created_targets": created_targets,
                "reused_targets": reused_targets,
                "skipped": skipped,
            },
        )
    else:
        postprocess = {}
        updated_target = model_target
        receipt = _save_receipt(
            garden_id=manifest.garden_id,
            model_target=model_target,
            persisted_path=str(model_target.get("path", "")),
            operation="create_honeybee_apertures_by_guide_surface",
            object_target=host_target,
            change_details={
                "created_targets": [],
                "reused_targets": reused_targets,
                "skipped": skipped,
            },
            status="no_change",
        )

    targets = [*created_targets, *reused_targets]
    response = {
        "target": targets[0] if targets else None,
        "aperture_target": targets[0] if targets else None,
        "targets": targets,
        "created_targets": created_targets,
        "reused_targets": reused_targets,
        "skipped": skipped,
        "model_target": updated_target,
        "summary_view": {
            "host_target": host_target,
            "guide_count": len(guide_surfaces),
            "created_count": len(created_targets),
            "reused_count": len(reused_targets),
            "skipped_count": len(skipped),
            "skipped": skipped,
            "objects": object_summaries,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                f"Created {len(created_targets)} Honeybee aperture(s) from guide "
                f"surfaces on Face: {host.identifier}."
            ),
            warnings=[item["message"] for item in skipped],
        ),
    }
    if not created:
        response["runtime_status"] = "no_change"
    return attach_postprocess_result(response, postprocess)


def _guide_identifier(prefix: str, index: int, total: int) -> str:
    base = prefix if total == 1 else f"{prefix}_{index}"
    return base[:100]


def _skip_detail(index: int, reason: str, message: str) -> dict[str, Any]:
    return {"guide_surface_index": index, "reason": reason, "message": message}
