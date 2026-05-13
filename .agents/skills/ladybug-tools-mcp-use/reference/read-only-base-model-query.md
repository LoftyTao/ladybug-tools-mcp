# 只读查询 Base Model

## 用户意图

- 回答当前有哪些 model、active base model 是什么，但不要扩展成新的写入动作

## 模拟真实用户 Prompts

```text
检查这个 Garden 里有哪些 model，并告诉我当前 active base model。
请用 get_base_honeybee_model 回答这个 Garden 当前的 base model 是什么。
不要修改模型，只告诉我这个 Garden 里当前的 model 和 active base model。
```

## 已验证推荐路径

1. 如果场景前面需要写入，先完成必要写入动作
2. 明确调用 `get_base_honeybee_model`
3. 再组织回答

## 主断言

- 是否发生 `get_base_honeybee_model`
- `garden.json` 中的 `base_honeybee_model`
- 最终回答是否提到目标 model identifier

## Prompt 约束

- 给出确切 Garden 根目录
- 明确写出 `use get_base_honeybee_model`
- 明确要求不要修改模型

## 避坑说明

- 如果 prompt 过于模糊，模型可能继续调用写工具而不是停在只读链
- 只读问题要避免写成泛化描述，例如 `check the model`
