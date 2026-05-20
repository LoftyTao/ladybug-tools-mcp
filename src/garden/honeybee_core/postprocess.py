"""Honeybee model post-processing helpers for create/edit/remove/operate flows."""

from __future__ import annotations

from collections import Counter
from typing import Any

from honeybee.model import Model
from honeybee.room import Room

from garden.honeybee_core.relate import (
    _adjacency_counts,
    _clone_single_missing_subfaces,
    _empty_patch_summary,
)

POSTPROCESS_STRATEGIES = {
    "none",
    "suggest_validate",
    "auto_validate",
    "auto_relate_existing_geometry",
    "auto_relate_intersect_clone_single",
}


def default_postprocess_strategy(
    *,
    operation: str,
    target: dict[str, Any] | None = None,
    object_type: str | None = None,
    updated_fields: list[str] | None = None,
) -> str:
    """Return the default post-processing strategy for a Honeybee action."""
    object_type = object_type or _object_type_from_target(target)
    updated_fields = updated_fields or []

    if operation in {
        "move_object",
        "rotate_object",
        "scale_object",
        "mirror_object",
    }:
        if _is_model_target(target):
            return "auto_validate"
        if object_type in {"room", "face", "aperture", "door"}:
            return "auto_relate_intersect_clone_single"
        return "suggest_validate"

    if operation.startswith("create_honeybee_"):
        if object_type in {"room", "face", "aperture", "door"}:
            return "auto_relate_intersect_clone_single"
        if object_type == "shade" or operation == "create_honeybee_shades_by_parameters":
            return "suggest_validate"
        return "none"

    if operation.startswith("edit_honeybee_"):
        if operation == "edit_honeybee_model":
            return "auto_validate"
        if object_type in {"face", "aperture", "door"} and _changes_geometry_or_relation(
            updated_fields,
        ):
            return "auto_relate_intersect_clone_single"
        return "suggest_validate"

    if operation.startswith("remove_honeybee_"):
        if object_type in {"room", "face", "aperture", "door"}:
            return "auto_relate_intersect_clone_single"
        return "suggest_validate"

    return "none"


def apply_honeybee_postprocess(
    *,
    model: Model,
    garden_id: str,
    model_identifier: str,
    operation: str,
    target: dict[str, Any] | None = None,
    object_type: str | None = None,
    updated_fields: list[str] | None = None,
    strategy: str | None = None,
) -> tuple[Model, dict[str, Any]]:
    """Apply a post-processing strategy and return the model to persist."""
    selected = strategy or default_postprocess_strategy(
        operation=operation,
        target=target,
        object_type=object_type,
        updated_fields=updated_fields,
    )
    if selected not in POSTPROCESS_STRATEGIES:
        raise ValueError(
            "postprocess_strategy must be one of "
            f"{', '.join(sorted(POSTPROCESS_STRATEGIES))}."
        )

    if selected == "none":
        return model, _summary(selected, "skipped")
    if selected == "suggest_validate":
        warning = (
            "Postprocess strategy suggest_validate did not modify relationships. "
            "Run validate_honeybee_model if this change should be checked."
        )
        return model, _summary(selected, "suggested", warnings=[warning])
    if selected == "auto_validate":
        validation = _validation_summary(model)
        warnings = _validation_warnings(validation)
        return model, _summary(
            selected,
            "completed",
            warnings=warnings,
            validation=validation,
        )

    return _apply_auto_relate(
        model=model,
        garden_id=garden_id,
        model_identifier=model_identifier,
        strategy=selected,
    )


def attach_postprocess_result(
    response: dict[str, Any],
    postprocess: dict[str, Any],
) -> dict[str, Any]:
    """Attach post-process summary and warnings to a public tool response."""
    if not postprocess or postprocess.get("strategy") == "none":
        return response

    warnings = list(postprocess.get("warnings", []))
    response.setdefault("summary_view", {})["postprocess"] = postprocess

    receipt = response.get("persistence_receipt")
    if isinstance(receipt, dict):
        receipt["warnings"] = [*receipt.get("warnings", []), *warnings]
        receipt.setdefault("change_summary", {})["postprocess"] = postprocess

    report = response.get("report")
    if isinstance(report, dict):
        report["warnings"] = [*report.get("warnings", []), *warnings]
        report.setdefault("details", {})["postprocess"] = postprocess

    return response


def _apply_auto_relate(
    *,
    model: Model,
    garden_id: str,
    model_identifier: str,
    strategy: str,
) -> tuple[Model, dict[str, Any]]:
    working_model = model.duplicate()
    before_counts = _adjacency_counts(working_model)
    before_face_count = len(working_model.faces)
    tol = working_model.tolerance
    angle_tol = working_model.angle_tolerance
    intersect = strategy == "auto_relate_intersect_clone_single"

    try:
        if intersect:
            Room.intersect_adjacency(working_model.rooms, tol, angle_tol)
        patch = _clone_single_missing_subfaces(
            working_model,
            garden_id=garden_id,
            model_identifier=model_identifier,
            tolerance=tol,
            angle_tolerance=angle_tol,
        ) if strategy == "auto_relate_intersect_clone_single" else _empty_patch_summary()
        working_model.solve_adjacency(
            merge_coplanar=False,
            intersect=False,
            overwrite=False,
            remove_mismatched_sub_faces=False,
            tolerance=tol,
            angle_tolerance=angle_tol,
        )
    except Exception as exc:  # pragma: no cover - SDK-specific diagnostics vary
        message = (
            "Automatic Honeybee postprocess failed; the original edit was preserved. "
            "Run relate_honeybee_model or validate_honeybee_model to inspect the model. "
            f"{exc}"
        )
        return model, _summary(
            strategy,
            "warning",
            warnings=[message],
            error=str(exc),
            adjacency_counts_before=before_counts,
            face_count_before=before_face_count,
        )

    after_counts = _adjacency_counts(working_model)
    validation = _validation_summary(working_model)
    warnings = []
    if intersect:
        warnings.append(
            "Automatic relate used intersect before solving adjacency; Room Face "
            "geometry may have changed."
        )
    warnings.extend(patch["warnings"])
    warnings.extend(_validation_warnings(validation))

    return working_model, _summary(
        strategy,
        "completed",
        warnings=warnings,
        face_count_before=before_face_count,
        face_count_after=len(working_model.faces),
        adjacency_counts_before=before_counts,
        adjacency_counts_after=after_counts,
        subface_patch=patch,
        validation=validation,
    )


def _validation_summary(model: Model) -> dict[str, Any]:
    try:
        issues = model.check_all(raise_exception=False, detailed=True)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        return {
            "status": "failed",
            "is_valid": False,
            "issue_count": 0,
            "issue_codes": [],
            "issue_counts_by_code": {},
            "error": str(exc),
        }

    issue_codes = [
        issue["code"]
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("code"), str)
    ]
    return {
        "status": "ok",
        "is_valid": len(issues) == 0,
        "issue_count": len(issues),
        "issue_codes": sorted(set(issue_codes)),
        "issue_counts_by_code": dict(sorted(Counter(issue_codes).items())),
    }


def _validation_warnings(validation: dict[str, Any]) -> list[str]:
    if validation.get("status") == "failed":
        return [f"Automatic validation failed. {validation.get('error', '')}".strip()]
    if validation.get("is_valid") is False:
        return [
            "Automatic validation found "
            f"{validation.get('issue_count', 0)} Honeybee issue(s)."
        ]
    return []


def _summary(
    strategy: str,
    status: str,
    *,
    warnings: list[str] | None = None,
    **details: Any,
) -> dict[str, Any]:
    return {
        "strategy": strategy,
        "status": status,
        "warnings": warnings or [],
        **details,
    }


def _object_type_from_target(target: dict[str, Any] | None) -> str | None:
    if not target:
        return None
    if _is_model_target(target):
        return "model"
    value = target.get("object_type")
    return str(value) if value is not None else None


def _is_model_target(target: dict[str, Any] | None) -> bool:
    return (
        isinstance(target, dict)
        and target.get("target_type") == "honeybee_model"
        and target.get("domain") == "honeybee"
    )


def _changes_geometry_or_relation(updated_fields: list[str]) -> bool:
    relation_fields = {
        "geometry",
        "type",
        "boundary_condition",
        "is_operable",
        "is_glass",
    }
    return bool(relation_fields.intersection(updated_fields))
