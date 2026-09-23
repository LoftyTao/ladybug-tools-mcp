# Flowerpot for Grasshopper

All seven components belong to one **Flowerpot** tab with one **Flowerpot**
subcategory. Like LBT-Grasshopper, components are grouped inside that subcategory
using `GH_Exposure`, mapped from `AdditionalHelpFromDocStrings` at build time.

| Group inside Flowerpot | Components | Handoff |
| --- | --- | --- |
| Garden (primary) | FP Create Garden, FP Garden List | Create or discover persistent Garden contexts |
| Models (secondary) | FP Honeybee Link, FP Dragonfly Link | Native Honeybee and Dragonfly models |
| Properties (tertiary) | FP Energy Properties Input, FP Radiance Properties Input | Existing Garden property dictionaries |
| HVAC (quarternary) | FP Detail HVAC | Native Ironbug HVAC systems |

Dragonfly Link is included in `1.2.2`; the previous `1.2.1` release contains six components.

Flowerpot components use the MCP version; they have no separate release number.
The generator copies `ladybug_tools_mcp.__version__` into every component script,
the saved `.ghuser` version label and the manifest. Package builds and installation
reject version mismatches. After changing the MCP version, regenerate the
Grasshopper assets before packaging.

## Runtime and installation

The installer copies prebuilt `.ghuser` files to the persistent Grasshopper
UserObjects directory. Restart Grasshopper after upgrading to refresh its
component library. Components already placed on a canvas retain their embedded
script; replace those instances to use a newer component version.

Installation updates only the files recorded as owned Flowerpot assets. It does
not reload Grasshopper's full plugin library. For upgrades, restart Rhino /
Grasshopper normally; calling `LoadExternalFiles` in a running session can
register unrelated plugins again.

Each script reads `LADYBUG_TOOLS_MCP_INSTALLATION` or the default installation
record and imports its installed `flowerpot.runtime`. The runtime delegates
Garden operations to that installation's persistent Python 3 worker. Development
source paths remain a fallback. Component scripts only adapt inputs and outputs;
Garden and SDK services own the domain behavior.

Flowerpot handles display as `Flowerpot : <name>` and connect directly between
FP components. Users do not need to unpack their internal fields.

## Model links

Honeybee Link and Dragonfly Link have the same inputs: `_flowerpot`, optional
`model_`, optional `_write`, and optional `follow_`. They return a native model,
the Flowerpot handle, a `changed` flag and a report.

- Leave `_write` disconnected or False to read the Garden base model or pass
  through a connected model.
- Toggle `_write` from False to True to persist the connected model once.
- Set `follow_` True to reload after external Garden model changes.

Honeybee and Dragonfly use independent base-model slots. Connect Dragonfly Link's
`model` output directly to native Dragonfly components, including their existing
deconstruction, visualization and Honeybee conversion workflows.

## Existing Garden and native components

Connect FP Garden List's `flowerpots` output to Grasshopper's **List Item** to
select an existing Garden, then connect that handle to the desired FP component.
No separate Open Garden component is needed. Continue using native Ladybug Tools
components for weather files, data collections, charts and model operations.

## Properties and detailed HVAC

Energy and Radiance Properties Input read existing Garden library objects.
They return property dictionaries and do not modify model assignments.

Detail HVAC takes `_flowerpot`, optional Ironbug model identifier `model_`, and
optional `follow_`. Its `hvac_system` output is a native
`Ironbug.HVAC.IB_HVACSystem` for **HB Detailed HVAC**. Handoff checks the allowed
serialized types, Ironbug assembly version `1.26.0`, native type and `ToJson`.
EMS and ElectricLoadCenter data are excluded from the HVAC snapshot.

## Building

Run `scripts/distribution/build_grasshopper.py` through Rhino Python 3. It reads
the component source interfaces and writes the assets under stable filenames
with a versioned manifest. Wheel builds reject stale
sources, missing components or mismatched checksums.
