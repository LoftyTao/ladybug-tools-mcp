# 创建 Garden

## 用户意图

- 创建一个新的 Garden，并使用默认 Gardens root
- 创建一个新的 Garden，并指定明确落盘目录

## 模拟真实用户 Prompts

```text
在这个目录里创建一个新的 Garden，名字叫 Office Garden。
帮我新建一个 Garden，用这个确切路径作为 root directory。
请先搜索正确工具，再创建一个名为 Office Garden 的 Garden。
创建一个名为 Office Garden 的 Garden，使用默认位置。
```

## 已验证最短路径

1. `search_tools`
   查询词优先贴近用户动作，例如 `create garden`
2. `call_tool`
   调 `create_garden`

如果用户给的是已经存在的 Garden 路径，只是想确认项目状态，优先调用
`get_garden` 或 `get_base_honeybee_model`。不要在 Code Mode 里用 Python
`import os` / `os.path.exists` 做文件探测。

## deterministic-pass/candidate 默认 root 参数形态

2026-04-30 deterministic test covered MCP `create_garden` without `root_dir`
and `list_gardens` without `root_dir` sharing the default Gardens root. Treat
this as deterministic-pass/candidate until a real Agent run verifies the path.

```json
{
  "name": "create_garden",
  "arguments": {
    "name": "Office Garden"
  }
}
```

## 已验证最小参数形态：明确 root_dir

```json
{
  "name": "create_garden",
  "arguments": {
    "name": "Office Garden",
    "root_dir": "<exact garden root>"
  }
}
```

如果用户指定目录，必须使用 `root_dir`。`call_tool.arguments` 必须是完整对象；如果模型把它写成 `null` 或 `{}`，不要继续空参重试，应重建上面的完整 JSON。

## 成功判据

- `garden.json`
- `.gitignore`
- `summary_view.path`

## 额外注意

- 这是典型的 `search_tools -> call_tool(create_garden)` 场景
- root directory 越明确，越不容易漂移到错误路径
- 引导阶段如果没有用户指定目录，先让 `list_gardens` 和 `create_garden` 使用默认 Gardens root，不要把当前仓库目录当成默认搜索范围。
- 2026-04-30 supervised task 24 verified that `get_garden(garden_root=...)`
  is the compact read-only check for an existing Garden manifest.
- 低智能模型曾在全量 agent regression 中反复调用 `{"name":"create_garden","arguments":null}`。这是披露层失败，不是 Garden 服务层失败。
