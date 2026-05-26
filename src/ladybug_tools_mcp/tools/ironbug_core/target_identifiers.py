"""Helpers for Ironbug tool parameters that bind by model object identifier."""

from __future__ import annotations

from typing import Any


def target_identifier(target: dict[str, Any] | str, *, parameter_name: str) -> str:
    """Return the identifier carried by a Garden target or an explicit name."""

    if isinstance(target, str):
        if target:
            return target
        raise ValueError(f"{parameter_name} requires a non-empty identifier.")
    identifier = target.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"{parameter_name} requires a target identifier.")
    return identifier
