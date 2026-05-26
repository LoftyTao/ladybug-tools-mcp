"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_AirConditionerVariableRefrigerantFlow(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_AirConditionerVariableRefrigerantFlow'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Loops/IB_AirConditionerVariableRefrigerantFlow.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_VRFSystem',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_AirConditionerVariableRefrigerantFlow_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Terminals',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'Terminals',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'GrossRatedTotalCoolingCapacity',
        'GrossRatedCoolingCOP',
        'RatedTotalCoolingCapacity',
        'RatedCoolingCOP',
        'MinimumOutdoorTemperatureinCoolingMode',
        'MaximumOutdoorTemperatureinCoolingMode',
        'CoolingCapacityRatioModifierFunctionofLowTemperatureCurve',
        'CoolingCapacityRatioBoundaryCurve',
        'CoolingCapacityRatioModifierFunctionofHighTemperatureCurve',
        'CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve',
        'CoolingEnergyInputRatioBoundaryCurve',
        'CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve',
        'CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve',
        'CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve',
        'CoolingCombinationRatioCorrectionFactorCurve',
        'CoolingPartLoadFractionCorrelationCurve',
        'GrossRatedHeatingCapacity',
        'RatedHeatingCapacitySizingRatio',
        'RatedTotalHeatingCapacity',
        'RatedTotalHeatingCapacitySizingRatio',
        'RatedHeatingCOP',
        'MinimumOutdoorTemperatureinHeatingMode',
        'MaximumOutdoorTemperatureinHeatingMode',
        'HeatingCapacityRatioModifierFunctionofLowTemperatureCurve',
        'HeatingCapacityRatioBoundaryCurve',
        'HeatingCapacityRatioModifierFunctionofHighTemperatureCurve',
        'HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve',
        'HeatingEnergyInputRatioBoundaryCurve',
        'HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve',
        'HeatingPerformanceCurveOutdoorTemperatureType',
        'HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve',
        'HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve',
        'HeatingCombinationRatioCorrectionFactorCurve',
        'HeatingPartLoadFractionCorrelationCurve',
        'MinimumHeatPumpPartLoadRatio',
        'MasterThermostatPriorityControlType',
        'ThermostatPrioritySchedule',
        'HeatPumpWasteHeatRecovery',
        'EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode',
        'VerticalHeightusedforPipingCorrectionFactor',
        'PipingCorrectionFactorforLengthinCoolingModeCurve',
        'PipingCorrectionFactorforHeightinCoolingModeCoefficient',
        'EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode',
        'PipingCorrectionFactorforLengthinHeatingModeCurve',
        'PipingCorrectionFactorforHeightinHeatingModeCoefficient',
        'CrankcaseHeaterPowerperCompressor',
        'NumberofCompressors',
        'RatioofCompressorSizetoTotalCompressorCapacity',
        'MaximumOutdoorDrybulbTemperatureforCrankcaseHeater',
        'DefrostStrategy',
        'DefrostControl',
        'DefrostEnergyInputRatioModifierFunctionofTemperatureCurve',
        'DefrostTimePeriodFraction',
        'ResistiveDefrostHeaterCapacity',
        'MaximumOutdoorDrybulbTemperatureforDefrostOperation',
        'CondenserType',
        'WaterCondenserVolumeFlowRate',
        'EvaporativeCondenserEffectiveness',
        'EvaporativeCondenserAirFlowRate',
        'EvaporativeCondenserPumpRatedPowerConsumption',
        'BasinHeaterCapacity',
        'BasinHeaterSetpointTemperature',
        'BasinHeaterOperatingSchedule',
        'FuelType',
        'MinimumOutdoorTemperatureinHeatRecoveryMode',
        'MaximumOutdoorTemperatureinHeatRecoveryMode',
        'HeatRecoveryCoolingCapacityModifierCurve',
        'InitialHeatRecoveryCoolingCapacityFraction',
        'HeatRecoveryCoolingCapacityTimeConstant',
        'HeatRecoveryCoolingEnergyModifierCurve',
        'InitialHeatRecoveryCoolingEnergyFraction',
        'HeatRecoveryCoolingEnergyTimeConstant',
        'HeatRecoveryHeatingCapacityModifierCurve',
        'InitialHeatRecoveryHeatingCapacityFraction',
        'HeatRecoveryHeatingCapacityTimeConstant',
        'HeatRecoveryHeatingEnergyModifierCurve',
        'InitialHeatRecoveryHeatingEnergyFraction',
        'HeatRecoveryHeatingEnergyTimeConstant',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterCapacity': 'float',
        'BasinHeaterSetpointTemperature': 'float',
        'CondenserType': 'str',
        'CrankcaseHeaterPowerperCompressor': 'float',
        'DefrostControl': 'str',
        'DefrostStrategy': 'str',
        'DefrostTimePeriodFraction': 'float',
        'EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode': 'float',
        'EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode': 'float',
        'EvaporativeCondenserAirFlowRate': 'float',
        'EvaporativeCondenserEffectiveness': 'float',
        'EvaporativeCondenserPumpRatedPowerConsumption': 'float',
        'FuelType': 'str',
        'GrossRatedCoolingCOP': 'float',
        'GrossRatedHeatingCapacity': 'float',
        'GrossRatedTotalCoolingCapacity': 'float',
        'HeatPumpWasteHeatRecovery': 'bool | str',
        'HeatRecoveryCoolingCapacityTimeConstant': 'float',
        'HeatRecoveryCoolingEnergyTimeConstant': 'float',
        'HeatRecoveryHeatingCapacityTimeConstant': 'float',
        'HeatRecoveryHeatingEnergyTimeConstant': 'float',
        'InitialHeatRecoveryCoolingCapacityFraction': 'float',
        'InitialHeatRecoveryCoolingEnergyFraction': 'float',
        'InitialHeatRecoveryHeatingCapacityFraction': 'float',
        'InitialHeatRecoveryHeatingEnergyFraction': 'float',
        'MasterThermostatPriorityControlType': 'str',
        'MaximumOutdoorDrybulbTemperatureforCrankcaseHeater': 'float',
        'MaximumOutdoorDrybulbTemperatureforDefrostOperation': 'float',
        'MaximumOutdoorTemperatureinCoolingMode': 'float',
        'MaximumOutdoorTemperatureinHeatRecoveryMode': 'float',
        'MaximumOutdoorTemperatureinHeatingMode': 'float',
        'MinimumHeatPumpPartLoadRatio': 'float',
        'MinimumOutdoorTemperatureinCoolingMode': 'float',
        'MinimumOutdoorTemperatureinHeatRecoveryMode': 'float',
        'MinimumOutdoorTemperatureinHeatingMode': 'float',
        'NumberofCompressors': 'int',
        'PipingCorrectionFactorforHeightinCoolingModeCoefficient': 'float',
        'PipingCorrectionFactorforHeightinHeatingModeCoefficient': 'float',
        'RatedCoolingCOP': 'str | float | int | bool',
        'RatedHeatingCOP': 'float',
        'RatedHeatingCapacitySizingRatio': 'float',
        'RatedTotalCoolingCapacity': 'str | float | int | bool',
        'RatedTotalHeatingCapacity': 'str | float | int | bool',
        'RatedTotalHeatingCapacitySizingRatio': 'str | float | int | bool',
        'RatioofCompressorSizetoTotalCompressorCapacity': 'float',
        'ResistiveDefrostHeaterCapacity': 'float',
        'VerticalHeightusedforPipingCorrectionFactor': 'float',
        'WaterCondenserVolumeFlowRate': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'BasinHeaterOperatingSchedule': 'IB_Schedule',
        'CoolingCapacityRatioBoundaryCurve': 'IB_Curve',
        'CoolingCapacityRatioModifierFunctionofHighTemperatureCurve': 'IB_Curve',
        'CoolingCapacityRatioModifierFunctionofLowTemperatureCurve': 'IB_Curve',
        'CoolingCombinationRatioCorrectionFactorCurve': 'IB_Curve',
        'CoolingEnergyInputRatioBoundaryCurve': 'IB_Curve',
        'CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve': 'IB_Curve',
        'CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve': 'IB_Curve',
        'CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve': 'IB_Curve',
        'CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve': 'IB_Curve',
        'CoolingPartLoadFractionCorrelationCurve': 'IB_Curve',
        'DefrostEnergyInputRatioModifierFunctionofTemperatureCurve': 'IB_Curve',
        'HeatRecoveryCoolingCapacityModifierCurve': 'IB_Curve',
        'HeatRecoveryCoolingEnergyModifierCurve': 'IB_Curve',
        'HeatRecoveryHeatingCapacityModifierCurve': 'IB_Curve',
        'HeatRecoveryHeatingEnergyModifierCurve': 'IB_Curve',
        'HeatingCapacityRatioBoundaryCurve': 'IB_Curve',
        'HeatingCapacityRatioModifierFunctionofHighTemperatureCurve': 'IB_Curve',
        'HeatingCapacityRatioModifierFunctionofLowTemperatureCurve': 'IB_Curve',
        'HeatingCombinationRatioCorrectionFactorCurve': 'IB_Curve',
        'HeatingEnergyInputRatioBoundaryCurve': 'IB_Curve',
        'HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve': 'IB_Curve',
        'HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve': 'IB_Curve',
        'HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve': 'IB_Curve',
        'HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve': 'IB_Curve',
        'HeatingPartLoadFractionCorrelationCurve': 'IB_Curve',
        'HeatingPerformanceCurveOutdoorTemperatureType': 'IB_Curve',
        'PipingCorrectionFactorforLengthinCoolingModeCurve': 'IB_Curve',
        'PipingCorrectionFactorforLengthinHeatingModeCurve': 'IB_Curve',
        'ThermostatPrioritySchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'Terminals': 'List<IB_ZoneHVACTerminalUnitVariableRefrigerantFlow>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'Terminals': 'List<IB_ZoneHVACTerminalUnitVariableRefrigerantFlow>',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_AirConditionerVariableRefrigerantFlow'] = PydanticField(default='IB_AirConditionerVariableRefrigerantFlow')
    Terminals: list[IB_ZoneHVACTerminalUnitVariableRefrigerantFlow] | None = PydanticField(default=None)

__all__ = [
    'IB_AirConditionerVariableRefrigerantFlow',
]
