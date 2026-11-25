"""Model GBAS Properties."""

from .. import model as hb


class ModelGbasProperties(object):
    """GBAS Properties for Honeybee Model.

    Args:
        host: A honeybee_core Model object that hosts these properties.

    Properties:
        * host
    """

    ERROR_MAP = {
        "040101": "check_has_rooms",
        "040102": "check_room_floor_polygons",
    }

    def __init__(self, host):
        """Initialize ModelGbasProperties."""
        self._host = host

    @property
    def host(self):
        """Get the Model object hosting these properties."""
        return self._host

    def check_for_extension(self, raise_exception=True, detailed=False):
        """Check that the Model is valid for native GBAS DWG export.

        This process includes all relevant honeybee-core checks as well as checks
        that apply specifically to GBAS DWG export.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any errors are found. If False, this method will simply
                return a text string with all errors that were found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A text string with all errors that were found or a list if detailed is True.
            This string (or list) will be empty if no errors were found.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        tol = self.host.tolerance
        ang_tol = self.host.angle_tolerance

        msgs.append(self.host.check_all_duplicate_identifiers(False, detailed))
        msgs.append(self.host.check_planar(tol, False, detailed))
        msgs.append(self.host.check_self_intersecting(tol, False, detailed))
        msgs.append(self.host.check_degenerate_rooms(tol, False, detailed))
        msgs.append(self.host.check_sub_faces_valid(tol, ang_tol, False, detailed))
        msgs.append(self.host.check_sub_faces_overlapping(tol, False, detailed))
        msgs.append(self.host.check_rooms_solid(tol, ang_tol, False, detailed))
        msgs.append(self.host.check_upside_down_faces(ang_tol, False, detailed))
        msgs.append(self.host.check_room_volume_collisions(tol, False, detailed))
        msgs.append(self.host.check_missing_adjacencies(False, detailed))
        msgs.append(self.host.check_matching_adjacent_areas(tol, False, detailed))
        msgs.append(self.host.check_all_air_boundaries_adjacent(False, detailed))

        e_prop = self.host.properties.energy
        msgs.append(e_prop.check_interior_constructions_reversed(False, detailed))

        msgs.append(self.check_has_rooms(False, detailed))
        msgs.append(self.check_room_floor_polygons(False, detailed))

        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = "\n".join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_has_rooms(self, raise_exception=True, detailed=False):
        """Check whether the Model contains at least one Room.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if no rooms exist. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        if self.host.rooms:
            return [] if detailed else ""
        msg = 'Model "{}" requires at least one room for native GBAS DWG export.'.format(
            self.host.display_name
        )
        if raise_exception:
            raise ValueError(msg)
        full_msg = self.host._validation_message_child(
            msg,
            self.host,
            detailed,
            "040101",
            extension="GBAS",
            error_type="Model Missing Rooms",
        )
        if detailed:
            return [full_msg]
        return full_msg

    def check_room_floor_polygons(self, raise_exception=True, detailed=False):
        """Check whether every Room has a single horizontal floor boundary.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any Room lacks a single horizontal floor boundary. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with dictionaries if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for room in self.host.rooms:
            boundaries = hb.room_plan_boundaries(room)
            if len(boundaries) != 1:
                msg = (
                    'Room "{}" requires one horizontal floor boundary for native '
                    "GBAS DWG export (found {})."
                ).format(room.display_name, len(boundaries))
                full_msg = self.host._validation_message_child(
                    msg,
                    room,
                    detailed,
                    "040102",
                    extension="GBAS",
                    error_type="Invalid Room Floor Polygon",
                )
                msgs.append(full_msg)
        if detailed:
            return msgs
        full_msg = "\n".join(msgs)
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def to_dict(self):
        """Return Model GBAS properties as a dictionary."""
        return {"gbas": {"type": "ModelGbasProperties"}}

    def apply_properties_from_dict(self, data):
        """Apply the GBAS properties of a dictionary to the host Model of this object.

        Args:
            data: A dictionary representation of an entire honeybee-core Model.
                Note that this dictionary must have ModelGbasProperties in order
                for this method to successfully apply the GBAS properties.
        """
        assert "gbas" in data["properties"], (
            "Dictionary possesses no ModelGbasProperties."
        )

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return "Model GBAS Properties: [host: {}]".format(self.host.display_name)
