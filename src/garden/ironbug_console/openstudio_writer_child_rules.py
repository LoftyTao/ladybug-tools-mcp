"""Required child source-class rules for Python Ironbug writer diagnostics."""

from __future__ import annotations


_PTAC_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingDXSingleSpeed",
        "IB_CoilHeatingElectric",
        "IB_FanOnOff",
    }
)

_PTHP_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingDXSingleSpeed",
        "IB_CoilHeatingDXSingleSpeed",
        "IB_FanOnOff",
        "IB_CoilHeatingElectric",
    }
)

_UNIT_HEATER_ELECTRIC_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingElectric",
        "IB_FanConstantVolume",
    }
)

_UNIT_HEATER_WATER_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingWater",
        "IB_FanOnOff",
    }
)

_UNIT_VENTILATOR_COOLING_HEATING_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingWater",
        "IB_CoilHeatingWater",
        "IB_FanOnOff",
    }
)

_UNIT_VENTILATOR_COOLING_ONLY_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingWater",
        "IB_FanOnOff",
    }
)

_UNIT_VENTILATOR_HEATING_ONLY_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingWater",
        "IB_FanOnOff",
    }
)

_FOUR_PIPE_FAN_COIL_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingWater",
        "IB_CoilHeatingWater",
        "IB_FanOnOff",
    }
)

_BASEBOARD_RADIANT_WATER_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingWaterBaseboardRadiant",
    }
)

_AIR_TERMINAL_REHEAT_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingWater",
    }
)

_AIR_TERMINAL_ELECTRIC_REHEAT_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingElectric",
    }
)

_PIU_ELECTRIC_REHEAT_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingElectric",
        "IB_FanConstantVolume",
    }
)

_PIU_WATER_REHEAT_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingWater",
        "IB_FanConstantVolume",
    }
)

_FOUR_PIPE_INDUCTION_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilHeatingWater",
    }
)

_FOUR_PIPE_BEAM_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingFourPipeBeam",
        "IB_CoilHeatingFourPipeBeam",
    }
)

_COOLED_BEAM_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingCooledBeam",
    }
)

_AIR_LOOP_UNITARY_SYSTEM_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingDXSingleSpeed",
        "IB_CoilHeatingDXSingleSpeed",
        "IB_CoilHeatingElectric",
        "IB_FanOnOff",
    }
)

_AIR_LOOP_UNITARY_SYSTEM_TWO_SPEED_FSM_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingDXTwoSpeed",
        "IB_CoilHeatingElectric",
        "IB_FanSystemModel",
    }
)

_VRF_TERMINAL_REQUIRED_CHILD_CLASSES = frozenset(
    {
        "IB_CoilCoolingDXVariableRefrigerantFlow",
        "IB_CoilHeatingDXVariableRefrigerantFlow",
        "IB_FanOnOff",
    }
)

def _missing_terminal_child_classes(
    *,
    source_class: str,
    child_source_classes: set[str],
) -> list[str]:
    alternatives = _terminal_child_alternatives(source_class)
    if alternatives:
        if any(required <= child_source_classes for required in alternatives):
            return []
        best_match = min(
            alternatives,
            key=lambda required: len(required - child_source_classes),
        )
        return sorted(best_match - child_source_classes)
    return sorted(_required_terminal_child_classes(source_class) - child_source_classes)

def _terminal_child_alternatives(source_class: str) -> tuple[frozenset[str], ...]:
    if source_class == "IB_ZoneHVACUnitHeater":
        return (
            _UNIT_HEATER_ELECTRIC_REQUIRED_CHILD_CLASSES,
            _UNIT_HEATER_WATER_REQUIRED_CHILD_CLASSES,
        )
    if source_class in {
        "IB_AirTerminalSingleDuctConstantVolumeReheat",
        "IB_AirTerminalSingleDuctVAVHeatAndCoolReheat",
        "IB_AirTerminalSingleDuctVAVReheat",
    }:
        return (
            _AIR_TERMINAL_ELECTRIC_REHEAT_REQUIRED_CHILD_CLASSES,
            _AIR_TERMINAL_REHEAT_REQUIRED_CHILD_CLASSES,
        )
    if source_class in {
        "IB_AirTerminalSingleDuctParallelPIUReheat",
        "IB_AirTerminalSingleDuctSeriesPIUReheat",
    }:
        return (
            _PIU_ELECTRIC_REHEAT_REQUIRED_CHILD_CLASSES,
            _PIU_WATER_REHEAT_REQUIRED_CHILD_CLASSES,
        )
    if source_class == "IB_AirLoopHVACUnitarySystem":
        return (
            _AIR_LOOP_UNITARY_SYSTEM_REQUIRED_CHILD_CLASSES,
            _AIR_LOOP_UNITARY_SYSTEM_TWO_SPEED_FSM_CHILD_CLASSES,
        )
    return ()

def _missing_terminal_child_message(
    *,
    source_class: str,
    missing_children: list[str],
) -> str:
    if source_class == "IB_ZoneHVACUnitHeater":
        return (
            "IB_ZoneHVACUnitHeater requires either "
            "IB_CoilHeatingElectric + IB_FanConstantVolume or "
            "IB_CoilHeatingWater + IB_FanOnOff. Missing from the nearest "
            f"supported combination: {', '.join(missing_children)}."
        )
    return (
        f"{source_class} requires child source classes: "
        f"{', '.join(missing_children)}."
    )

def _required_terminal_child_classes(source_class: str) -> frozenset[str]:
    if source_class == "IB_ZoneHVACPackagedTerminalAirConditioner":
        return _PTAC_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACPackagedTerminalHeatPump":
        return _PTHP_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACUnitHeater":
        return _UNIT_HEATER_ELECTRIC_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACFourPipeFanCoil":
        return _FOUR_PIPE_FAN_COIL_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACBaseboardRadiantConvectiveWater":
        return _BASEBOARD_RADIANT_WATER_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACUnitVentilator_CoolingHeating":
        return _UNIT_VENTILATOR_COOLING_HEATING_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACUnitVentilator_CoolingOnly":
        return _UNIT_VENTILATOR_COOLING_ONLY_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACUnitVentilator_HeatingOnly":
        return _UNIT_VENTILATOR_HEATING_ONLY_REQUIRED_CHILD_CLASSES
    if source_class == "IB_AirTerminalSingleDuctConstantVolumeReheat":
        return _AIR_TERMINAL_REHEAT_REQUIRED_CHILD_CLASSES
    if source_class == "IB_AirTerminalSingleDuctVAVReheat":
        return _AIR_TERMINAL_REHEAT_REQUIRED_CHILD_CLASSES
    if source_class == "IB_AirTerminalSingleDuctVAVHeatAndCoolReheat":
        return _AIR_TERMINAL_ELECTRIC_REHEAT_REQUIRED_CHILD_CLASSES
    if source_class == "IB_AirTerminalSingleDuctParallelPIUReheat":
        return _PIU_ELECTRIC_REHEAT_REQUIRED_CHILD_CLASSES
    if source_class == "IB_AirTerminalSingleDuctSeriesPIUReheat":
        return _PIU_ELECTRIC_REHEAT_REQUIRED_CHILD_CLASSES
    if (
        source_class
        == "IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction"
    ):
        return _FOUR_PIPE_INDUCTION_REQUIRED_CHILD_CLASSES
    if source_class == "IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam":
        return _FOUR_PIPE_BEAM_REQUIRED_CHILD_CLASSES
    if source_class == "IB_AirTerminalSingleDuctConstantVolumeCooledBeam":
        return _COOLED_BEAM_REQUIRED_CHILD_CLASSES
    if source_class == "IB_ZoneHVACTerminalUnitVariableRefrigerantFlow":
        return _VRF_TERMINAL_REQUIRED_CHILD_CLASSES
    return frozenset()
