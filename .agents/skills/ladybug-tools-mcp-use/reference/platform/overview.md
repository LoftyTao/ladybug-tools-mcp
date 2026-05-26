# Platform Skill Overview

Use this category when the Agent needs Flowerpot, Grasshopper handoff, Web View Mode, or other platform integration surfaces that are not core model authoring.

## Preconditions

- Treat Flowerpot as an opaque handoff payload.
- Keep Rhino and Grasshopper geometry out of the public MCP geometry protocol.
- Use Web View Mode as a session preview strategy, not as a replacement for VisualizationSet artifacts or simulation tools.

## Common Scenarios

- Continue modeling from a Grasshopper-linked Garden.
- Prepare Flowerpot-based collaboration with Grasshopper components.
- Start Web View Mode for local session previews.
- Route real model work back to Garden, Honeybee, Dragonfly, Fairyfly, Energy, Radiance, or Visualization tools.

## Usual MCP Route

1. Confirm the platform context and Garden.
2. Resolve Flowerpot context or start Web View Mode.
3. Perform model edits through the core model/tool categories.
4. Return opaque Flowerpot or preview-session receipts without unpacking internal fields.

## Stop Conditions

- Stop before inventing Grasshopper-only MCP public tools.
- Stop before manually editing Flowerpot internals.
- Stop when the requested platform behavior is not public and route to the nearest supported Garden/model workflow.

## References

- `flowerpot-grasshopper-modeling.md`
- `web-view-mode.md`
