"""Shared PassiveStrategyParameters, strategy normalization, and comfort polygon helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable

from ladybug.datacollection import (
    BaseCollection,
    DailyCollection,
    HourlyContinuousCollection,
    MonthlyCollection,
)
from ladybug.datatype.temperature import Temperature
from ladybug.psychchart import PsychrometricChart
from ladybug.psychrometrics import humid_ratio_from_db_rh
from ladybug_comfort.chart.polygonpmv import PolygonPMV
from ladybug_comfort.chart.polygonutci import PolygonUTCI
from ladybug_geometry.geometry2d import LineSegment2D, Point2D, Polyline2D

STRATEGY_DISPLAY_NAMES: dict[str, str] = {
    "evaporative_cooling": "Evaporative Cooling",
    "night_flush": "Mass + Night Vent",
    "fan_use": "Occupant Use of Fans",
    "internal_heat": "Capture Internal Heat",
    "passive_solar": "Passive Solar Heating",
    "shade_line": "Shade Line",
}

_STRATEGY_ALIASES: dict[str, str] = {
    "evaporative_cooling": "evaporative_cooling",
    "evaporative cooling": "evaporative_cooling",
    "evap": "evaporative_cooling",
    "evaporative": "evaporative_cooling",
    "night_flush": "night_flush",
    "night flush": "night_flush",
    "mass_night_vent": "night_flush",
    "mass + night vent": "night_flush",
    "thermal mass + night vent": "night_flush",
    "thermal_mass": "night_flush",
    "thermal mass": "night_flush",
    "night_ventilation": "night_flush",
    "night ventilation": "night_flush",
    "night_vent": "night_flush",
    "fan_use": "fan_use",
    "fan use": "fan_use",
    "occupant use of fans": "fan_use",
    "fan": "fan_use",
    "fans": "fan_use",
    "air_movement": "fan_use",
    "natural_ventilation": "fan_use",
    "natural ventilation": "fan_use",
    "internal_heat": "internal_heat",
    "capture internal heat": "internal_heat",
    "internal heat": "internal_heat",
    "internal_heat_gain": "internal_heat",
    "internal_gains": "internal_heat",
    "passive_solar": "passive_solar",
    "passive solar heating": "passive_solar",
    "passive solar": "passive_solar",
    "passive_solar_heating": "passive_solar",
    "solar_heating": "passive_solar",
    "shade_line": "shade_line",
    "shade line": "shade_line",
    "shading_line": "shade_line",
}

UTCI_STRESS_ZONES: tuple[tuple[str, str, str], ...] = (
    ("very_strong_cold", "very_strong_cold_polygon", "Very Strong Cold Stress"),
    ("strong_cold", "strong_cold_polygon", "Strong Cold Stress"),
    ("moderate_cold", "moderate_cold_polygon", "Moderate Cold Stress"),
    ("moderate_heat", "moderate_heat_polygon", "Moderate Heat Stress"),
    ("strong_heat", "strong_heat_polygon", "Strong Heat Stress"),
    ("very_strong_heat", "very_strong_heat_polygon", "Very Strong Heat Stress"),
)

_DEFAULT_STRATEGIES_NO_SOLAR: tuple[str, ...] = (
    "evaporative_cooling",
    "night_flush",
    "fan_use",
    "internal_heat",
)
_DEFAULT_STRATEGIES_WITH_SOLAR: tuple[str, ...] = (
    "evaporative_cooling",
    "night_flush",
    "fan_use",
    "internal_heat",
    "passive_solar",
)


def _check_numeric_range(
    value: Any,
    *,
    field_name: str,
    minimum: float,
    maximum: float,
    integer_only: bool = False,
) -> float | int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number.")
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if not isfinite(num):
        raise ValueError(f"{field_name} must be finite.")
    if num < minimum or num > maximum:
        raise ValueError(
            f"{field_name} must be between {minimum} and {maximum}; got {num}."
        )
    if integer_only:
        if num != int(num):
            raise ValueError(f"{field_name} must be an integer; got {num}.")
        return int(num)
    return num


@dataclass(frozen=True)
class PassiveStrategyParameters:
    """Parameters matching Ladybug's ``LB Passive Strategy Parameters`` component."""

    day_above_comfort: float = 12.0
    night_below_comfort: float = 3.0
    fan_air_speed: float = 1.0
    balance_temperature: float = 12.8
    solar_heat_capacity: float = 50.0
    time_constant: int = 8

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "day_above_comfort",
            float(
                _check_numeric_range(
                    self.day_above_comfort,
                    field_name="day_above_comfort",
                    minimum=0.0,
                    maximum=30.0,
                )
            ),
        )
        object.__setattr__(
            self,
            "night_below_comfort",
            float(
                _check_numeric_range(
                    self.night_below_comfort,
                    field_name="night_below_comfort",
                    minimum=0.0,
                    maximum=15.0,
                )
            ),
        )
        object.__setattr__(
            self,
            "fan_air_speed",
            float(
                _check_numeric_range(
                    self.fan_air_speed,
                    field_name="fan_air_speed",
                    minimum=0.1,
                    maximum=10.0,
                )
            ),
        )
        object.__setattr__(
            self,
            "balance_temperature",
            float(
                _check_numeric_range(
                    self.balance_temperature,
                    field_name="balance_temperature",
                    minimum=5.0,
                    maximum=20.0,
                )
            ),
        )
        object.__setattr__(
            self,
            "solar_heat_capacity",
            float(
                _check_numeric_range(
                    self.solar_heat_capacity,
                    field_name="solar_heat_capacity",
                    minimum=1.0,
                    maximum=1000.0,
                )
            ),
        )
        object.__setattr__(
            self,
            "time_constant",
            int(
                _check_numeric_range(
                    self.time_constant,
                    field_name="time_constant",
                    minimum=1,
                    maximum=48,
                    integer_only=True,
                )
            ),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PassiveStrategyParameters:
        """Construct ``PassiveStrategyParameters`` from a dict supporting aliases."""
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("passive_strategy_parameters must be a dictionary.")

        def _pick(keys: tuple[str, ...], default: float | int) -> Any:
            for key in keys:
                if key in data and data[key] is not None:
                    return data[key]
            return default

        return cls(
            day_above_comfort=_pick(
                (
                    "day_above_comfort",
                    "day_above_comf",
                    "night_flush_temp_above_comfort",
                    "temperature_above_comfort",
                ),
                12.0,
            ),
            night_below_comfort=_pick(
                ("night_below_comfort", "night_below_comf"),
                3.0,
            ),
            fan_air_speed=_pick(("fan_air_speed",), 1.0),
            balance_temperature=_pick(
                (
                    "balance_temperature",
                    "balance_temp",
                    "internal_heat_balance_temperature",
                ),
                12.8,
            ),
            solar_heat_capacity=_pick(
                ("solar_heat_capacity", "solar_heat_cap"),
                50.0,
            ),
            time_constant=_pick(("time_constant",), 8),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize parameters to a Ladybug-style dictionary."""
        return {
            "type": "PassiveStrategyParameters",
            "day_above_comfort": self.day_above_comfort,
            "night_below_comfort": self.night_below_comfort,
            "fan_air_speed": self.fan_air_speed,
            "balance_temperature": self.balance_temperature,
            "solar_heat_capacity": self.solar_heat_capacity,
            "time_constant": self.time_constant,
        }


def normalize_passive_strategies(
    strategies: list[str] | tuple[str, ...] | dict[str, Any] | str | None,
    *,
    has_solar: bool = False,
    strict: bool = True,
) -> list[str]:
    """Normalize passive strategy names or flags into canonical keys preserving order."""
    if strategies is None:
        return list(
            _DEFAULT_STRATEGIES_WITH_SOLAR if has_solar else _DEFAULT_STRATEGIES_NO_SOLAR
        )
    if isinstance(strategies, dict):
        raw_items: list[str] = [str(k) for k, v in strategies.items() if v]
    elif isinstance(strategies, str):
        raw_items = [strategies]
    elif isinstance(strategies, (list, tuple, set)):
        raw_items = [str(item) for item in strategies]
    else:
        raise ValueError("strategies must be a list of strategy names or a boolean mapping.")

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        key = " ".join(raw.strip().lower().split())
        canon = _STRATEGY_ALIASES.get(key) or _STRATEGY_ALIASES.get(key.replace(" ", "_"))
        if canon is None:
            if strict:
                raise ValueError(
                    f"Unknown passive strategy {raw!r}. Valid strategies: "
                    "evaporative_cooling, night_flush, fan_use, internal_heat, "
                    "passive_solar, shade_line."
                )
            continue
        if canon not in seen:
            seen.add(canon)
            normalized.append(canon)
    return normalized


def summarize_polygon_numeric_input(
    value: Any,
    *,
    load_collection_fn: Callable[[dict[str, Any], str], Any],
    field_name: str,
) -> list[float] | None:
    """Coerce a scalar, short list, or DataCollection target into a safe polygon input list.

    ``PolygonPMV`` and ``PolygonUTCI`` solve one comfort polygon per array item.
    Long sequences or full-year DataCollections (> 12 entries) are collapsed to
    their mean to prevent solving 8,760 redundant polygons.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number, list of numbers, or DataCollection target.")
    if isinstance(value, (int, float)):
        num = float(value)
        if not isfinite(num):
            raise ValueError(f"{field_name} must be finite.")
        return [num]
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return None
        nums: list[float] = []
        for idx, item in enumerate(value):
            if isinstance(item, bool):
                raise ValueError(f"{field_name}[{idx}] must be numeric.")
            try:
                num = float(item)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name}[{idx}] must be numeric.") from exc
            if not isfinite(num):
                raise ValueError(f"{field_name}[{idx}] must be finite.")
            nums.append(num)
        if len(nums) > 24:
            return [sum(nums) / len(nums)]
        return nums
    if isinstance(value, dict):
        col = load_collection_fn(value, field_name)
        vals = [float(v) for v in col.values]
        if not vals:
            raise ValueError(f"{field_name} must contain at least one value.")
        if len(vals) <= 12:
            return vals
        return [float(col.average)]
    raise ValueError(f"{field_name} must be a number, list of numbers, or DataCollection target.")


def _chart_time_multiplier(temperature: Any) -> float:
    if isinstance(temperature, MonthlyCollection):
        return 30.0 * 24.0
    if isinstance(temperature, DailyCollection):
        return 24.0
    if isinstance(temperature, BaseCollection):
        timestep = getattr(getattr(temperature.header, "analysis_period", None), "timestep", 1)
        return 1.0 / float(timestep or 1)
    return 1.0


def _is_annual_hourly_compatible(chart: PsychrometricChart, col: Any) -> bool:
    if not isinstance(col, HourlyContinuousCollection):
        return False
    if not col.header.analysis_period.is_annual:
        return False
    chart_col = (
        chart.temperature
        if isinstance(chart.temperature, BaseCollection)
        else chart.relative_humidity
    )
    if not isinstance(chart_col, HourlyContinuousCollection):
        # PolygonPMV._check_hourly accepts HourlyContinuousCollection or HourlyDiscontinuousCollection
        from ladybug.datacollection import HourlyDiscontinuousCollection

        if not isinstance(chart_col, HourlyDiscontinuousCollection):
            return False
    return col.header.analysis_period.timestep == chart_col.header.analysis_period.timestep


def _safe_evaluate_polygon(
    ppmv: PolygonPMV,
    segments: tuple[Any, ...] | list[Any],
    tolerance: float,
) -> list[int]:
    try:
        return [int(v) for v in ppmv.evaluate_polygon(segments, tolerance=tolerance)]
    except (AssertionError, IndexError, TypeError, ValueError):
        for fallback_tol in (1e-3, 1e-4, 0.05):
            if fallback_tol == tolerance:
                continue
            try:
                return [int(v) for v in ppmv.evaluate_polygon(segments, tolerance=fallback_tol)]
            except (AssertionError, IndexError, TypeError, ValueError):
                continue
        return [0] * len(ppmv.psychrometric_chart.data_points)


def _compute_shade_line(
    chart: PsychrometricChart,
    ppmv: PolygonPMV,
    balance_temperature: float,
) -> tuple[Any, ...] | None:
    if balance_temperature < 5.0 or ppmv.is_comfort_too_cold:
        return None
    segs = ppmv.shade_line(balance_temperature=balance_temperature)
    if segs:
        return tuple(segs) if isinstance(segs, (list, tuple)) else (segs,)
    bal_disp = (
        balance_temperature
        if not chart.use_ip
        else Temperature().to_unit([balance_temperature], "F", "C")[0]
    )
    bal_x = chart.t_x_value(bal_disp)
    comf_poly = ppmv.merged_comfort_polygon
    if bal_x < chart.base_point.x or comf_poly[0][0].x < bal_x:
        return None
    sat_hr = humid_ratio_from_db_rh(balance_temperature, 100, chart.average_pressure)
    sat_y = chart.hr_y_value(sat_hr)
    top_y = min(comf_poly[0][0].y, sat_y)
    if top_y <= chart.base_point.y:
        top_y = comf_poly[0][0].y
    if top_y <= chart.base_point.y:
        return None
    return (
        LineSegment2D.from_end_points(
            Point2D(bal_x, chart.base_point.y),
            Point2D(bal_x, top_y),
        ),
    )


def evaluate_pmv_passive_strategies(
    *,
    chart: PsychrometricChart,
    ppmv: PolygonPMV,
    params: PassiveStrategyParameters,
    strategies: list[str],
    outdoor_temperature: Any = None,
    incident_irradiance: Any = None,
    passive_solar_balance_temperature: float | None = None,
    passive_solar_max_delta: float = 10.0,
    shade_balance_temperature: float | None = None,
    merge_polygons: bool = True,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Evaluate PMV comfort polygon and passive strategy polygons/statistics."""
    base_vals = [int(v) for v in ppmv.merged_comfort_values]
    n_points = len(base_vals)
    time_mult = _chart_time_multiplier(chart.temperature)
    baseline_comfort_pct = (sum(base_vals) / n_points * 100.0) if n_points else 0.0

    polygon_geometries: dict[str, Any] = {}
    masks: dict[str, list[int]] = {"comfort": base_vals}
    polygon_names: list[str] = []
    polygon_comfort: list[float] = []

    if not merge_polygons and ppmv.polygon_count > 1:
        comfort_polys = list(ppmv.comfort_polygons)
        polygon_geometries["comfort_polygons"] = comfort_polys
        for idx, c_vals in enumerate(ppmv.comfort_values):
            c_list = [int(v) for v in c_vals]
            polygon_names.append(f"Comfort {idx + 1}")
            polygon_comfort.append((sum(c_list) / len(c_list) * 100.0) if c_list else 0.0)
    else:
        polygon_geometries["comfort_polygons"] = [ppmv.merged_comfort_polygon]
        polygon_names.append("Comfort")
        polygon_comfort.append(baseline_comfort_pct)

    strategies_added: list[str] = []
    strategies_skipped: list[str] = []
    strategy_percents: dict[str, float] = {}
    strategy_details: dict[str, dict[str, Any]] = {}
    comfort_strategy_masks: list[list[int]] = [base_vals]

    out_col = outdoor_temperature if outdoor_temperature is not None else chart.temperature

    for strat in strategies:
        display_name = STRATEGY_DISPLAY_NAMES.get(strat, strat)
        if strat == "evaporative_cooling":
            segs = ppmv.evaporative_cooling_polygon()
            if not segs:
                strategies_skipped.append(strat)
                continue
            vals = _safe_evaluate_polygon(ppmv, segs, tolerance)
            eval_mode = "polygon"
        elif strat == "night_flush":
            segs = ppmv.night_flush_polygon(temperature_above_comfort=params.day_above_comfort)
            if not segs:
                strategies_skipped.append(strat)
                continue
            if _is_annual_hourly_compatible(chart, out_col):
                vals = [
                    int(v)
                    for v in ppmv.evaluate_night_flush_polygon(
                        segs,
                        out_col,
                        night_below_comfort=params.night_below_comfort,
                        time_constant=params.time_constant,
                        tolerance=tolerance,
                    )
                ]
                eval_mode = "night_flush_annual"
            else:
                vals = _safe_evaluate_polygon(ppmv, segs, tolerance)
                eval_mode = "polygon_only_non_annual"
        elif strat == "fan_use":
            segs = ppmv.fan_use_polygon(air_speed=params.fan_air_speed)
            if not segs:
                strategies_skipped.append(strat)
                continue
            vals = _safe_evaluate_polygon(ppmv, segs, tolerance)
            eval_mode = "polygon"
        elif strat == "internal_heat":
            segs = ppmv.internal_heat_polygon(balance_temperature=params.balance_temperature)
            if not segs:
                strategies_skipped.append(strat)
                continue
            vals = _safe_evaluate_polygon(ppmv, segs, tolerance)
            eval_mode = "polygon"
        elif strat == "passive_solar":
            bal_t = (
                float(passive_solar_balance_temperature)
                if passive_solar_balance_temperature is not None
                else (params.balance_temperature if "internal_heat" in strategies else None)
            )
            if incident_irradiance is not None and _is_annual_hourly_compatible(
                chart, incident_irradiance
            ):
                raw_vals, max_delta = ppmv.evaluate_passive_solar(
                    incident_irradiance,
                    solar_heat_capacity=params.solar_heat_capacity,
                    time_constant=params.time_constant,
                    balance_temperature=bal_t,
                )
                vals = [int(v) for v in raw_vals]
                segs = ppmv.passive_solar_polygon(max_delta, balance_temperature=bal_t)
                eval_mode = "passive_solar_annual"
            else:
                max_delta = float(passive_solar_max_delta)
                segs = ppmv.passive_solar_polygon(max_delta, balance_temperature=bal_t)
                if not segs:
                    strategies_skipped.append(strat)
                    continue
                vals = _safe_evaluate_polygon(ppmv, segs, tolerance)
                eval_mode = (
                    "polygon_only_non_annual"
                    if incident_irradiance is not None
                    else "polygon_only_no_solar"
                )
            if not segs:
                strategies_skipped.append(strat)
                continue
        elif strat == "shade_line":
            shade_bal = float(
                shade_balance_temperature
                if shade_balance_temperature is not None
                else params.balance_temperature
            )
            segs = _compute_shade_line(chart, ppmv, shade_bal)
            if not segs:
                strategies_skipped.append(strat)
                continue
            polygon_geometries["shade_line"] = segs
            strategies_added.append("shade_line")
            strategy_details["shade_line"] = {
                "display_name": display_name,
                "balance_temperature": shade_bal,
                "evaluation_mode": "overlay_line",
            }
            continue
        else:
            strategies_skipped.append(strat)
            continue

        polygon_geometries[strat] = tuple(segs)
        masks[strat] = vals
        comfort_strategy_masks.append(vals)
        strategies_added.append(strat)

        pct = (sum(vals) / n_points * 100.0) if n_points else 0.0
        add_hrs_count = sum(1 for b, v in zip(base_vals, vals) if v and not b)
        add_pct = (add_hrs_count / n_points * 100.0) if n_points else 0.0
        strategy_percents[strat] = pct
        polygon_names.append(display_name)
        polygon_comfort.append(pct)
        detail: dict[str, Any] = {
            "display_name": display_name,
            "percent": pct,
            "hours": float(sum(vals)) * time_mult,
            "additional_percent": add_pct,
            "additional_hours": float(add_hrs_count) * time_mult,
            "evaluation_mode": eval_mode,
        }
        if strat == "passive_solar":
            detail["max_temperature_delta"] = float(max_delta)
            detail["balance_temperature"] = bal_t
        strategy_details[strat] = detail

    total_vals = (
        [1 if any(row) else 0 for row in zip(*comfort_strategy_masks)]
        if n_points
        else []
    )
    masks["total_comfort"] = total_vals
    total_comfort_pct = (sum(total_vals) / n_points * 100.0) if n_points else 0.0
    passive_gain_pct = total_comfort_pct - baseline_comfort_pct

    statistics = {
        "model": "pmv",
        "passive_strategy_parameters": params.to_dict(),
        "polygon_count": ppmv.polygon_count,
        "merge_polygons": bool(merge_polygons),
        "baseline_comfort_percent": baseline_comfort_pct,
        "comfort_percent": baseline_comfort_pct,
        "total_comfort_percent": total_comfort_pct,
        "passive_gain_percent": passive_gain_pct,
        "baseline_comfort_hours": float(sum(base_vals)) * time_mult,
        "total_comfort_hours": float(sum(total_vals)) * time_mult,
        "passive_gain_hours": float(sum(total_vals) - sum(base_vals)) * time_mult,
        "strategies_requested": list(strategies),
        "strategies_added": strategies_added,
        "strategies_skipped": strategies_skipped,
        "strategy_percents": strategy_percents,
        "strategy_details": strategy_details,
        "polygon_names": polygon_names,
        "polygon_comfort": polygon_comfort,
    }
    return {
        "polygon_geometries": polygon_geometries,
        "masks": masks,
        "statistics": statistics,
    }


def evaluate_utci_polygons(
    putci: PolygonUTCI,
    *,
    merge_polygons: bool = True,
    stress_polygons: bool | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Evaluate UTCI comfort polygon(s) and all six thermal stress polygons."""
    base_vals = [int(v) for v in putci.merged_comfort_values]
    n_points = len(base_vals)
    baseline_comfort_pct = (sum(base_vals) / n_points * 100.0) if n_points else 0.0

    if not merge_polygons and putci.polygon_count > 1:
        comfort_polys = list(putci.comfort_polygons)
        polygon_names = [f"Comfort {idx + 1}" for idx in range(len(comfort_polys))]
        polygon_comfort = [
            (sum(vals) / len(vals) * 100.0) if vals else 0.0
            for vals in putci.comfort_values
        ]
    else:
        comfort_polys = [putci.merged_comfort_polygon]
        polygon_names = ["Comfort"]
        polygon_comfort = [baseline_comfort_pct]

    if stress_polygons is True:
        requested_stress = [key for key, _, _ in UTCI_STRESS_ZONES]
    elif isinstance(stress_polygons, (list, tuple, set)):
        requested_stress = [str(item).strip().lower() for item in stress_polygons]
    else:
        requested_stress = []

    stress_geometries: dict[str, tuple[Any, ...]] = {}
    stress_percents: dict[str, float] = {}
    for key, attr, display_name in UTCI_STRESS_ZONES:
        segs = getattr(putci, attr, None)
        if not segs:
            continue
        eval_res = putci.evaluate_inside(segs[0], segs[2], display_name)
        pct = (
            float(eval_res.average) * 100.0
            if hasattr(eval_res, "average")
            else float(eval_res) * 100.0
        )
        stress_percents[key] = pct
        if key in requested_stress:
            stress_geometries[key] = tuple(segs)

    added_stress = [key for key, _, _ in UTCI_STRESS_ZONES if key in stress_geometries]
    statistics = {
        "model": "utci",
        "polygon_count": putci.polygon_count,
        "merge_polygons": bool(merge_polygons),
        "comfort_percent": baseline_comfort_pct,
        "baseline_comfort_percent": baseline_comfort_pct,
        "stress_polygons": added_stress,
        "stress_percents": stress_percents,
        "polygon_names": polygon_names,
        "polygon_comfort": polygon_comfort,
    }
    return {
        "comfort_polygons": comfort_polys,
        "stress_geometries": stress_geometries,
        "statistics": statistics,
    }


__all__ = [
    "PassiveStrategyParameters",
    "STRATEGY_DISPLAY_NAMES",
    "UTCI_STRESS_ZONES",
    "evaluate_pmv_passive_strategies",
    "evaluate_utci_polygons",
    "normalize_passive_strategies",
    "summarize_polygon_numeric_input",
]
