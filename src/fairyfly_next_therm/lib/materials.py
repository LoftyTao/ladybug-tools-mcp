"""Establish the default materials within the fairyfly_next_therm library."""
from ._loadmaterials import _solid_materials, _cavity_materials


# establish variables for the default materials used across the library
concrete = _solid_materials['Generic HW Concrete']
air_cavity = _cavity_materials['Frame Cavity - Generic']


# make lists of material identifiers to look up items in the library
SOLID_MATERIALS = tuple(_solid_materials.keys())
CAVITY_MATERIALS = tuple(_cavity_materials.keys())


def solid_material_by_name(material_name):
    """Get a solid material from the library given the material name.

    Args:
        material_name: A text string for the display_name of the material.
    """
    try:  # first check the default data
        return _solid_materials[material_name]
    except KeyError:
        raise ValueError(
            '"{}" was not found in the solid material library.'.format(material_name))


def cavity_material_by_name(material_name):
    """Get a cavity material from the library given the material name.

    Args:
        material_name: A text string for the display_name of the material.
    """
    try:  # first check the default data
        return _cavity_materials[material_name]
    except KeyError:
        raise ValueError(
            '"{}" was not found in the cavity material library.'.format(material_name))
