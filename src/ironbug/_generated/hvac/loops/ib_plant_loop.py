"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_PlantLoop(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_PlantLoop'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Loops/IB_PlantLoop.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Loop',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_PlantLoop_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'SizingPlant',
        'OperationScheme',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'SizingPlant',
        'OperationScheme',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'LoadDistributionScheme',
        'FluidType',
        'GlycolConcentration',
        'MaximumLoopTemperature',
        'MinimumLoopTemperature',
        'MaximumLoopFlowRate',
        'MinimumLoopFlowRate',
        'PlantLoopVolume',
        'CommonPipeSimulation',
        'PlantEquipmentOperationHeatingLoadSchedule',
        'PlantEquipmentOperationCoolingLoadSchedule',
        'PrimaryPlantEquipmentOperationSchemeSchedule',
        'ComponentSetpointOperationSchemeSchedule',
        'AvailabilityManagers',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CommonPipeSimulation': 'str',
        'FluidType': 'str',
        'GlycolConcentration': 'int',
        'LoadDistributionScheme': 'str',
        'MaximumLoopFlowRate': 'float',
        'MaximumLoopTemperature': 'float',
        'MinimumLoopFlowRate': 'float',
        'MinimumLoopTemperature': 'float',
        'PlantLoopVolume': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilityManagers': 'IB_AvailabilityManager',
        'ComponentSetpointOperationSchemeSchedule': 'IB_Schedule',
        'PlantEquipmentOperationCoolingLoadSchedule': 'IB_Schedule',
        'PlantEquipmentOperationHeatingLoadSchedule': 'IB_Schedule',
        'PrimaryPlantEquipmentOperationSchemeSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilityManagers',
    )
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'OperationScheme': 'IB_PlantEquipmentOperationSchemeBase',
        'SizingPlant': 'IB_SizingPlant',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'OperationScheme': 'IB_PlantEquipmentOperationSchemeBase',
        'SizingPlant': 'IB_SizingPlant',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_PlantLoop'] = PydanticField(default='IB_PlantLoop')
    SizingPlant: IB_SizingPlant | None = PydanticField(default=None)
    OperationScheme: IB_PlantEquipmentOperationSchemeBase | None = PydanticField(default=None)

__all__ = [
    'IB_PlantLoop',
]
