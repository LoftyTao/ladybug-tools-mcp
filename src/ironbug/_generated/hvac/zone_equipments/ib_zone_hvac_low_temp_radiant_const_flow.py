"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ZoneHVACLowTempRadiantConstFlow(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ZoneHVACLowTempRadiantConstFlow'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ZoneEquipments/ZoneHVAC/IB_ZoneHVACLowTempRadiantConstFlow.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ZoneEquipment',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ZoneHVACLowTempRadiantConstFlow_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'RadiantSurfaceType',
        'FluidtoRadiantSurfaceHeatTransferModel',
        'HydronicTubingInsideDiameter',
        'HydronicTubingOutsideDiameter',
        'HydronicTubingLength',
        'HydronicTubingConductivity',
        'TemperatureControlType',
        'RunningMeanOutdoorDryBulbTemperatureWeightingFactor',
        'RatedFlowRate',
        'PumpFlowRateSchedule',
        'RatedPumpHead',
        'RatedPowerConsumption',
        'MotorEfficiency',
        'FractionofMotorInefficienciestoFluidStream',
        'NumberofCircuits',
        'CircuitLength',
        'ChangeoverDelayTimePeriodSchedule',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CircuitLength': 'float',
        'FluidtoRadiantSurfaceHeatTransferModel': 'str',
        'FractionofMotorInefficienciestoFluidStream': 'float',
        'HydronicTubingConductivity': 'float',
        'HydronicTubingInsideDiameter': 'float',
        'HydronicTubingLength': 'float',
        'HydronicTubingOutsideDiameter': 'float',
        'MotorEfficiency': 'float',
        'NumberofCircuits': 'str',
        'RadiantSurfaceType': 'str',
        'RatedFlowRate': 'float',
        'RatedPowerConsumption': 'float',
        'RatedPumpHead': 'float',
        'RunningMeanOutdoorDryBulbTemperatureWeightingFactor': 'float',
        'TemperatureControlType': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'ChangeoverDelayTimePeriodSchedule': 'IB_Schedule',
        'PumpFlowRateSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ZoneHVACLowTempRadiantConstFlow'] = PydanticField(default='IB_ZoneHVACLowTempRadiantConstFlow')

__all__ = [
    'IB_ZoneHVACLowTempRadiantConstFlow',
]
