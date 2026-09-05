"""OpenStudio writers for Ironbug performance-table objects."""

from __future__ import annotations

import math
from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import _set_if_present


def _table_values(node: ConsoleGraphNode, field_name: str) -> list[float]:
    values = node.fields.get(field_name)
    if not isinstance(values, list | tuple) or not values:
        raise ValueError(f"{node.source_class} {field_name} must be a non-empty list.")
    try:
        result = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{node.source_class} {field_name} must contain only numbers."
        ) from exc
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{node.source_class} {field_name} must contain finite numbers.")
    return result


def _table_variable_values(node: ConsoleGraphNode) -> list[float]:
    values = _table_values(node, "Values")
    if len(values) < 2:
        raise ValueError(
            "IB_TableIndependentVariable Values must contain at least two values."
        )
    if any(right <= left for left, right in zip(values, values[1:])):
        raise ValueError(
            "IB_TableIndependentVariable Values must be strictly ascending."
        )
    return values


def _table_variable_nodes(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[ConsoleGraphNode, ...]:
    variables = tuple(
        graph.node_by_identifier(str(child_identifier))
        for child_identifier in node.children
    )
    invalid = tuple(
        child.source_class
        for child in variables
        if child.source_class != "IB_TableIndependentVariable"
    )
    if invalid:
        raise ValueError(
            "IB_TableLookup variables must be IB_TableIndependentVariable objects; "
            f"got {', '.join(invalid)}."
        )
    if not variables:
        raise ValueError("IB_TableLookup requires at least one independent variable.")
    return variables


def _write_table_independent_variable(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    """Write one Table:IndependentVariable object."""

    name = str(node.fields.get("Name") or node.identifier)
    optional_variable = model.getTableIndependentVariableByName(name)
    if optional_variable.is_initialized():
        variable = optional_variable.get()
    else:
        variable = openstudio.model.TableIndependentVariable(model)
        variable.setName(name)
    values = _table_variable_values(node)
    variable.removeAllValues()
    variable.setValues(values)
    _set_if_present(variable.setInterpolationMethod, node, "InterpolationMethod", cast=str)
    _set_if_present(variable.setExtrapolationMethod, node, "ExtrapolationMethod", cast=str)
    _set_if_present(variable.setMinimumValue, node, "MinimumValue")
    _set_if_present(variable.setMaximumValue, node, "MaximumValue")
    _set_if_present(
        variable.setNormalizationReferenceValue,
        node,
        "NormalizationReferenceValue",
    )
    _set_if_present(variable.setUnitType, node, "UnitType", cast=str)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="curves",
        openstudio_type="OS:Table:IndependentVariable",
        name=name,
    )


def _write_table_lookup(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    """Write one Table:Lookup object and its independent-variable list."""

    variable_nodes = _table_variable_nodes(graph, node)
    variable_values = [_table_variable_values(variable) for variable in variable_nodes]
    output_values = _table_values(node, "OutputValues")
    expected_output_count = math.prod(len(values) for values in variable_values)
    if len(output_values) != expected_output_count:
        raise ValueError(
            "IB_TableLookup OutputValues count must equal the product of its "
            f"independent-variable dimensions ({expected_output_count}); "
            f"got {len(output_values)}."
        )

    name = str(node.fields.get("Name") or node.identifier)
    optional_lookup = model.getTableLookupByName(name)
    if optional_lookup.is_initialized():
        lookup = optional_lookup.get()
    else:
        lookup = openstudio.model.TableLookup(model)
        lookup.setName(name)
    lookup.removeAllIndependentVariables()
    for variable_node in variable_nodes:
        _write_table_independent_variable(openstudio, model, variable_node)
        variable_name = str(variable_node.fields.get("Name") or variable_node.identifier)
        optional_variable = model.getTableIndependentVariableByName(variable_name)
        if not optional_variable.is_initialized():
            raise ValueError(
                f"IB_TableLookup independent variable was not written: {variable_name}."
            )
        lookup.addIndependentVariable(optional_variable.get())
    lookup.removeAllOutputValues()
    lookup.setOutputValues(output_values)
    _set_if_present(lookup.setNormalizationMethod, node, "NormalizationMethod", cast=str)
    _set_if_present(lookup.setNormalizationDivisor, node, "NormalizationDivisor")
    _set_if_present(lookup.setMinimumOutput, node, "MinimumOutput")
    _set_if_present(lookup.setMaximumOutput, node, "MaximumOutput")
    _set_if_present(lookup.setOutputUnitType, node, "OutputUnitType", cast=str)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="curves",
        openstudio_type="OS:Table:Lookup",
        name=name,
    )


__all__ = [
    "_write_table_independent_variable",
    "_write_table_lookup",
]
