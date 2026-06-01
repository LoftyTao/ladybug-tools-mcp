"""Garden runtime boundary for the Python Ironbug Console."""

from __future__ import annotations

from garden.ironbug_console.runtime import (
    OpenStudioRuntimeStatus,
    PythonConsoleRuntimeReport,
    check_openstudio_runtime,
)
from garden.ironbug_console.energy_runtime import (
    PYTHON_ONLY_ENV,
    PythonIronbugRuntimeUnsupported,
    prepare_python_only_energy_model,
)
from garden.ironbug_console.console_app import save_hvac_to_osm
from garden.ironbug_console.console_contracts import PythonConsoleFileResult
from garden.ironbug_console.console_payloads import (
    console_hvac_payload_to_specification,
    load_console_hvac_specification,
)
from garden.ironbug_console.console_model_payloads import (
    ConsoleModelSpecification,
    console_model_payload_to_specification,
    load_console_model_specification,
)
from garden.ironbug_console.openstudio_writer import (
    OpenStudioWriteResult,
    OpenStudioWrittenObject,
    write_console_model_specification_to_openstudio_model,
    write_detailed_hvac_specification_to_openstudio_model,
    write_first_family_to_openstudio_model,
)
from garden.ironbug_console.graph_decoder import (
    detailed_hvac_specification_to_console_graph,
    source_payload_to_console_graph,
)
from garden.ironbug_console.writer_registry import (
    FIRST_WRITER_FAMILY_NAMES,
    ConsoleWriterNodePlan,
    ConsoleWriterPlan,
    build_writer_family_plan,
)

__all__ = [
    "FIRST_WRITER_FAMILY_NAMES",
    "OpenStudioWriteResult",
    "OpenStudioWrittenObject",
    "OpenStudioRuntimeStatus",
    "PythonConsoleRuntimeReport",
    "PythonConsoleFileResult",
    "ConsoleModelSpecification",
    "PYTHON_ONLY_ENV",
    "PythonIronbugRuntimeUnsupported",
    "ConsoleWriterNodePlan",
    "ConsoleWriterPlan",
    "build_writer_family_plan",
    "check_openstudio_runtime",
    "console_hvac_payload_to_specification",
    "console_model_payload_to_specification",
    "detailed_hvac_specification_to_console_graph",
    "load_console_hvac_specification",
    "load_console_model_specification",
    "prepare_python_only_energy_model",
    "save_hvac_to_osm",
    "source_payload_to_console_graph",
    "write_console_model_specification_to_openstudio_model",
    "write_detailed_hvac_specification_to_openstudio_model",
    "write_first_family_to_openstudio_model",
]
