# Garden Properties Library

Use this path when a reusable Honeybee Energy or Honeybee Radiance SDK object should persist as its own Garden resource instead of only passing as an inline dict.

Prefer direct Garden-saving create tools when they exist. A direct create call with `garden_root` and `return_object_dict=false` saves the object and returns a reusable `target` without asking the Agent to carry a full SDK `object_dict` into `save_garden_properties_library_object`. For schedules, add `include_data=false` unless the user specifically needs the annual time-series `data`.

For project-specific Radiance modifiers, use the deterministic-pass `create_radiance_opaque_modifier`, `create_radiance_mirror_modifier`, `create_radiance_metal_modifier`, `create_radiance_trans_modifier`, or `create_radiance_glass_modifier` direct-save tools instead of the fallback save path. For IES light fixtures, use the Agent-verified `create_radiance_luminaire` direct-save path.

## Shortest Verified Path

1. `search_tools`
   - Query: `create schedule Garden Properties Library reusable target`
2. Create the final reusable object with a direct Garden-saving create tool when available.
   - Example: `create_schedule_ruleset`
   - Required:
     - `garden_root`
     - `include_data=false` for schedules when time-series inspection is not needed
     - `return_object_dict=false`
3. Reuse the returned `target` with `get_garden_properties_library_object`, or discover it later with `search_garden_properties_library_objects`.
4. Use `save_garden_properties_library_object` only as a fallback when you already have an existing full `object_dict` and no direct Garden-saving create path is available.
   - Required:
     - `garden_root`
     - `domain`: `honeybee_energy` or `honeybee_radiance`
    - `object_family`: `schedule`, `schedule_type_limit`, `program_type`, `load`, `hvac`, `material`, `construction`, `construction_set`, `modifier`, `modifier_set`, or `luminaire`
     - `object_dict`

## Minimal Example

```json
{
  "name": "create_schedule_ruleset",
  "arguments": {
    "garden_root": "D:/path/to/Garden",
    "identifier": "Office Occupancy",
    "default_day_schedule": "<create_schedule_day.object_dict>",
    "include_data": false,
    "return_object_dict": false
  }
}
```

Fallback only:

```json
{
  "name": "save_garden_properties_library_object",
  "arguments": {
    "garden_root": "D:/path/to/Garden",
    "domain": "honeybee_energy",
    "object_family": "schedule",
    "object_dict": "<existing full SDK object_dict>"
  }
}
```

## Expected Output

- `target`: a `garden_properties_library_object` target with `domain`, `object_family`, `identifier`, and Garden-relative `path`.
- `object_dict`: omitted on direct create paths when `return_object_dict=false`; returned by the generic fallback save because it validates the supplied SDK object dictionary.
- `persistence_receipt.persisted_path`: the saved resource path under `libraries/...`.
- `search_garden_properties_library_objects.matches[]`: reusable targets for later get or assignment workflows.

## Notes

- This is the Garden project object library. Do not call it `Garden-local`; Garden already implies locality.
- SDK standards library search remains separate: use `search_energy_library_objects` and `search_radiance_library_objects` when the user only needs built-in standards identifiers.
- Model objects like Room, Face, Aperture, Door, and Shade remain embedded in Garden model files; they do not use this library path.
- Search accepts `object_type` as a deterministic Agent-friendly synonym for `object_family`, matching the Energy and Radiance standards-library search behavior. Keep using `object_family` in deliberate hand-written calls.
- Search accepts `identifier_contains` as an Agent-friendly query alias. Deliberate calls should still prefer `query` or `identifier`.
- Avoid the fallback save path for objects that can be created directly into Garden. It increases token use because the Agent must receive and resend the full SDK `object_dict`.
- 2026-04-27 Agent smoke verified the direct schedule path with `create_schedule_ruleset(garden_root, include_data=false, return_object_dict=false)` followed by `search_garden_properties_library_objects`: 4 real MCP calls, no generic save, no repeated tools, 13,321 total tokens.
- 2026-04-30 supervised external Agent task 13 verified a reusable schedule library save and search under the stable `energy_results` suite. It closed in `68.010s`; repeated schedule creation remains a cost smell, but the final path no longer requires a full schedule `object_dict` handoff.
- 2026-04-29 deterministic tests verify direct Garden-saving Radiance modifier create tools. They are deterministic-pass until an external Agent smoke promotes the path.
- 2026-04-29 Agent smoke verified the direct Garden-saving Radiance Luminaire / IES path with `create_radiance_luminaire(garden_root, ies_content, return_object_dict=false)` followed by `search_garden_properties_library_objects(object_family=luminaire)`.
