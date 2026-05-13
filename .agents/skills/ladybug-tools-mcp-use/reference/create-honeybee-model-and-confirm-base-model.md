# 创建 Honeybee Model 并确认 Base Model

## 用户意图

- 在指定 Garden 里创建一个 Honeybee model，并确认它已经成为当前 base model

## 模拟真实用户 Prompts

```text
在这个 Garden 里创建一个名为 office_model 的 Honeybee model，然后确认当前 active base model。
帮我先建 Garden，再建一个 office_model，并用 get_base_honeybee_model 确认它是不是 base model。
请在这个确切 Garden root 下创建 office_model，然后告诉我当前激活的 base model 是什么。
```

## 已验证最短路径

1. `search_tools`
   查询 `create garden honeybee model`
2. `search_tools`
   查询 `get base model honeybee`
3. `call_tool(create_garden)`
4. `call_tool(create_honeybee_model)`
5. `call_tool(get_base_honeybee_model)`

## 已验证最小参数形态

```json
{
  "name": "create_honeybee_model",
  "arguments": {
    "identifier": "office_model",
    "garden_root": "<exact garden root>",
    "_set_base_": true,
    "_save_back_": true
  }
}
```

如需在创建时同步把完整对象接入 model，可额外传 `add_objects_`；当前已做 deterministic 验证，支持 `Room / Face / Aperture / Door / Shade` 的完整 Honeybee object dict。

## 成功判据

- `models/honeybee/office_model.hbjson`
- `garden.json` 中 `base_honeybee_model.model_identifier == "office_model"`
- `get_base_honeybee_model` 返回结果
- 最终回答中提到 `office_model`

## 避坑说明

- 确认 base model 时优先使用 `get_base_honeybee_model`
- 不要只依赖 `list_garden_models` 或 `list_gardens` 来替代 base model 确认
