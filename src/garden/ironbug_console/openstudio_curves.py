"""Curve writers for the Python Ironbug OpenStudio writer."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import _set_if_present


_CURVE_SPECS: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...]]] = {
    "IB_CurveBicubic": (
        "CurveBicubic",
        "OS:Curve:Bicubic",
        (
            "Coefficient1Constant",
            "Coefficient2x",
            "Coefficient3xPOW2",
            "Coefficient4y",
            "Coefficient5yPOW2",
            "Coefficient6xTIMESY",
            "Coefficient7xPOW3",
            "Coefficient8yPOW3",
            "Coefficient9xPOW2TIMESY",
            "Coefficient10xTIMESYPOW2",
        ),
        ("MinimumValueofx", "MaximumValueofx", "MinimumValueofy", "MaximumValueofy"),
    ),
    "IB_CurveBiquadratic": (
        "CurveBiquadratic",
        "OS:Curve:Biquadratic",
        (
            "Coefficient1Constant",
            "Coefficient2x",
            "Coefficient3xPOW2",
            "Coefficient4y",
            "Coefficient5yPOW2",
            "Coefficient6xTIMESY",
        ),
        ("MinimumValueofx", "MaximumValueofx", "MinimumValueofy", "MaximumValueofy"),
    ),
    "IB_CurveCubic": (
        "CurveCubic",
        "OS:Curve:Cubic",
        (
            "Coefficient1Constant",
            "Coefficient2x",
            "Coefficient3xPOW2",
            "Coefficient4xPOW3",
        ),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveExponent": (
        "CurveExponent",
        "OS:Curve:Exponent",
        (
            "Coefficient1Constant",
            "Coefficient2Constant",
            "Coefficient3Constant",
        ),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveDoubleExponentialDecay": (
        "CurveDoubleExponentialDecay",
        "OS:Curve:DoubleExponentialDecay",
        (
            "Coefficient1C1",
            "Coefficient2C2",
            "Coefficient3C3",
            "Coefficient4C4",
            "Coefficient5C5",
        ),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveExponentialDecay": (
        "CurveExponentialDecay",
        "OS:Curve:ExponentialDecay",
        ("Coefficient1C1", "Coefficient2C2", "Coefficient3C3"),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveExponentialSkewNormal": (
        "CurveExponentialSkewNormal",
        "OS:Curve:ExponentialSkewNormal",
        ("Coefficient1C1", "Coefficient2C2", "Coefficient3C3", "Coefficient4C4"),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveFanPressureRise": (
        "CurveFanPressureRise",
        "OS:Curve:FanPressureRise",
        (
            "Coefficient1C1",
            "Coefficient2C2",
            "Coefficient3C3",
            "Coefficient4C4",
        ),
        (
            "MinimumValueofPsm",
            "MaximumValueofPsm",
            "MinimumValueofQfan",
            "MaximumValueofQfan",
        ),
    ),
    "IB_CurveFunctionalPressureDrop": (
        "CurveFunctionalPressureDrop",
        "OS:Curve:Functional:PressureDrop",
        (
            "Diameter",
            "MinorLossCoefficient",
            "Length",
            "Roughness",
            "FixedFrictionFactor",
        ),
        (),
    ),
    "IB_CurveLinear": (
        "CurveLinear",
        "OS:Curve:Linear",
        ("Coefficient1Constant", "Coefficient2x"),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveQuadratic": (
        "CurveQuadratic",
        "OS:Curve:Quadratic",
        ("Coefficient1Constant", "Coefficient2x", "Coefficient3xPOW2"),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveQuadLinear": (
        "CurveQuadLinear",
        "OS:Curve:QuadLinear",
        (
            "Coefficient1Constant",
            "Coefficient2w",
            "Coefficient3x",
            "Coefficient4y",
            "Coefficient5z",
        ),
        (
            "MinimumValueofw",
            "MaximumValueofw",
            "MinimumValueofx",
            "MaximumValueofx",
            "MinimumValueofy",
            "MaximumValueofy",
            "MinimumValueofz",
            "MaximumValueofz",
        ),
    ),
    "IB_CurveQuadraticLinear": (
        "CurveQuadraticLinear",
        "OS:Curve:QuadraticLinear",
        (
            "Coefficient1Constant",
            "Coefficient2x",
            "Coefficient3xPOW2",
            "Coefficient4y",
            "Coefficient5xTIMESY",
            "Coefficient6xPOW2TIMESY",
        ),
        (
            "MinimumValueofx",
            "MaximumValueofx",
            "MinimumValueofy",
            "MaximumValueofy",
        ),
    ),
    "IB_CurveQuartic": (
        "CurveQuartic",
        "OS:Curve:Quartic",
        (
            "Coefficient1Constant",
            "Coefficient2x",
            "Coefficient3xPOW2",
            "Coefficient4xPOW3",
            "Coefficient5xPOW4",
        ),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveQuintLinear": (
        "CurveQuintLinear",
        "OS:Curve:QuintLinear",
        (
            "Coefficient1Constant",
            "Coefficient2v",
            "Coefficient3w",
            "Coefficient4x",
            "Coefficient5y",
            "Coefficient6z",
        ),
        (
            "MinimumValueofv",
            "MaximumValueofv",
            "MinimumValueofw",
            "MaximumValueofw",
            "MinimumValueofx",
            "MaximumValueofx",
            "MinimumValueofy",
            "MaximumValueofy",
            "MinimumValueofz",
            "MaximumValueofz",
        ),
    ),
    "IB_CurveRectangularHyperbola1": (
        "CurveRectangularHyperbola1",
        "OS:Curve:RectangularHyperbola1",
        ("Coefficient1C1", "Coefficient2C2", "Coefficient3C3"),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveRectangularHyperbola2": (
        "CurveRectangularHyperbola2",
        "OS:Curve:RectangularHyperbola2",
        ("Coefficient1C1", "Coefficient2C2", "Coefficient3C3"),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveSigmoid": (
        "CurveSigmoid",
        "OS:Curve:Sigmoid",
        (
            "Coefficient1C1",
            "Coefficient2C2",
            "Coefficient3C3",
            "Coefficient4C4",
            "Coefficient5C5",
        ),
        ("MinimumValueofx", "MaximumValueofx"),
    ),
    "IB_CurveTriquadratic": (
        "CurveTriquadratic",
        "OS:Curve:Triquadratic",
        (
            "Coefficient1Constant",
            "Coefficient2xPOW2",
            "Coefficient3x",
            "Coefficient4yPOW2",
            "Coefficient5y",
            "Coefficient6zPOW2",
            "Coefficient7z",
            "Coefficient8xPOW2TIMESYPOW2",
            "Coefficient9xTIMESY",
            "Coefficient10xTIMESYPOW2",
            "Coefficient11xPOW2TIMESY",
            "Coefficient12xPOW2TIMESZPOW2",
            "Coefficient13xTIMESZ",
            "Coefficient14xTIMESZPOW2",
            "Coefficient15xPOW2TIMESZ",
            "Coefficient16yPOW2TIMESZPOW2",
            "Coefficient17yTIMESZ",
            "Coefficient18yTIMESZPOW2",
            "Coefficient19yPOW2TIMESZ",
            "Coefficient20xPOW2TIMESYPOW2TIMESZPOW2",
            "Coefficient21xPOW2TIMESYPOW2TIMESZ",
            "Coefficient22xPOW2TIMESYTIMESZPOW2",
            "Coefficient23xTIMESYPOW2TIMESZPOW2",
            "Coefficient24xPOW2TIMESYTIMESZ",
            "Coefficient25xTIMESYPOW2TIMESZ",
            "Coefficient26xTIMESYTIMESZPOW2",
            "Coefficient27xTIMESYTIMESZ",
        ),
        (
            "MinimumValueofx",
            "MaximumValueofx",
            "MinimumValueofy",
            "MaximumValueofy",
            "MinimumValueofz",
            "MaximumValueofz",
        ),
    ),
}


def _write_curve(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    curve_class_name, openstudio_type, coefficient_fields, limit_fields = (
        _CURVE_SPECS[node.source_class]
    )
    name = str(node.fields.get("Name") or node.identifier)
    optional_curve = getattr(model, f"get{curve_class_name}ByName")(name)
    if optional_curve.is_initialized():
        curve = optional_curve.get()
    else:
        curve = getattr(openstudio.model, curve_class_name)(model)
        curve.setName(name)
    for field_name in coefficient_fields:
        _set_if_present(getattr(curve, f"set{field_name}"), node, field_name)
    for field_name in limit_fields:
        _set_if_present(getattr(curve, f"set{field_name}"), node, field_name)
    minimum_curve_output_setter = getattr(curve, "setMinimumCurveOutput", None)
    if minimum_curve_output_setter is not None:
        _set_if_present(minimum_curve_output_setter, node, "MinimumCurveOutput")
    maximum_curve_output_setter = getattr(curve, "setMaximumCurveOutput", None)
    if maximum_curve_output_setter is not None:
        _set_if_present(maximum_curve_output_setter, node, "MaximumCurveOutput")
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="curves",
        openstudio_type=openstudio_type,
        name=name,
    )


