# coding=utf-8
"""Utilities to convert condition dictionaries to Python objects."""
from fairyfly_next_therm.condition.steadystate import SteadyState
from fairyfly_next_therm.condition.transient import Transient


CONDITION_TYPES = ('SteadyState', 'Transient')


def dict_to_condition(condition_dict, raise_exception=True):
    """Get a Python object of any condition from a dictionary.

    Args:
        condition_dict: A dictionary of any Fairyfly-Next THERM condition.
        raise_exception: Boolean to note whether an exception should be raised
            if the object is not identified as a condition. (Default: True).

    Returns:
        A Python object derived from the input condition_dict.
    """
    try:  # get the type key from the dictionary
        con_type = condition_dict['type']
    except KeyError:
        raise ValueError('Condition dictionary lacks required "type" key.')

    if con_type == 'SteadyState':
        return SteadyState.from_dict(condition_dict)
    elif con_type == 'Transient':
        return Transient.from_dict(condition_dict)
    elif raise_exception:
        raise ValueError(
            '{} is not a recognized THERM condition type'.format(
                condition_dict))
