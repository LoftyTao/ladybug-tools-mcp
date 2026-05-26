"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_PumpVariableSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_PumpVariableSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_PumpVariableSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Pump',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_PumpVariableSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'RatedFlowRate',
        'RatedPumpHead',
        'RatedPowerConsumption',
        'MotorEfficiency',
        'FractionofMotorInefficienciestoFluidStream',
        'Coefficient1ofthePartLoadPerformanceCurve',
        'Coefficient2ofthePartLoadPerformanceCurve',
        'Coefficient3ofthePartLoadPerformanceCurve',
        'Coefficient4ofthePartLoadPerformanceCurve',
        'MinimumFlowRate',
        'PumpControlType',
        'PumpFlowRateSchedule',
        'PumpCurve',
        'ImpellerDiameter',
        'VFDControlType',
        'PumpRPMSchedule',
        'MinimumPressureSchedule',
        'MaximumPressureSchedule',
        'MinimumRPMSchedule',
        'MaximumRPMSchedule',
        'DesignPowerSizingMethod',
        'DesignElectricPowerPerUnitFlowRate',
        'DesignShaftPowerPerUnitFlowRatePerUnitHead',
        'SkinLossRadiativeFraction',
        'DesignMinimumFlowRateFraction',
        'EndUseSubcategory',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'DesignElectricPowerPerUnitFlowRate': 'float',
        'DesignMinimumFlowRateFraction': 'float',
        'DesignPowerSizingMethod': 'str',
        'DesignShaftPowerPerUnitFlowRatePerUnitHead': 'float',
        'EndUseSubcategory': 'str',
        'FractionofMotorInefficienciestoFluidStream': 'float',
        'ImpellerDiameter': 'float',
        'MinimumFlowRate': 'float',
        'MotorEfficiency': 'float',
        'PumpControlType': 'str',
        'RatedFlowRate': 'float',
        'RatedPowerConsumption': 'float',
        'RatedPumpHead': 'float',
        'SkinLossRadiativeFraction': 'float',
        'VFDControlType': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'Coefficient1ofthePartLoadPerformanceCurve': 'IB_Curve',
        'Coefficient2ofthePartLoadPerformanceCurve': 'IB_Curve',
        'Coefficient3ofthePartLoadPerformanceCurve': 'IB_Curve',
        'Coefficient4ofthePartLoadPerformanceCurve': 'IB_Curve',
        'MaximumPressureSchedule': 'IB_Schedule',
        'MaximumRPMSchedule': 'IB_Schedule',
        'MinimumPressureSchedule': 'IB_Schedule',
        'MinimumRPMSchedule': 'IB_Schedule',
        'PumpCurve': 'IB_Curve',
        'PumpFlowRateSchedule': 'IB_Schedule',
        'PumpRPMSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_PumpVariableSpeed'] = PydanticField(default='IB_PumpVariableSpeed')

__all__ = [
    'IB_PumpVariableSpeed',
]
