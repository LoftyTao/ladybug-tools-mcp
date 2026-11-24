"""Load all materials from the LBNL XML files and JSON libraries."""
import os
import json

from fairyfly_next_therm.config import folders
from fairyfly_next_therm.material.solid import SolidMaterial
from fairyfly_next_therm.material.hygrothermal import HygrothermalMaterial
from fairyfly_next_therm.material.cavity import CavityMaterial
from fairyfly_next_therm.material.xmlutil import extract_all_materials_from_xml_file
from ._loadgases import _gases

# empty dictionaries to hold loaded materials
_solid_materials = {}
_cavity_materials = {}


def check_and_add_material(mat):
    """Check that a mat is not overwriting a default and add it."""
    mat.lock()
    if mat.display_name not in ('Generic HW Concrete', 'Frame Cavity - CEN Simplified'):
        if isinstance(mat, (SolidMaterial, HygrothermalMaterial)):
            _solid_materials[mat.display_name] = mat
        elif isinstance(mat, CavityMaterial):
            _cavity_materials[mat.display_name] = mat


def load_materials_from_folder(lib_folder):
    """Load all of the material objects from a therm standards folder.

    Args:
        lib_folder: Path to a sub-folder within a honeybee standards folder.
    """
    for f in os.listdir(lib_folder):
        f_path = os.path.join(lib_folder, f)
        if os.path.isfile(f_path):
            if f_path.endswith('.xml'):
                solid, cavity = extract_all_materials_from_xml_file(f_path, _gases)
                for m in solid + cavity:
                    check_and_add_material(m)
            elif f_path.endswith('.json'):
                with open(f_path) as json_file:
                    data = json.load(json_file)
                if 'type' in data:  # single object
                    if data['type'] == 'SolidMaterial':
                        check_and_add_material(SolidMaterial.from_dict(data))
                    elif data['type'] == 'HygrothermalMaterial':
                        check_and_add_material(
                            HygrothermalMaterial.from_dict(data))
                    elif data['type'] == 'CavityMaterial':
                        check_and_add_material(CavityMaterial.from_dict(data))
                else:  # a collection of several objects
                    for m_id in data:
                        try:
                            m_dict = data[m_id]
                            if m_dict['type'] == 'SolidMaterial':
                                check_and_add_material(SolidMaterial.from_dict(m_dict))
                            elif m_dict['type'] == 'HygrothermalMaterial':
                                check_and_add_material(
                                    HygrothermalMaterial.from_dict(m_dict))
                            elif m_dict['type'] == 'CavityMaterial':
                                check_and_add_material(CavityMaterial.from_dict(m_dict))
                        except (TypeError, KeyError):
                            pass  # not an acceptable JSON; possibly a comment


# load therm gases from a user folder if we are not using the official THERM lib
if folders.user_material_folder is not None:
    load_materials_from_folder(folders.user_material_folder)


# ensure that there is always a concrete material
concrete_dict = {
    'type': 'SolidMaterial',
    'identifier': '6442842d-7c8f-4231-a9b3-64302e3b2bc4',
    'display_name': 'Generic HW Concrete',
    'conductivity': 1.95,
    'emissivity': 0.9,
    'emissivity_back': 0.9,
    'density': 2240,
    'porosity': 0.24,
    'specific_heat': 900,
    'vapor_diffusion_resistance': 19,
    'color': '#808080',
    'protected': True
}
concrete = SolidMaterial.from_dict(concrete_dict)
concrete.lock()
_solid_materials[concrete.display_name] = concrete

# ensure that we always have an air cavity material
air_dict = {
    'type': 'CavityMaterialAbridged',
    'identifier': '0b46bbd7-0dbc-c148-3afe-87431bf0f66f',
    'gas': 'Air',
    'cavity_model': 'ISO15099',
    'emissivity': 0.9,
    'emissivity_back': 0.9,
    'display_name': 'Frame Cavity - Generic',
    'protected': True,
    'color': '#00ff00'
}
air_mat = CavityMaterial.from_dict_abridged(air_dict, _gases)
air_mat.lock()
_cavity_materials[air_mat.display_name] = air_mat


# load the materials from the LBNL library if they exist
if folders.material_lib_file is not None:
    solid, cavit = extract_all_materials_from_xml_file(folders.material_lib_file, _gases)
    for sol in solid:
        sol.lock()
        _solid_materials[sol.display_name] = sol
    for cav in cavit:
        cav.lock()
        _cavity_materials[cav.display_name] = cav
