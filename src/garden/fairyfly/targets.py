"""Typed target helpers for Fairyfly THERM artifacts and results."""

from __future__ import annotations

from typing import Any

FAIRYFLY_THERM_RECIPE = "therm"
FAIRYFLY_THMZ_TARGET_TYPE = "fairyfly_thmz"
FAIRYFLY_THERM_RUN_TARGET_TYPE = "fairyfly_therm_run"
FAIRYFLY_THERM_RESULT_TARGET_TYPE = "fairyfly_therm_result"
FAIRYFLY_THERM_DOMAIN = "fairyfly"


def make_fairyfly_thmz_target(
    garden_id: str,
    run_id: str,
    path: str,
) -> dict[str, Any]:
    """Build a Fairyfly THERM THMZ artifact target."""
    return {
        "target_type": FAIRYFLY_THMZ_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": FAIRYFLY_THERM_DOMAIN,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_id": run_id,
        "path": path,
    }


def make_fairyfly_therm_run_target(garden_id: str, run_id: str) -> dict[str, Any]:
    """Build a Fairyfly THERM run target."""
    return {
        "target_type": FAIRYFLY_THERM_RUN_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": FAIRYFLY_THERM_DOMAIN,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_id": run_id,
    }


def make_fairyfly_therm_result_target(
    garden_id: str,
    run_id: str,
    data_type: str,
    path: str,
) -> dict[str, Any]:
    """Build a Fairyfly THERM result target."""
    return {
        "target_type": FAIRYFLY_THERM_RESULT_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": FAIRYFLY_THERM_DOMAIN,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_id": run_id,
        "data_type": data_type,
        "path": path,
    }


def make_fairyfly_u_factor_result_target(
    garden_id: str,
    run_id: str,
    path: str,
) -> dict[str, Any]:
    """Build the U-Factor specialization of a Fairyfly THERM result target."""
    return make_fairyfly_therm_result_target(
        garden_id=garden_id,
        run_id=run_id,
        data_type="u_factors",
        path=path,
    )


def normalize_fairyfly_therm_run_target(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a Fairyfly THERM run target."""
    if not isinstance(value, dict):
        raise ValueError("Fairyfly THERM run target must be a dictionary.")
    if value.get("target_type") != FAIRYFLY_THERM_RUN_TARGET_TYPE:
        raise ValueError("run_target must have target_type 'fairyfly_therm_run'.")
    if value.get("domain") != FAIRYFLY_THERM_DOMAIN:
        raise ValueError("run_target must reference domain 'fairyfly'.")
    if value.get("recipe") != FAIRYFLY_THERM_RECIPE:
        raise ValueError("run_target must reference recipe 'therm'.")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_target requires run_id.")
    return dict(value)
