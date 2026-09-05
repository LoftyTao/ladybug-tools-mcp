"""Resumable Honeybee exterior opening and shade stage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from honeybee.room import Room
from honeybee.typing import valid_string

from garden.honeybee_core.creation import _load_target_model, _save_receipt
from garden.honeybee_core.geometry import (
    validate_face_sub_faces,
    validate_honeybee_shade,
)
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import save_honeybee_model
from garden.honeybee_core.targets import (
    make_honeybee_object_target,
    normalize_honeybee_object_target,
)
from garden.operations.core import _payload_path
from garden.paths import validate_portable_file_name
from ladybug_tools_mcp.contracts.report import make_report


def _checkpoint_target(
    *, checkpoint_id: str, garden_id: str, model_target: dict[str, Any]
) -> dict[str, Any]:
    validate_portable_file_name(checkpoint_id, label="Checkpoint identifier")
    try:
        valid_string(checkpoint_id, "checkpoint_id")
    except (AssertionError, TypeError) as exc:
        raise ValueError(str(exc)) from exc
    if len(checkpoint_id) > 64:
        raise ValueError("checkpoint_id must be 64 characters or fewer.")
    path = (Path("workflows") / "honeybee" / f"{checkpoint_id}.json").as_posix()
    return {
        "target_type": "honeybee_workflow_checkpoint",
        "garden_id": garden_id,
        "workflow_type": "honeybee_opening_shade_stage",
        "checkpoint_id": checkpoint_id,
        "model_identifier": str(model_target["model_identifier"]),
        "model_target": model_target,
        "path": path,
    }


def _load_checkpoint(
    root: Path,
    target: dict[str, Any],
    *,
    garden_id: str,
    model_target: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(target, dict) or not isinstance(target.get("checkpoint_id"), str):
        raise ValueError("checkpoint_target must be a typed checkpoint target.")
    expected = _checkpoint_target(
        checkpoint_id=target["checkpoint_id"],
        garden_id=garden_id,
        model_target=model_target,
    )
    if target != expected:
        raise ValueError(
            "checkpoint_target does not match the current Garden and Honeybee model."
        )
    path = _payload_path(root, expected["path"])
    if not path.is_file():
        raise ValueError(f"Workflow checkpoint not found: {expected['path']}.")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != "1"
        or data.get("checkpoint_target") != expected
    ):
        raise ValueError("Unsupported or mismatched Honeybee opening/shade checkpoint.")
    return expected, data


def _object_target(
    *,
    garden_id: str,
    model_identifier: str,
    object_type: str,
    object_identifier: str,
    room_identifier: str,
    face_identifier: str,
    aperture_identifier: str | None = None,
) -> dict[str, Any]:
    parent = {"room_identifier": room_identifier, "face_identifier": face_identifier}
    if aperture_identifier:
        parent["aperture_identifier"] = aperture_identifier
    return make_honeybee_object_target(
        garden_id=garden_id,
        model_identifier=model_identifier,
        object_type=object_type,
        object_identifier=object_identifier,
        parent=parent,
    )


def _validation_state(model: Any) -> dict[str, Any]:
    issues = model.check_all(raise_exception=False, detailed=True)
    return {
        "is_valid": not issues,
        "issue_count": len(issues),
        "issue_codes": sorted(
            {
                issue["code"]
                for issue in issues
                if isinstance(issue, dict) and isinstance(issue.get("code"), str)
            }
        ),
    }


def _result(
    *,
    garden_id: str,
    model_target: dict[str, Any],
    checkpoint_target: dict[str, Any] | None,
    created_targets: list[dict[str, Any]],
    reused_targets: list[dict[str, Any]],
    missing_requirements: list[str],
    validation_state: dict[str, Any],
    next_action: str,
    persistence_status: str,
    message: str,
) -> dict[str, Any]:
    receipt = _save_receipt(
        garden_id=garden_id,
        model_target=model_target,
        persisted_path=(checkpoint_target or {}).get("path", ""),
        operation="complete_honeybee_opening_shade_stage",
        object_target=checkpoint_target,
        change_details={
            "created_targets": created_targets,
            "reused_targets": reused_targets,
            "missing_requirements": missing_requirements,
            "checkpoint_target": checkpoint_target,
        },
        warnings=missing_requirements,
    )
    receipt["status"] = persistence_status
    return {
        "target": checkpoint_target,
        "checkpoint_target": checkpoint_target,
        "model_target": model_target,
        "created_targets": created_targets,
        "reused_targets": reused_targets,
        "missing_requirements": missing_requirements,
        "validation_state": validation_state,
        "next_action": next_action,
        "summary_view": {
            "created_count": len(created_targets),
            "reused_count": len(reused_targets),
            "missing_requirement_count": len(missing_requirements),
            "validation_state": validation_state,
            "next_action": next_action,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok" if not missing_requirements else "blocked",
            message=message,
            warnings=missing_requirements,
            details={"next_action": next_action, "validation_state": validation_state},
        ),
    }


def complete_honeybee_opening_shade_stage(
    *,
    garden_root: str,
    checkpoint_id: str | None = None,
    checkpoint_target: dict[str, Any] | None = None,
    room_target: dict[str, Any] | None = None,
    face_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    aperture_ratio: float | None = None,
    shade_depth: float | None = None,
    shade_count: int | None = None,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Create or resume one Room -> exterior Face -> Aperture -> Shade stage."""
    if checkpoint_target is not None and model_target is None:
        checkpoint_model_target = checkpoint_target.get("model_target")
        if not isinstance(checkpoint_model_target, dict):
            raise ValueError("checkpoint_target requires model_target.")
        model_target = checkpoint_model_target
    root, manifest, model_target, model = _load_target_model(garden_root, model_target)
    model_identifier = str(model_target["model_identifier"])

    checkpoint_data: dict[str, Any] | None = None
    if checkpoint_target is not None:
        checkpoint_target, checkpoint_data = _load_checkpoint(
            root,
            checkpoint_target,
            garden_id=manifest.garden_id,
            model_target=model_target,
        )
        checkpoint_id = str(checkpoint_target["checkpoint_id"])
        room_target = checkpoint_data["room_target"]
        face_target = checkpoint_data["face_target"]
        parameters = checkpoint_data["parameters"]
        aperture_ratio = parameters["aperture_ratio"]
        shade_depth = parameters["shade_depth"]
        shade_count = parameters["shade_count"]
        tolerance = parameters["tolerance"]
    elif checkpoint_id is None:
        raise ValueError("checkpoint_id is required when checkpoint_target is omitted.")

    checkpoint_target = _checkpoint_target(
        checkpoint_id=str(checkpoint_id),
        garden_id=manifest.garden_id,
        model_target=model_target,
    )
    if checkpoint_data is None and _payload_path(
        root, checkpoint_target["path"]
    ).is_file():
        requirement = (
            f"checkpoint_id {checkpoint_id!r} already exists; pass its original "
            "checkpoint_target to resume or choose a new checkpoint_id."
        )
        return _result(
            garden_id=manifest.garden_id,
            model_target=model_target,
            checkpoint_target=None,
            created_targets=[],
            reused_targets=[],
            missing_requirements=[requirement],
            validation_state=_validation_state(model),
            next_action="resolve_conflict",
            persistence_status="no_change",
            message="Opening and shade checkpoint identifier is already in use.",
        )
    if room_target is None or face_target is None:
        raise ValueError("room_target and face_target are required for a new stage.")
    room_target = normalize_honeybee_object_target(room_target)
    face_target = normalize_honeybee_object_target(face_target)
    for target, object_type in ((room_target, "room"), (face_target, "face")):
        if target["object_type"] != object_type:
            raise ValueError(
                f"{object_type}_target must identify a Honeybee {object_type}."
            )
        if (
            target.get("garden_id") != manifest.garden_id
            or target.get("model_identifier") != model_identifier
        ):
            raise ValueError(
                f"{object_type}_target belongs to another Garden or model."
            )
    if aperture_ratio is None or not 0 < aperture_ratio < 1:
        raise ValueError("aperture_ratio must be greater than 0 and less than 1.")
    if shade_depth is None or shade_depth <= 0:
        raise ValueError("shade_depth must be a positive number.")
    if (
        isinstance(shade_count, bool)
        or not isinstance(shade_count, int)
        or shade_count <= 0
    ):
        raise ValueError("shade_count must be a positive integer.")
    if tolerance <= 0:
        raise ValueError("tolerance must be a positive number.")

    room = find_object(model, room_target)
    face = find_object(model, face_target)
    if not isinstance(room, Room) or face not in room.faces:
        raise ValueError("face_target must identify a Face on room_target.")
    if face.type.name != "Wall" or face.boundary_condition.name != "Outdoors":
        raise ValueError("face_target must identify an exterior Wall Face.")

    created_targets: list[dict[str, Any]] = []
    reused_targets: list[dict[str, Any]] = []
    missing_requirements: list[str] = []
    existing_apertures = sorted(face.apertures, key=lambda item: item.identifier)
    if existing_apertures:
        if abs(face.aperture_ratio - aperture_ratio) > tolerance:
            missing_requirements.append(
                "Existing Apertures conflict with aperture_ratio; resolve them "
                "explicitly."
            )
        apertures = existing_apertures
    else:
        face.apertures_by_ratio(aperture_ratio, tolerance=tolerance, rect_split=True)
        apertures = sorted(face.apertures, key=lambda item: item.identifier)
        if not apertures:
            raise ValueError("No Apertures can be created on the selected exterior Face.")
        for index, aperture in enumerate(apertures, start=1):
            aperture.identifier = (
                f"{checkpoint_id}_aperture"
                if len(apertures) == 1
                else f"{checkpoint_id}_aperture_{index}"
            )

    if checkpoint_data is not None:
        checkpoint_ids = {
            target["object_identifier"]
            for target in checkpoint_data["aperture_targets"]
        }
        if {aperture.identifier for aperture in apertures} != checkpoint_ids:
            missing_requirements.append(
                "Current Apertures differ from the checkpoint; resolve the Face "
                "explicitly."
            )

    aperture_targets = [
        _object_target(
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
            object_type="aperture",
            object_identifier=aperture.identifier,
            room_identifier=room.identifier,
            face_identifier=face.identifier,
        )
        for aperture in apertures
    ]
    (reused_targets if existing_apertures else created_targets).extend(aperture_targets)

    shade_targets: list[dict[str, Any]] = []
    if not missing_requirements:
        for aperture_index, aperture in enumerate(apertures, start=1):
            existing_shades = list(aperture.outdoor_shades)
            existing_by_id = {shade.identifier: shade for shade in existing_shades}
            expected_ids = [
                f"{checkpoint_id}_shade_{aperture_index}_{shade_index}"
                for shade_index in range(1, shade_count + 1)
            ]
            stage_ids = {
                identifier
                for identifier in existing_by_id
                if identifier.startswith(f"{checkpoint_id}_shade_{aperture_index}_")
            }
            if not stage_ids.issubset(expected_ids):
                missing_requirements.append(
                    f"Aperture {aperture.identifier} has conflicting stage Shades."
                )
                break

            generated = aperture.louvers_by_count(
                shade_count,
                shade_depth,
                tolerance=tolerance,
                base_name="stage_candidate",
            )
            aperture.remove_outdoor_shades()
            aperture.add_outdoor_shades(existing_shades)
            if len(generated) != shade_count:
                missing_requirements.append(
                    f"Aperture {aperture.identifier} can create only "
                    f"{len(generated)} of {shade_count} requested Shades."
                )
                break
            for shade, identifier in zip(generated, expected_ids, strict=True):
                shade.identifier = identifier
            reused_existing_ids: set[str] = set()

            for shade in generated:
                existing = existing_by_id.get(shade.identifier)
                if existing is None:
                    existing = next(
                        (
                            candidate
                            for candidate in existing_shades
                            if candidate.identifier not in reused_existing_ids
                            and candidate.geometry.is_geometrically_equivalent(
                                shade.geometry, tolerance
                            )
                        ),
                        None,
                    )
                target_identifier = (
                    existing.identifier if existing is not None else shade.identifier
                )
                target = _object_target(
                    garden_id=manifest.garden_id,
                    model_identifier=model_identifier,
                    object_type="shade",
                    object_identifier=target_identifier,
                    room_identifier=room.identifier,
                    face_identifier=face.identifier,
                    aperture_identifier=aperture.identifier,
                )
                shade_targets.append(target)
                if existing is not None:
                    if (
                        existing.identifier == shade.identifier
                        and not existing.geometry.is_geometrically_equivalent(
                            shade.geometry, tolerance
                        )
                    ):
                        missing_requirements.append(
                            f"Existing Shade {shade.identifier} conflicts with "
                            "parameters."
                        )
                        break
                    reused_existing_ids.add(existing.identifier)
                    reused_targets.append(target)
                else:
                    validate_honeybee_shade(shade)
                    aperture.add_outdoor_shade(shade)
                    created_targets.append(target)
            if missing_requirements:
                break

    if missing_requirements:
        return _result(
            garden_id=manifest.garden_id,
            model_target=model_target,
            checkpoint_target=checkpoint_target if checkpoint_data else None,
            created_targets=[],
            reused_targets=reused_targets,
            missing_requirements=missing_requirements,
            validation_state=_validation_state(model),
            next_action="resolve_conflict",
            persistence_status="no_change",
            message="Opening and shade stage is blocked by existing model conflicts.",
        )

    validate_face_sub_faces(face)
    validation_state = _validation_state(model)
    checkpoint = {
        "schema_version": "1",
        "checkpoint_target": checkpoint_target,
        "room_target": room_target,
        "face_target": face_target,
        "aperture_targets": aperture_targets,
        "shade_targets": shade_targets,
        "parameters": {
            "aperture_ratio": aperture_ratio,
            "shade_depth": shade_depth,
            "shade_count": shade_count,
            "tolerance": tolerance,
        },
        "validation_state": validation_state,
        "next_action": (
            "stage_complete" if validation_state["is_valid"] else "review_validation"
        ),
    }
    checkpoint_content = (
        json.dumps(checkpoint, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    checkpoint_path = _payload_path(root, checkpoint_target["path"])
    unchanged = checkpoint_path.is_file() and not created_targets
    if unchanged:
        with checkpoint_path.open("rb") as handle:
            unchanged = handle.read() == checkpoint_content
    if unchanged:
        return _result(
            garden_id=manifest.garden_id,
            model_target=model_target,
            checkpoint_target=checkpoint_target,
            created_targets=[],
            reused_targets=reused_targets,
            missing_requirements=[],
            validation_state=validation_state,
            next_action=checkpoint["next_action"],
            persistence_status="no_change",
            message="Opening and shade stage is already complete.",
        )

    updated_target, _ = save_honeybee_model(
        root,
        manifest,
        model,
        name=model_identifier,
        set_base=manifest.base_honeybee_model == model_target,
        staged_writes={checkpoint_target["path"]: checkpoint_content},
    )
    return _result(
        garden_id=manifest.garden_id,
        model_target=updated_target,
        checkpoint_target=checkpoint_target,
        created_targets=created_targets,
        reused_targets=reused_targets,
        missing_requirements=[],
        validation_state=validation_state,
        next_action=checkpoint["next_action"],
        persistence_status="persisted",
        message="Opening and shade stage completed.",
    )
