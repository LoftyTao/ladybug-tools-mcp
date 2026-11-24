"""Gas library."""
from ._loadgases import _pure_gases, _gases


# establish variables for the default gasess used across the library
pure_air = _pure_gases['Air']
air = _gases['Air']

# make lists of gases to look up items in the library
PURE_GASES = tuple(_pure_gases.keys())
GASES = tuple(_gases.keys())


def gas_by_name(gas_name):
    """Get a gas from the library given its name.

    Args:
        gas_name: A text string for the display_name of the gas.
    """
    try:
        return _gases[gas_name]
    except KeyError:
        raise ValueError('"{}" was not found in the gas library.'.format(gas_name))


def pure_gas_by_name(pure_gas_name):
    """Get a pure gas from the library given its name.

    Args:
        gas_name: A text string for the display_name of the pure gas.
    """
    try:
        return _pure_gases[pure_gas_name]
    except KeyError:
        raise ValueError('"{}" was not found in the pure gas '
                         'library.'.format(pure_gas_name))
