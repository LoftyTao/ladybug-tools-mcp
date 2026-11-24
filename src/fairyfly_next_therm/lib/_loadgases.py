"""Load all gases from the standards library."""
from fairyfly_next_therm.config import folders
from fairyfly_next_therm.material.gas import PureGas, Gas

import os
import json


# empty dictionary to hold loaded gases
_pure_gases = {}
_gases = {}


def check_and_add_gas(gas):
    """Check that a gas is not overwriting a default and add it."""
    gas.lock()
    if gas.display_name != 'Air':
        if isinstance(gas, PureGas):
            _pure_gases[gas.display_name] = gas
        elif isinstance(gas, Gas):
            _gases[gas.display_name] = gas


def load_gases_from_folder(lib_folder):
    """Load all of the gas objects from a therm standards folder.

    Args:
        lib_folder: Path to a sub-folder within a honeybee standards folder.
    """
    for f in os.listdir(lib_folder):
        f_path = os.path.join(lib_folder, f)
        if os.path.isfile(f_path):
            if f_path.endswith('.xml'):
                gs, pgs = Gas.extract_all_from_xml_file(f_path)
                for g in pgs + gs:
                    check_and_add_gas(g)
            elif f_path.endswith('.json'):
                with open(f_path) as json_file:
                    data = json.load(json_file)
                if 'type' in data:  # single object
                    if data['type'] == 'PureGas':
                        check_and_add_gas(PureGas.from_dict(data))
                    elif data['type'] == 'Gas':
                        check_and_add_gas(Gas.from_dict(data))
                else:  # a collection of several objects
                    for g_id in data:
                        try:
                            g_dict = data[g_id]
                            if g_dict['type'] == 'PureGas':
                                check_and_add_gas(PureGas.from_dict(g_dict))
                            elif g_dict['type'] == 'Gas':
                                check_and_add_gas(Gas.from_dict(g_dict))
                        except (TypeError, KeyError):
                            pass  # not an acceptable JSON; possibly a comment


# load therm gases from a user folder if we are not using the official THERM lib
if folders.user_gas_folder is not None:
    load_gases_from_folder(folders.user_gas_folder)


# make sure that we always have an Air gas
air_dict = {
    'type': 'PureGas',
    'identifier': '8d33196f-f052-46e6-8353-bccb9a779f9c',
    'conductivity_coeff_a': 0.002873,
    'viscosity_coeff_a': 3.723e-06,
    'specific_heat_coeff_a': 1002.737,
    'conductivity_coeff_b': 7.76e-05,
    'viscosity_coeff_b': 4.94e-08,
    'specific_heat_coeff_b': 0.012324,
    'conductivity_coeff_c': 0.0,
    'viscosity_coeff_c': 0.0,
    'specific_heat_coeff_c': 0.0,
    'specific_heat_ratio': 1.4,
    'molecular_weight': 28.97,
    'display_name': 'Air',
    'protected': True,
    'color': '#556d11'
}
pure_air = PureGas.from_dict(air_dict)
pure_air.lock()
_pure_gases['Air'] = pure_air
air_gas = Gas(
    [pure_air], [1], identifier='6c2409e9-5296-46c1-be11-9029b59a549b'
)
air_gas.display_name = 'Air'
air_gas.protected = True
air_gas.lock()
_gases['Air'] = air_gas

# load the gasses from the LBNL library if they exist
if folders.gas_lib_file is not None:
    gs, pgs = Gas.extract_all_from_xml_file(folders.gas_lib_file)
    for pg in pgs:
        pg.lock()
        _pure_gases[pg.display_name] = pg
    for g in gs:
        g.lock()
        _gases[g.display_name] = g
