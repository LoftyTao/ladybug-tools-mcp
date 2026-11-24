"""Ironbug Garden target helpers."""

from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError

IRONBUG_MODEL_TARGET_TYPE = "ironbug_model"

_TModel = TypeVar("_TModel", bound=BaseModel)


class IronbugModelTarget(BaseModel):
    """Pydantic schema for an Ironbug system target."""

    model_config = ConfigDict(extra="allow")

    target_type: Literal["ironbug_model"]
    id: StrictStr = Field(min_length=1)


class NormalizedIronbugModelTarget(IronbugModelTarget):
    """Pydantic schema for a persisted Ironbug system target with Garden path."""

    path: StrictStr = Field(min_length=1)


def _validate_dict_model(model_cls: type[_TModel], value: Any, error_message: str) -> _TModel:
    if not isinstance(value, dict):
        raise ValueError(error_message)
    try:
        return model_cls.model_validate(value)
    except ValidationError as exc:
        raise ValueError(error_message) from exc


def is_ironbug_model_target(value: Any) -> bool:
    """Return whether a value is an Ironbug system target."""
    if not isinstance(value, dict):
        return False
    try:
        IronbugModelTarget.model_validate(value)
    except ValidationError:
        return False
    return True


def make_ironbug_model_target(
    *,
    garden_id: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build an Ironbug system target."""
    parsed = NormalizedIronbugModelTarget(
        target_type=IRONBUG_MODEL_TARGET_TYPE,
        id=identifier,
        path=path,
    )
    return {
        "target_type": IRONBUG_MODEL_TARGET_TYPE,
        "id": parsed.id,
        "identifier": parsed.id,
        "garden_id": garden_id,
        "domain": "ironbug",
        "path": parsed.path,
        "root_type": "IB_HVACSystem",
    }


def normalize_ironbug_model_target(value: Any) -> dict[str, Any]:
    """Validate and normalize an Ironbug system target."""
    _validate_dict_model(
        IronbugModelTarget,
        value,
        "ironbug_model_target must be a dict with target_type 'ironbug_model' "
        "and a non-empty id.",
    )
    parsed = _validate_dict_model(
        NormalizedIronbugModelTarget,
        value,
        "ironbug_model_target requires a Garden-relative path.",
    )
    target = parsed.model_dump()
    target["domain"] = "ironbug"
    target["identifier"] = parsed.id
    target["root_type"] = "IB_HVACSystem"
    return target
