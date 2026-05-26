"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_PhotovoltaicPerformanceSandia(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_PhotovoltaicPerformanceSandia'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ElectricLoadCenter/IB_PhotovoltaicPerformanceSandia.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_PhotovoltaicPerformance',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_PhotovoltaicPerformanceSandia_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ActiveArea',
        'NumberofCellsinSeries',
        'NumberofCellsinParallel',
        'ShortCircuitCurrent',
        'OpenCircuitVoltage',
        'CurrentatMaximumPowerPoint',
        'VoltageatMaximumPowerPoint',
        'SandiaDatabaseParameteraIsc',
        'SandiaDatabaseParameteraImp',
        'SandiaDatabaseParameterc0',
        'SandiaDatabaseParameterc1',
        'SandiaDatabaseParameterBVoc0',
        'SandiaDatabaseParametermBVoc',
        'SandiaDatabaseParameterBVmp0',
        'SandiaDatabaseParametermBVmp',
        'DiodeFactor',
        'SandiaDatabaseParameterc2',
        'SandiaDatabaseParameterc3',
        'SandiaDatabaseParametera0',
        'SandiaDatabaseParametera1',
        'SandiaDatabaseParametera2',
        'SandiaDatabaseParametera3',
        'SandiaDatabaseParametera4',
        'SandiaDatabaseParameterb0',
        'SandiaDatabaseParameterb1',
        'SandiaDatabaseParameterb2',
        'SandiaDatabaseParameterb3',
        'SandiaDatabaseParameterb4',
        'SandiaDatabaseParameterb5',
        'SandiaDatabaseParameterDeltaTc',
        'SandiaDatabaseParameterfd',
        'SandiaDatabaseParametera',
        'SandiaDatabaseParameterb',
        'SandiaDatabaseParameterc4',
        'SandiaDatabaseParameterc5',
        'SandiaDatabaseParameterIx0',
        'SandiaDatabaseParameterIxx0',
        'SandiaDatabaseParameterc6',
        'SandiaDatabaseParameterc7',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ActiveArea': 'float',
        'CurrentatMaximumPowerPoint': 'float',
        'DiodeFactor': 'float',
        'NumberofCellsinParallel': 'int',
        'NumberofCellsinSeries': 'int',
        'OpenCircuitVoltage': 'float',
        'SandiaDatabaseParameterBVmp0': 'float',
        'SandiaDatabaseParameterBVoc0': 'float',
        'SandiaDatabaseParameterDeltaTc': 'float',
        'SandiaDatabaseParameterIx0': 'float',
        'SandiaDatabaseParameterIxx0': 'float',
        'SandiaDatabaseParametera': 'float',
        'SandiaDatabaseParametera0': 'float',
        'SandiaDatabaseParametera1': 'float',
        'SandiaDatabaseParametera2': 'float',
        'SandiaDatabaseParametera3': 'float',
        'SandiaDatabaseParametera4': 'float',
        'SandiaDatabaseParameteraImp': 'float',
        'SandiaDatabaseParameteraIsc': 'float',
        'SandiaDatabaseParameterb': 'float',
        'SandiaDatabaseParameterb0': 'float',
        'SandiaDatabaseParameterb1': 'float',
        'SandiaDatabaseParameterb2': 'float',
        'SandiaDatabaseParameterb3': 'float',
        'SandiaDatabaseParameterb4': 'float',
        'SandiaDatabaseParameterb5': 'float',
        'SandiaDatabaseParameterc0': 'float',
        'SandiaDatabaseParameterc1': 'float',
        'SandiaDatabaseParameterc2': 'float',
        'SandiaDatabaseParameterc3': 'float',
        'SandiaDatabaseParameterc4': 'float',
        'SandiaDatabaseParameterc5': 'float',
        'SandiaDatabaseParameterc6': 'float',
        'SandiaDatabaseParameterc7': 'float',
        'SandiaDatabaseParameterfd': 'float',
        'SandiaDatabaseParametermBVmp': 'float',
        'SandiaDatabaseParametermBVoc': 'float',
        'ShortCircuitCurrent': 'float',
        'VoltageatMaximumPowerPoint': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_PhotovoltaicPerformanceSandia'] = PydanticField(default='IB_PhotovoltaicPerformanceSandia')

__all__ = [
    'IB_PhotovoltaicPerformanceSandia',
]
