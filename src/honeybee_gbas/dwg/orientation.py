from collections import Counter
from math import radians, sin

from honeybee.facetype import face_types, get_type_from_normal


def vertical_wall_normal(normal, angle_tolerance):
    return abs(normal.z) <= sin(radians(min(1.0, angle_tolerance))) + 1e-12


def face_role(face, angle_tolerance, suggested=None):
    declared = str(face.type)
    if (declared == "RoofCeiling" and str(face.boundary_condition) == "Outdoors"
            and vertical_wall_normal(face.normal, angle_tolerance)
            and (suggested or get_type_from_normal(face.normal)) == face_types.wall):
        return "Wall"
    return declared


def orientation_model(model):
    counts = Counter()
    changes = {}
    for room in model.rooms:
        for face in room.faces:
            suggested = get_type_from_normal(face.normal)
            role = face_role(face, model.angle_tolerance, suggested)
            counts[str(face.type), str(suggested), role] += 1
            if role != str(face.type):
                changes[face.identifier] = {"source_room": room.identifier, "declared": str(face.type), "effective": role,
                                            "normal": list(face.normal), "boundary_condition": str(face.boundary_condition)}
    audit = {"classifier": "honeybee.facetype.get_type_from_normal", "vertical_tolerance_degrees": min(1.0, model.angle_tolerance),
             "policy": "SDK normal suggestion; confirmed vertical outdoor roofs become walls; preserve authored slopes and reciprocal boundaries",
             "counts": [{"declared": d, "suggested": s, "effective": e, "faces": n} for (d, s, e), n in sorted(counts.items())],
             "reclassified": changes}
    if not changes:
        return model, audit
    working = model.duplicate()
    for face in working.faces_by_identifier(changes):
        components = (face, *face.sub_faces)
        constructions = [c.properties.energy.construction for c in components]
        face.type = face_types.wall
        for component, construction in zip(components, constructions):
            component.properties.energy.construction = construction
    return working, audit
