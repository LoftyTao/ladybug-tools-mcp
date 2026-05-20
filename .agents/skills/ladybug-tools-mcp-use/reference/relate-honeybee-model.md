# Relate Honeybee Model

本路径已通过本地 deterministic tests 验证，包括默认 intersect、单侧单子面复制、显式 full repair、多子面复制、无法修复 mismatch 删除，以及克隆 subface 时的 Radiance dynamic state geometry 同步。2026-04-24 的 OpenAI Agents focused smoke 已验证 `search -> await call_tool(relate_honeybee_model, _relation_mode_=explicit_relate_full)` 可执行。

## 适用场景

- 用户要求重新处理 Honeybee 房间关系、相邻面或 adjacency。
- 导入、编辑或几何变换后，需要显式运行关系处理再校验。

## 最短路径

1. `search` 查询 `relate honeybee model solve adjacency`。
2. 调用 `relate_honeybee_model`。
3. 继续调用 `validate_honeybee_model` 检查关系处理后的模型。

## 成功调用形态

```json
{
  "name": "relate_honeybee_model",
  "arguments": {
    "garden_root": "tests/.artifacts/.../garden",
    "_relation_mode_": "solve_adjacency"
  }
}
```

## 显式 full repair 路径

仅当用户明确要求覆盖、批量修复、删除不匹配子面或清理旧 adjacency 时使用。Agent 已验证最短路径先检索 `explicit full repair overwrite cleanup remove mismatched subfaces clone missing adjacency`，再按下面形态调用：

```json
{
  "name": "relate_honeybee_model",
  "arguments": {
    "garden_root": "tests/.artifacts/.../garden",
    "_relation_mode_": "explicit_relate_full"
  }
}
```

`explicit_relate_full` 会自动启用：

- `merge_coplanar = true`
- `overwrite = true`
- `remove_mismatched_sub_faces = true`
- `relationship_cleanup = true`
- `subface_mismatch_policy = "clone_missing"`

## 当前边界

- 默认 `intersect_ = true`，也就是先切分 Room Face，再求解相邻关系；它可能改变房间面几何，运行后必须 `validate_honeybee_model`。
- 默认 `subface_mismatch_policy_ = "clone_single"`，只处理一侧正好 1 个 Aperture / Door、另一侧 0 个 subface 的情况。
- 默认 `remove_mismatched_sub_faces_ = false`，不要为了通过关系求解自动删除用户已经建好的 Aperture / Door。
- 多子面修复、覆盖已有 adjacency、删除无法修复的 mismatched subfaces 和 relationship cleanup 只属于显式 full repair，不属于默认内置后处理。
- Create / Edit / Remove / Operate 的内置后处理会在工作副本上复用 `auto_relate_intersect_clone_single`。内置路径失败只返回 warning 并保存原始动作；显式 `relate_honeybee_model` 仍会把 SDK 关系失败暴露成工具失败。
- 子面复制使用 Honeybee SDK 的 `Face.project_and_add_sub_face` 投影接口。Radiance dynamic state geometry 没有同一个宿主投影接口，因此服务层只同步投影 state 的 `shades / vmtx_geometry / dmtx_geometry`，并在 warnings 中披露。

## 已观察失败模式

- 低智能模型曾在同一 prompt 中连续执行 `relate_honeybee_model` 和 `validate_honeybee_model` 时，把第二次及后续 `call_tool.arguments` 丢成 `{}`，触发 `garden_root` 缺失。当前 disclosure 应把关键调用拆短，并明确“不要用空 arguments”；后续可继续优化 tool description 或示例格式。
