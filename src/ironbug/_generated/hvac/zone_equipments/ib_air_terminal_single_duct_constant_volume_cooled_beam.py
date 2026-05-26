"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_AirTerminalSingleDuctConstantVolumeCooledBeam(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_AirTerminalSingleDuctConstantVolumeCooledBeam'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ZoneEquipments/AirTerminals/IB_AirTerminalSingleDuctConstantVolumeCooledBeam.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_AirTerminal',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_AirTerminalSingleDuctConstantVolumeCooledBeam_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'CooledBeamType',
        'SupplyAirVolumetricFlowRate',
        'MaximumTotalChilledWaterVolumetricFlowRate',
        'NumberofBeams',
        'BeamLength',
        'DesignInletWaterTemperature',
        'DesignOutletWaterTemperature',
        'CoefficientofInductionKin',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BeamLength': 'float',
        'CoefficientofInductionKin': 'float',
        'CooledBeamType': 'str',
        'DesignInletWaterTemperature': 'float',
        'DesignOutletWaterTemperature': 'float',
        'MaximumTotalChilledWaterVolumetricFlowRate': 'float',
        'NumberofBeams': 'int',
        'SupplyAirVolumetricFlowRate': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_AirTerminalSingleDuctConstantVolumeCooledBeam'] = PydanticField(default='IB_AirTerminalSingleDuctConstantVolumeCooledBeam')

__all__ = [
    'IB_AirTerminalSingleDuctConstantVolumeCooledBeam',
]
