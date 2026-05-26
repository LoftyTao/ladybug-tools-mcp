"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_GroundHeatExchangerHorizontalTrench(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_GroundHeatExchangerHorizontalTrench'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_GroundHeatExchangerHorizontalTrench.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_GroundHeatExchangerHorizontalTrench_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'DesignFlowRate',
        'TrenchLengthinPipeAxialDirection',
        'NumberofTrenches',
        'HorizontalSpacingBetweenPipes',
        'PipeInnerDiameter',
        'PipeOuterDiameter',
        'BurialDepth',
        'SoilThermalConductivity',
        'SoilDensity',
        'SoilSpecificHeat',
        'PipeThermalConductivity',
        'PipeDensity',
        'PipeSpecificHeat',
        'SoilMoistureContentPercent',
        'SoilMoistureContentPercentatSaturation',
        'GroundTemperatureModel',
        'KusudaAchenbachAverageSurfaceTemperature',
        'KusudaAchenbachAverageAmplitudeofSurfaceTemperature',
        'KusudaAchenbachPhaseShiftofMinimumSurfaceTemperature',
        'EvapotranspirationGroundCoverParameter',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BurialDepth': 'float',
        'DesignFlowRate': 'float',
        'EvapotranspirationGroundCoverParameter': 'float',
        'GroundTemperatureModel': 'str | float | int | bool',
        'HorizontalSpacingBetweenPipes': 'float',
        'KusudaAchenbachAverageAmplitudeofSurfaceTemperature': 'str | float | int | bool',
        'KusudaAchenbachAverageSurfaceTemperature': 'str | float | int | bool',
        'KusudaAchenbachPhaseShiftofMinimumSurfaceTemperature': 'str | float | int | bool',
        'NumberofTrenches': 'int',
        'PipeDensity': 'float',
        'PipeInnerDiameter': 'float',
        'PipeOuterDiameter': 'float',
        'PipeSpecificHeat': 'float',
        'PipeThermalConductivity': 'float',
        'SoilDensity': 'float',
        'SoilMoistureContentPercent': 'float',
        'SoilMoistureContentPercentatSaturation': 'float',
        'SoilSpecificHeat': 'float',
        'SoilThermalConductivity': 'float',
        'TrenchLengthinPipeAxialDirection': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_GroundHeatExchangerHorizontalTrench'] = PydanticField(default='IB_GroundHeatExchangerHorizontalTrench')

__all__ = [
    'IB_GroundHeatExchangerHorizontalTrench',
]
