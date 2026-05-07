# Energy Result Diagnosis

Use this path when the user asks why an Energy result looks high, low, or suspicious and wants an evidence-first explanation.

## 用户意图

- 解释 annual Energy run 的 EUI 或分项负荷为什么异常
- 区分 weather、window / envelope、schedule / program、setpoint、HVAC assumptions 等可能原因
- 在改模型前保存 baseline，并把建议说成可验证假设

## 已验证最短路径

1. 确认或创建一个独立 Garden 和 Energy-ready model。
2. `validate_honeybee_model` 确认模型有效。
3. `create_garden_version` 保存当前 baseline。
4. `search_epw_map -> download_epw` 获取 Garden-managed weather target。
5. `start_energy_run -> get_energy_run` 启动并轮询 annual run；完成后 `list_energy_run_outputs -> read_energy_eui`。
6. `search_honeybee_model_objects` 检查 rooms、apertures、faces 和 `room_energy_properties`。
7. `search_energy_library_objects` 或 Garden library search 检查 construction / program / schedule 资源摘要。
8. 回复时先列证据，再给最小下一步测试；不要把单次 run 写成因果证明。

## 成功判据

- 结果来自 completed `energy_run` ledger，而不是猜测或静态模板。
- 天气 target、EUI 分项、房间 Energy 属性、窗墙比或主要 aperture 证据都可追溯。
- baseline Garden version 已保存，且最终 Garden 状态 clean。
- 建议明确标为 hypothesis，例如“最值得先测的是降低 WWR 到 0.30 后重跑”，而不是“已证明窗是原因”。

## 高价值边界

- 单次 annual run 只能支持证据排序，不能证明唯一因果。
- IdealAir 或模板 HVAC 会影响解释边界；不要把结果当成真实设备选型报告。
- 如果用户问“是不是窗太大”，先查 window ratio / aperture area / construction，再决定它是否比 schedule 或 weather 更可疑。
- 如果 schedule 看起来是普通办公程序，不要为了迎合问题把它描述成主因。

## Evidence

- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch C Task 14 first functionally passed but wrote to shared `D:\Desktop\Codex\gardens\test-garden`, so it was rejected as formal campaign evidence under the repo artifact rule.
- 2026-05-01 Task 14 retry passed in `tests/.artifacts/natural_agent_broad_20_20260501_batch_c/task14_retry/garden`: the Agent created an independent Garden, ran `task14_retry_baseline`, read EUI total `207.176` with Heating `102.431`, inspected weather, generic construction/program resources, a `0.75` WWR aperture, saved baseline version `d640c6b0a0bc056a20c83245780c8fb4a4146f1c`, and recommended lowering WWR as the first A/B test while explicitly preserving causality uncertainty.
