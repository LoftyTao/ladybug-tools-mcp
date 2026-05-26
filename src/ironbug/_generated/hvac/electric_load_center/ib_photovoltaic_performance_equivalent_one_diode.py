"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_PhotovoltaicPerformanceEquivalentOneDiode(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_PhotovoltaicPerformanceEquivalentOneDiode'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ElectricLoadCenter/IB_PhotovoltaicPerformanceEquivalentOneDiode.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_PhotovoltaicPerformance',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_PhotovoltaicPerformanceEquivalentOneDiode_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'Celltype',
        'NumberofCellsinSeries',
        'ActiveArea',
        'TransmittanceAbsorptanceProduct',
        'SemiconductorBandgap',
        'ShuntResistance',
        'ShortCircuitCurrent',
        'OpenCircuitVoltage',
        'ReferenceTemperature',
        'ReferenceInsolation',
        'ModuleCurrentatMaximumPower',
        'ModuleVoltageatMaximumPower',
        'TemperatureCoefficientofShortCircuitCurrent',
        'TemperatureCoefficientofOpenCircuitVoltage',
        'NominalOperatingCellTemperatureTestAmbientTemperature',
        'NominalOperatingCellTemperatureTestCellTemperature',
        'NominalOperatingCellTemperatureTestInsolation',
        'ModuleHeatLossCoefficient',
        'TotalHeatCapacity',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ActiveArea': 'float',
        'Celltype': 'str',
        'ModuleCurrentatMaximumPower': 'float',
        'ModuleHeatLossCoefficient': 'float',
        'ModuleVoltageatMaximumPower': 'float',
        'NominalOperatingCellTemperatureTestAmbientTemperature': 'float',
        'NominalOperatingCellTemperatureTestCellTemperature': 'float',
        'NominalOperatingCellTemperatureTestInsolation': 'float',
        'NumberofCellsinSeries': 'int',
        'OpenCircuitVoltage': 'float',
        'ReferenceInsolation': 'float',
        'ReferenceTemperature': 'float',
        'SemiconductorBandgap': 'float',
        'ShortCircuitCurrent': 'float',
        'ShuntResistance': 'float',
        'TemperatureCoefficientofOpenCircuitVoltage': 'float',
        'TemperatureCoefficientofShortCircuitCurrent': 'float',
        'TotalHeatCapacity': 'float',
        'TransmittanceAbsorptanceProduct': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_PhotovoltaicPerformanceEquivalentOneDiode'] = PydanticField(default='IB_PhotovoltaicPerformanceEquivalentOneDiode')

__all__ = [
    'IB_PhotovoltaicPerformanceEquivalentOneDiode',
]
