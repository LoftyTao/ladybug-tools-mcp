# Grasshopper Components

This folder contains standalone GHPython/IronPython adapter code for Ladybug Tools MCP Flowerpot workflows.

These files are not part of the `ladybug_tools_mcp` service package. They should stay thin:

- collect Grasshopper inputs
- import and reload the local Flowerpot runtime
- delegate formal work to the Python 3 worker in the project `.venv`
- return opaque `flowerpot` values and compact `report` dictionaries

The MCP service remains the source of Flowerpot, Garden, and Honeybee behavior.

## Flowerpot Display

Grasshopper outputs use a lightweight `FlowerpotHandle`. It is intentionally
not a `dict` subclass, so Grasshopper should not expand it into dictionary keys
in panels. It displays as `Flowerpot : <name>` while exposing `to_dict()`,
`get()`, and `[]` access for downstream FP components.

## Flowerpot Worker

There is no user-facing `transport_` input. The components follow the previous
Ladybug Tools MCP Grasshopper design: a GHPython/IronPython shell calls
`flowerpot.runtime`, and that runtime keeps a repository `.venv`
Python worker session alive for domain actions such as `garden_create`,
`garden_list`, or `honeybee_link`. The first call starts Python; later calls
reuse the same worker process instead of paying the CLI startup cost again.

The Python 3 worker and runtime helpers live in `src/flowerpot/`. They import
the formal Garden, Flowerpot, and Honeybee services and return JSON that the GH
runtime reshapes into component outputs.

## Properties Input Components

`FP Energy Properties Input` and `FP Radiance Properties Input` read existing
Garden Properties Library objects from a Flowerpot Garden. They do not create
properties and do not apply properties to the current Honeybee Model.

Inputs are `_flowerpot`, `_type`, `value_`, and `follow_`. Outputs are only
`property` and `report`. The `property` output is a Ladybug Tools object dict or
a list of object dicts. Internal Garden targets are kept inside `report.details`
for MCP/Agent context.

`FP Honeybee Link` does not expose `display_name_`; it uses the connected
Honeybee model's own display name or identifier. Its `_write` input is optional:
leave it disconnected or False to pass through/read, and set it True only when
you want to persist the connected model into the Flowerpot Garden.

When `follow_` is True, the component schedules a lightweight Grasshopper
refresh poll. The poll checks the followed Garden/base model file signature and
expires the component only after that file changes, so external Agent/MCP writes
can appear in Grasshopper without manually toggling the component. A currently
open Grasshopper document must solve the component once with the updated script
loaded before the automatic polling loop exists.

Each component script bootstraps `sys.path` before importing helpers. By default it points at this repository root:

```text
D:\Desktop\Codex\rec-ladybug-tools-mcp
```

If the repository moves, set the `LADYBUG_TOOLS_MCP_ROOT` environment variable
or edit `_DEVELOPMENT_SRC_ROOT` at the top of each component script. The
bootstrap adds:

- `src`
