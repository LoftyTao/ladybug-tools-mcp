"""Plant heat rejection writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_cooling_tower_variable_speed(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_tower = model.getCoolingTowerVariableSpeedByName(name)
    if optional_tower.is_initialized():
        tower = optional_tower.get()
    else:
        tower = openstudio.model.CoolingTowerVariableSpeed(model)
        tower.setName(name)
    _set_if_present(tower.setModelType, node, "ModelType", cast=str)
    _set_if_present(
        tower.setDesignInletAirWetBulbTemperature,
        node,
        "DesignInletAirWetBulbTemperature",
    )
    _set_if_present(tower.setDesignApproachTemperature, node, "DesignApproachTemperature")
    _set_if_present(tower.setDesignRangeTemperature, node, "DesignRangeTemperature")
    _set_autosizable_if_present(
        tower.setDesignWaterFlowRate,
        tower.autosizeDesignWaterFlowRate,
        node,
        "DesignWaterFlowRate",
    )
    _set_autosizable_if_present(
        tower.setDesignAirFlowRate,
        tower.autosizeDesignAirFlowRate,
        node,
        "DesignAirFlowRate",
    )
    _set_autosizable_if_present(
        tower.setDesignFanPower,
        tower.autosizeDesignFanPower,
        node,
        "DesignFanPower",
    )
    _set_if_present(tower.setMinimumAirFlowRateRatio, node, "MinimumAirFlowRateRatio")
    _set_if_present(
        tower.setFractionofTowerCapacityinFreeConvectionRegime,
        node,
        "FractionofTowerCapacityinFreeConvectionRegime",
    )
    _set_if_present(tower.setBasinHeaterCapacity, node, "BasinHeaterCapacity")
    _set_if_present(
        tower.setBasinHeaterSetpointTemperature,
        node,
        "BasinHeaterSetpointTemperature",
    )
    _set_if_present(tower.setCellControl, node, "CellControl", cast=str)
    _set_if_present(
        tower.setCellMinimumWaterFlowRateFraction,
        node,
        "CellMinimumWaterFlowRateFraction",
    )
    _set_if_present(
        tower.setCellMaximumWaterFlowRateFraction,
        node,
        "CellMaximumWaterFlowRateFraction",
    )
    _set_if_present(tower.setEndUseSubcategory, node, "EndUseSubcategory", cast=str)
    return tower, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:CoolingTower:VariableSpeed",
        name=name,
    )
