# coding=utf-8
"""Utilities to convert material dictionaries to Python objects."""
from fairyfly_next_therm.material.solid import SolidMaterial
from fairyfly_next_therm.material.hygrothermal import HygrothermalMaterial
from fairyfly_next_therm.material.cavity import CavityMaterial


MATERIAL_TYPES = ('SolidMaterial', 'HygrothermalMaterial', 'CavityMaterial')


def dict_to_material(material_dict, raise_exception=True):
    """Get a Python object of any Material from a dictionary.

    Args:
        material_dict: A dictionary of any Fairyfly material. Note
            that this should be a non-abridged dictionary to be valid.
        raise_exception: Boolean to note whether an exception should be raised
            if the object is not identified as a material. (Default: True).

    Returns:
        A Python object derived from the input constr_dict.
    """
    try:  # get the type key from the dictionary
        mat_type = material_dict['type']
    except KeyError:
        raise ValueError('Material dictionary lacks required "type" key.')

    if mat_type == 'SolidMaterial':
        return SolidMaterial.from_dict(material_dict)
    elif mat_type == 'HygrothermalMaterial':
        return HygrothermalMaterial.from_dict(material_dict)
    elif mat_type == 'CavityMaterial':
        return CavityMaterial.from_dict(material_dict)
    elif raise_exception:
        raise ValueError(
            '{} is not a recognized energy Material type'.format(material_dict))


def dict_abridged_to_material(material_dict, gases, raise_exception=True):
    """Get a Python object of any Material from an abridged dictionary.

    Args:
        constr_dict: An abridged dictionary of any Fairyfly energy material.
        gases: A dictionary with Gas identifiers as keys and Gas object instances
            as values. These will be used to reassign the gas that fills
            this cavity.
        raise_exception: Boolean to note whether an exception should be raised
            if the object is not identified as a material. Default: True.

    Returns:
        A Python object derived from the input constr_dict.
    """
    try:  # get the type key from the dictionary
        mat_type = material_dict['type']
    except KeyError:
        raise ValueError('Material dictionary lacks required "type" key.')

    if mat_type == 'SolidMaterial':
        return SolidMaterial.from_dict(material_dict)
    elif mat_type == 'HygrothermalMaterial':
        return HygrothermalMaterial.from_dict(material_dict)
    elif mat_type == 'CavityMaterialAbridged':
        return CavityMaterial.from_dict_abridged(material_dict, gases)
    elif raise_exception:
        raise ValueError(
            '{} is not a recognized energy Material type'.format(mat_type))
