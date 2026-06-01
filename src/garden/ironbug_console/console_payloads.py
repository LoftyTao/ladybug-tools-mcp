"""Ironbug HVAC JSON payload loading for Python Console file runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


_HVAC_COLLECTION_KEYS = (
    "AirLoops",
    "PlantLoops",
    "VariableRefrigerantFlows",
)


def load_console_hvac_specification(path: str | Path) -> dict[str, Any]:
    """Load a C# Console-style HVAC JSON or Garden `.ibjson` payload."""

    candidate = Path(path)
    if not candidate.exists():
        raise FileNotFoundError(f"Ironbug HVAC JSON file does not exist: {candidate}")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Ironbug HVAC JSON root must be a JSON object.")
    return console_hvac_payload_to_specification(payload)


def console_hvac_payload_to_specification(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the DetailedHVAC-shaped top-level HVAC collections."""

    source_class = _source_class(payload)
    if source_class == "IB_Model":
        hvac_payload = payload.get("HVACSystem")
        if not isinstance(hvac_payload, Mapping):
            raise ValueError("IB_Model payload has no HVACSystem object.")
    elif source_class == "IB_HVACSystem" or _has_hvac_collection(payload):
        hvac_payload = payload
    else:
        raise ValueError(
            "Ironbug HVAC JSON root must be IB_HVACSystem, IB_Model, or contain "
            "AirLoops/PlantLoops/VariableRefrigerantFlows."
        )

    return {
        key: list(hvac_payload.get(key) or [])
        for key in _HVAC_COLLECTION_KEYS
    }


def _source_class(value: Mapping[str, Any]) -> str | None:
    source_type = value.get("$type") or value.get("type")
    if not isinstance(source_type, str) or not source_type:
        return None
    return source_type.split(",", 1)[0].rsplit(".", 1)[-1]


def _has_hvac_collection(value: Mapping[str, Any]) -> bool:
    return any(key in value for key in _HVAC_COLLECTION_KEYS)
