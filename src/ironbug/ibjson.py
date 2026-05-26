"""ibjson IO helpers for Ironbug-Core models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ironbug import hvac
from ironbug.hvac import IB_Model


IBJSON_EXTENSION = ".ibjson"
IBJSON_ROOT_TYPE = "IB_Model"


def _coerce_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.suffix != IBJSON_EXTENSION:
        raise ValueError(
            f"ibjson files must use the {IBJSON_EXTENSION!r} extension: {candidate}"
        )
    return candidate


def _load_json_object(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("ibjson root must be a JSON object with root type 'IB_Model'")
    root_type = value.get("type")
    if root_type is None:
        raise ValueError("ibjson root type is required and must be 'IB_Model'")
    if root_type != IBJSON_ROOT_TYPE:
        raise ValueError(f"ibjson root type must be {IBJSON_ROOT_TYPE!r}, got {root_type!r}")
    return value


def _validate_model_root(model: IB_Model) -> IB_Model:
    if not isinstance(model, IB_Model):
        raise TypeError(f"ibjson root model must be an {IBJSON_ROOT_TYPE}")
    return model


def model_from_ibjson_string(text: str) -> IB_Model:
    """Parse an ibjson string into an ``IB_Model``."""

    data = _load_json_object(text)
    try:
        return IB_Model.model_validate(data)
    except ValidationError as exc:
        if not _known_source_polymorphism_error(exc):
            raise
        return _construct_source_object(data)


def _known_source_polymorphism_error(exc: ValidationError) -> bool:
    errors = exc.errors()
    if not errors:
        return False
    for error in errors:
        if error.get("type") != "literal_error":
            return False
        value = error.get("input")
        if not isinstance(value, str) or not hasattr(hvac, value):
            return False
    return True


def _construct_source_object(value: Any) -> Any:
    if isinstance(value, list):
        return [_construct_source_object(item) for item in value]
    if not isinstance(value, dict):
        return value
    hydrated = {key: _construct_source_object(item) for key, item in value.items()}
    source_type = hydrated.get("type")
    if not isinstance(source_type, str) or not hasattr(hvac, source_type):
        return hydrated
    if "DisplayName" in hydrated and "display_name" not in hydrated:
        hydrated["display_name"] = hydrated.pop("DisplayName")
    cls = getattr(hvac, source_type)
    return cls.model_construct(**hydrated)


def model_to_ibjson_string(model: IB_Model, *, indent: int | None = 2) -> str:
    """Serialize an ``IB_Model`` to an ibjson string."""

    model = _validate_model_root(model)
    return model.model_dump_json(by_alias=True, exclude_none=True, indent=indent)


def model_from_ibjson(path: str | Path) -> IB_Model:
    """Read an ``.ibjson`` file into an ``IB_Model``."""

    candidate = _coerce_path(path)
    return model_from_ibjson_string(candidate.read_text(encoding="utf-8"))


def model_to_ibjson(model: IB_Model, path: str | Path, *, indent: int = 2) -> Path:
    """Write an ``IB_Model`` to an ``.ibjson`` file and return the path."""

    candidate = _coerce_path(path)
    candidate.write_text(model_to_ibjson_string(model, indent=indent), encoding="utf-8")
    return candidate
