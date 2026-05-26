"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilCoolingFourPipeBeam(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilCoolingFourPipeBeam'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilCoolingFourPipeBeam.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilCoolingBasic',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilCoolingFourPipeBeam_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'BeamRatedCoolingCapacityperBeamLength',
        'BeamRatedCoolingRoomAirChilledWaterTemperatureDifference',
        'BeamRatedChilledWaterVolumeFlowRateperBeamLength',
        'BeamCoolingCapacityTemperatureDifferenceModificationFactorCurve',
        'BeamCoolingCapacityAirFlowModificationFactorCurve',
        'BeamCoolingCapacityChilledWaterFlowModificationFactorCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BeamRatedChilledWaterVolumeFlowRateperBeamLength': 'float',
        'BeamRatedCoolingCapacityperBeamLength': 'float',
        'BeamRatedCoolingRoomAirChilledWaterTemperatureDifference': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'BeamCoolingCapacityAirFlowModificationFactorCurve': 'IB_Curve',
        'BeamCoolingCapacityChilledWaterFlowModificationFactorCurve': 'IB_Curve',
        'BeamCoolingCapacityTemperatureDifferenceModificationFactorCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilCoolingFourPipeBeam'] = PydanticField(default='IB_CoilCoolingFourPipeBeam')

__all__ = [
    'IB_CoilCoolingFourPipeBeam',
]
