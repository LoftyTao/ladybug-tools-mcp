# Tool Naming And Disclosure

Use this reference when maintaining Ladybug Tools MCP tool names, tags,
descriptions, or Skill references.

## Runtime Rule

- Discover with Code Mode `search` or `get_schema`; call domain tools only inside
  `execute` through `await call_tool(...)`.
- The returned public name is complete and case-sensitive. Its uppercase
  ecosystem prefix is part of the name; do not prepend or derive another name.
- Preserve existing lowercase `snake_case` arguments, business parameters,
  typed target fields, and returned handoff fields.
- After a reconnect or deployment rename, load the current connection and
  rediscover the directory before calling a tool. If discovery omits a needed
  tool, stop and report the missing current surface.

## Prefix Map

- `LB_`: config and visualization; `HB_`: Honeybee; `EP_`: Energy;
  `RAD_`: Radiance; `FF_`: Fairyfly; `IB_`: Ironbug; `DF_`: Dragonfly core.
- `DF_des_`, `DF_grid_`, `DF_uwg_`, and `DF_urbanopt_` identify Dragonfly
  subfamilies; `FP_` is Flowerpot; `GD_` is Garden;
  `GD_library_` is Garden libraries; `GD_web_view_` is Web View.
- Examples: `GD_create`, `HB_create_room`, `EP_start_simulation`,
  `RAD_create_sensor_grid`, `FF_start_simulation`, `IB_zone_equipment_ptac`,
  `DF_model`, `DF_grid_substation`, `DF_des_thermal_connector`,
  `DF_uwg_start_simulation`, `DF_urbanopt_prepare_project`,
  `GD_library_search_garden_properties_objects`, and
  `GD_web_view_start_mode`.

## Sync Rule

Update complete names in every Code Mode snippet, tool list, and name
suggestion while leaving SDK fields, business function names, target types, and
paths unchanged.
Use only names returned by current discovery; do not retain compatibility
aliases or infer a local name.
