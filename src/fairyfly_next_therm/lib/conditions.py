"""Establish the default conditions within the fairyfly_next_therm library."""
from ._loadconditions import _conditions


# establish variables for the default materials used across the library
adiabatic = _conditions['Adiabatic']
frame_cavity = _conditions['Frame Cavity Surface']
exterior = _conditions['Generic Exterior']
interior = _conditions['Generic Interior']


# make lists of condition names to look up items in the library
CONDITIONS = tuple(_conditions.keys())


def condition_by_name(condition_name):
    """Get a solid condition from the library given the condition name.

    Args:
        condition_name: A text string for the display_name of the condition.
    """
    try:  # first check the default data
        return _conditions[condition_name]
    except KeyError:
        raise ValueError(
            '"{}" was not found in the solid condition library.'.format(condition_name))
