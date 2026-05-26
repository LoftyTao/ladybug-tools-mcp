# Flowerpot Grasshopper Modeling Handoff

Use this when the user refers to the current Grasshopper model, a Flowerpot handoff, or a Garden created by Flowerpot/Grasshopper components.

## Preconditions

- Flowerpot is opaque. Do not inspect or explain `payload_context` directly.
- Rhino and Grasshopper are platform surfaces; MCP modeling continues through Garden and typed targets.
- `FP Honeybee Link` must have written or followed a Garden base Honeybee Model before Honeybee edits can continue.

## Grasshopper Component Roles

- `FP Garden List`: lists existing Gardens and outputs Flowerpots.
- `FP Create Garden`: creates a Garden and outputs a Flowerpot.
- `FP Honeybee Link`: writes the Grasshopper Honeybee Model into the Flowerpot Garden or follows the current Garden base model.
- `FP Energy Properties Input`: reads existing Garden Energy Properties Library resources.
- `FP Radiance Properties Input`: reads existing Garden Radiance Properties Library resources.

The main collaboration chain is `FP Garden List` or `FP Create Garden` into `FP Honeybee Link`. Properties Input components are readers; they do not create resources or apply them to the model.

## MCP Route

1. If the user says "current Grasshopper model" and the Garden is known, prefer `flowerpot_get_active_context(garden_root=...)`.
2. If an opaque Flowerpot is provided, call `flowerpot_get(flowerpot=<opaque Flowerpot>)`.
3. Read `summary_view.garden_root`.
4. Continue with normal Garden tools such as `honeybee_create_room`, `honeybee_search_model_objects`, and `honeybee_validate_model`.

## Code Mode Pattern

```python
context = await call_tool("flowerpot_get", {"flowerpot": flowerpot})
garden_root = context["summary_view"]["garden_root"]

room = await call_tool("honeybee_create_room", {
    "garden_root": garden_root,
    "identifier": "agent_room_from_flowerpot",
    "x_dim": 4,
    "y_dim": 5,
    "height": 3
})

rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room"
})
validation = await call_tool("honeybee_validate_model", {"garden_root": garden_root})
```

## Success Criteria

- Agent never manually reads or interprets `flowerpot["payload_context"]`.
- `flowerpot_get` or active context resolution returns `summary_view.garden_root`.
- New Honeybee edits write to the Garden base model linked by Grasshopper.
- `honeybee_validate_model.is_valid == true` when the workflow claims a valid model.
- `FP Honeybee Link follow_=True` can observe Garden model changes after the component has loaded the current runtime.

## Stop Conditions

- Do not ask the user to split Flowerpot internals.
- `flowerpot_get(..., include_body=True)` still does not return full model bodies; continue through Garden tools.
- Reuse existing Flowerpot handoff records unless the user explicitly asks for `force_new=true`.
- Prefer MCP for Program, HVAC, Construction, Modifier, batch windows/shades, search, validation, and summaries; prefer Grasshopper for component wiring and visual geometry sliders.
