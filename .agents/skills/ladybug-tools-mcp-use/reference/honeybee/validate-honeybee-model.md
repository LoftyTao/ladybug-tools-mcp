# Validate Honeybee Model

Use this after Honeybee create, edit, remove, relate, or transform operations to confirm the persisted Garden model is still valid.

## Preconditions

- A Garden exists with a base Honeybee Model, or an explicit `model_target` is available.
- The user wants model validity, not a full HBJSON export.

## MCP Route

1. Call `honeybee_validate_model` with `garden_root`.
2. If validating a non-base model, include `model_target`.
3. Read `summary_view`, `is_valid`, `valid`, and `issues`.
4. If invalid, choose the next repair tool based on the issue type instead of rerunning validation.

## Code Mode Pattern

```python
validation = await call_tool("honeybee_validate_model", {
    "garden_root": garden_root
})

return {
    "is_valid": validation["summary_view"]["is_valid"],
    "issue_count": validation["summary_view"].get("issue_count", 0),
    "issues": validation.get("issues", [])[:5]
}
```

## Success Criteria

- `summary_view.is_valid == true` or `is_valid == true`.
- Issue counts are zero for final successful modeling workflows.
- The validation target is the intended model.

## Stop Conditions

- Do not treat a successful tool call as a valid model; inspect the validation fields.
- Do not request or return full model bodies for routine validation.
- Store long evidence, run identifiers, and metrics in LLM-Wiki, not in this Skill reference.
