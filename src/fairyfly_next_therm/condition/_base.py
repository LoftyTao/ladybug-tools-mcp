# coding=utf-8
"""Base therm condition."""
from __future__ import division
import uuid
import random

from ladybug.color import Color
from fairyfly._lockable import lockable
from fairyfly.typing import valid_uuid


@lockable
class _ThermConditionBase(object):
    """Base therm condition.

    Args:
        identifier: Text string for a unique Condition ID. Must be < 100 characters
            and not contain any thermPlus special characters. This will be used to
            identify the object across a model and in the exported IDF.

    Properties:
        * identifier
        * display_name
        * color
        * protected
        * project_tag
        * user_data
    """
    __slots__ = ('_identifier', '_display_name', '_color', '_protected', '_project_tag',
                 '_user_data', '_locked')

    def __init__(self, identifier):
        """Initialize therm condition base."""
        self._locked = False
        self.identifier = identifier
        self._display_name = None
        self.color = None
        self.protected = False
        self.project_tag = None
        self._user_data = None

    @property
    def identifier(self):
        """Get or set a text string for the unique object identifier.

        This must be a UUID in the format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        and it remains constant as the object is mutated, copied, and
        serialized to different formats (eg. therm XML). As such, this
        property is used to reference the object across a Model.
        """
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        if value is None:
            self._identifier = str(uuid.uuid4())
        else:
            self._identifier = valid_uuid(value, 'therm condition identifier')

    @property
    def display_name(self):
        """Get or set a string for the object name without any character restrictions.

        If not set, this will be equal to the identifier.
        """
        if self._display_name is None:
            return self._identifier
        return self._display_name

    @display_name.setter
    def display_name(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._display_name = value

    @property
    def color(self):
        """Get or set an optional color for the condition as it displays in THERM.

        This will always be a Ladybug Color object when getting this property
        but the setter supports specifying hex codes. If unspecified, a radom
        color will automatically be assigned.
        """
        return self._color

    @color.setter
    def color(self, value):
        if value is None:
            self._color = Color(
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
        elif isinstance(value, str):
            value = value.replace('0x', '')
            self._color = Color.from_hex(value)
        else:
            assert isinstance(value, Color), 'Expected ladybug Color object for ' \
                'condition color. Got {}.'.format(type(value))
            self._color = value

    @property
    def protected(self):
        """Get or set a boolean for whether the condition is protected in THERM."""
        return self._protected

    @protected.setter
    def protected(self, value):
        try:
            self._protected = bool(value)
        except TypeError:
            raise TypeError(
                'Expected boolean for Condition.protected. Got {}.'.format(value))

    @property
    def project_tag(self):
        """Get or set a string for the condition's project name."""
        return self._project_tag

    @project_tag.setter
    def project_tag(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._project_tag = value

    @property
    def user_data(self):
        """Get or set an optional dictionary for additional meta data for this object.

        This will be None until it has been set. All keys and values of this
        dictionary should be of a standard Python type to ensure correct
        serialization of the object to/from JSON (eg. str, float, int, list, dict)
        """
        if self._user_data is not None:
            return self._user_data

    @user_data.setter
    def user_data(self, value):
        if value is not None:
            assert isinstance(value, dict), (
                'Expected dictionary for fairyfly_next_therm object user_data. '
                'Got {}.'.format(type(value)))
        self._user_data = value

    def duplicate(self):
        """Get a copy of this construction."""
        return self.__copy__()

    def __copy__(self):
        new_obj = self.__class__(self.identifier)
        new_obj._display_name = self._display_name
        new_obj._color = self._color
        new_obj._project_tag = self._project_tag
        new_obj._user_data = None if self._user_data is None else self._user_data.copy()
        return new_obj

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'Base THERM Condition:\n{}'.format(self.display_name)
