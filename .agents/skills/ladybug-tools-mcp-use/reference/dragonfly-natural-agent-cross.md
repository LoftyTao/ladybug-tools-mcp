# Dragonfly Natural Agent Cross-Suite Candidate

Status: candidate, not a recommended shortest path.

2026-05-13 Codex ran the opt-in natural-language Dragonfly Agent cross-suite with MiniMax-M2.7 through OpenAI Agents Code Mode. The prompts deliberately used user-facing Chinese project language and did not tell the Agent which domain MCP tools to call.

Verified progress:

- The suite now starts from a clean Garden artifact on each run.
- Large district modeling and project-editing workflows can close in retained runs with multi-building, multi-story, multi-room Dragonfly models, ContextShade objects, Story add/remove, adjacency solve/reset, Room2D cleanup, and validation.
- Deterministic regression coverage now accepts common natural handoff shapes: full upstream create-result envelopes, object targets where model targets are expected, Garden-relative DFJSON paths, plural object types, floor/geometry aliases, ContextShade 2D vertices and `face3d_list`, Story `floor_z`, `story_identifier`, `typical` Story type, Building natural count/type hints, Room2D `geometry` / `room_geometry`, UWG `target`, window `wwr`, and low-cost `return_object_dict=false` where compact output is valid.

Observed remaining failures:

- MiniMax repeatedly splits long Dragonfly work across isolated `execute` blocks, then references variables such as `garden_root`, `df_model`, or intermediate targets that do not persist.
- The model keeps inventing adjacent natural parameter names after each repair, for example `floor_height` / `num_of_floors` on Building creation, `room_identifier` / `polygon` on Room2D creation, `target` on adjacency solve, and `shading_parameter_target` on shading apply.
- Some failures happen after the persisted Garden is already functionally useful. Inspect `agent_metrics.json`, `intervention_report.json`, and the Garden state before deciding whether the owner is service schema, tool description, test budget, or Agent behavior.

Current guidance:

- Do not keep widening the public schema for every invented field. Add service/schema tolerance only when the shape is a stable natural synonym, maps cleanly to SDK-backed behavior, and reduces repeated calls without hiding unsupported capability.
- Classify Code Mode variable reuse across `execute` blocks as Agent behavior / skill-reference cost unless a compact target handoff is missing from the MCP response.
- For future retained evidence, prefer segmented natural scenarios or a stronger Code Mode reminder rather than one large all-in-one prompt.
- For Web View demo mode on an existing Dragonfly Garden, treat the path as targeted retained evidence: one upfront object inventory, reuse Building/Story/Room2D/model targets, do each maintenance action once, rely on Web View auto-refresh, and avoid persistent vtk.js export unless the user asks for a reusable asset.

MiMo-specific finding:

- `mimo-v2.5-pro` requires Chat Completions tool-call histories to replay provider `reasoning_content`. The OpenAI Agents SDK harness now enables a MiMo-only replay hook alongside the SDK's default DeepSeek replay path.
- MiMo may emit numeric JSON fields as strings on outer Code Mode discovery calls. Code Mode `search.limit` now accepts numeric strings and coerces them before search.
- A retained MiMo run of the first fused district-modeling scenario completed functionally after the above fixes and the `edit_dragonfly_room2d` `floor_z` / string-identifier recovery. Metrics: 6 model requests, 7 outer tools, 50 inner MCP calls, 113,973 total tokens. This is functional evidence for the first scenario only; the full natural suite remains candidate.
- A retained MiMo Dragonfly Web View demo-mode run passed after bounded natural aliases and auto-refresh wording were added. Metrics: 6 model requests, 7 outer tools, 14 inner MCP calls, no repeated MCP tools, 133,093 total tokens, and 10 Web View session preview steps. This verifies targeted demo mode only; the full sequential Dragonfly natural suite remains candidate.
