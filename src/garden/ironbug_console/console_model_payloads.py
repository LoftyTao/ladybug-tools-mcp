"""Ironbug model-root payload loading for Python Console file runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from garden.ironbug_console.console_payloads import (
    console_hvac_payload_to_specification,
    _has_hvac_collection,
    _source_class,
)


_MODEL_ROOT_KEYS = (
    "EnergyManagementSystem",
    "ElectricLoadCenter",
)
_EMPTY_HVAC_PAYLOAD = {
    "AirLoops": [],
    "PlantLoops": [],
    "VariableRefrigerantFlows": [],
}


@dataclass(frozen=True)
class ConsoleModelSpecification:
    """Normalized root collections for an Ironbug Console model save."""

    hvac_specification: dict[str, Any]
    root_payloads: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "root_payloads", tuple(self.root_payloads))


def load_console_model_specification(path: str | Path) -> ConsoleModelSpecification:
    """Load an Ironbug HVAC JSON or full Garden `.ibjson` model payload."""

    candidate = Path(path)
    if not candidate.exists():
        raise FileNotFoundError(f"Ironbug model JSON file does not exist: {candidate}")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Ironbug model JSON root must be a JSON object.")
    return console_model_payload_to_specification(payload)


def console_model_payload_to_specification(
    payload: Mapping[str, Any],
) -> ConsoleModelSpecification:
    """Normalize C# SaveHVAC and IB_Model-style roots."""

    source_class = _source_class(payload)
    if source_class == "IB_Model":
        hvac_payload = payload.get("HVACSystem")
        if isinstance(hvac_payload, Mapping):
            hvac_specification = console_hvac_payload_to_specification(hvac_payload)
        else:
            hvac_specification = console_hvac_payload_to_specification(
                _EMPTY_HVAC_PAYLOAD
            )
        return ConsoleModelSpecification(
            hvac_specification=hvac_specification,
            root_payloads=tuple(
                root
                for key in _MODEL_ROOT_KEYS
                if isinstance(root := payload.get(key), Mapping)
            ),
        )
    if source_class == "IB_HVACSystem" or _has_hvac_collection(payload):
        return ConsoleModelSpecification(
            hvac_specification=console_hvac_payload_to_specification(payload),
        )
    raise ValueError(
        "Ironbug model JSON root must be IB_HVACSystem, IB_Model, or contain "
        "AirLoops/PlantLoops/VariableRefrigerantFlows."
    )
