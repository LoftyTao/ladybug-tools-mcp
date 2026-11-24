# coding=utf-8
"""Utilities to convert THERM XML files to Material objects."""
from __future__ import division
import xml.etree.ElementTree as ET

from .solid import SolidMaterial
from .hygrothermal import HygrothermalMaterial
from .cavity import CavityMaterial

# HygroThermal child tags that SolidMaterial already models; any additional
# tag means the record carries hygrothermal data a dry material cannot hold
_DRY_HYGROTHERMAL_TAGS = frozenset((
    'ThermalConductivityDry', 'BulkDensity', 'Porosity',
    'SpecificHeatCapacityDry', 'WaterVaporDiffusionResistanceFactor'))


def extract_all_materials_from_xml_file(xml_file, gases=None):
    """Extract all Material objects from a THERM XML file.

    Args:
        xml_file: A path to an XML file containing objects Material objects.
        gases: A dictionary with gas names as keys and Gas object instances
            as values. These will be used to reassign the gas that fills
            cavity materials. If None, only solid materials are extracted.

    Returns:
        A tuple with two elements

        -   solid_materials: A list of all solid materials in the XML
            file as fairyfly_next_therm SolidMaterial or HygrothermalMaterial
            objects. Solid records that carry moisture storage, transport,
            or extended scalar data are returned as HygrothermalMaterial.

        -   cavity_materials: A list of all CavityMaterial objects in the XML
            file as fairyfly_next_therm CavityMaterial objects.
    """
    # read the file and get the root
    tree = ET.parse(xml_file)
    root = tree.getroot()
    # extract all of the objects
    solid_materials, cavity_materials = [], []
    for mat_obj in root:
        if mat_obj.find('Solid') is not None:
            hyt = mat_obj.find('Solid/HygroThermal')
            extended = hyt is not None and any(
                child.tag not in _DRY_HYGROTHERMAL_TAGS for child in hyt)
            if extended:
                # A record with moisture storage or transport tags carries
                # data a SolidMaterial cannot hold; failing to parse it must
                # be loud instead of silently losing the material.
                # direct children only; fields nested inside the moisture
                # tables are rejected by HygrothermalMaterial.from_therm_xml
                unknown = [child.tag for child in hyt
                           if child.tag not in _DRY_HYGROTHERMAL_TAGS
                           and child.tag not in HygrothermalMaterial.TABLE_TAGS
                           .values()
                           and child.tag not in
                           dict(HygrothermalMaterial.SCALAR_TAGS)]
                if unknown:
                    raise ValueError(
                        'Material "{}" has unsupported HygroThermal fields: '
                        '{}.'.format(
                            mat_obj.findtext('Name') or mat_obj.findtext('UUID'),
                            ', '.join(unknown)))
                try:
                    solid_materials.append(
                        HygrothermalMaterial.from_therm_xml(mat_obj))
                except Exception as error:
                    raise ValueError(
                        'Material "{}" carries hygrothermal data but could '
                        'not be parsed: {}'.format(
                            mat_obj.findtext('Name') or mat_obj.findtext('UUID'),
                            error))
            else:
                try:
                    solid_materials.append(SolidMaterial.from_therm_xml(mat_obj))
                except Exception:  # not a valid solid material
                    pass
        elif mat_obj.find('Cavity') is not None and gases is not None:
            try:
                cavity_materials.append(CavityMaterial.from_therm_xml(mat_obj, gases))
            except Exception:  # not a valid cavity material
                pass
    return solid_materials, cavity_materials
