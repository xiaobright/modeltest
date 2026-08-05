# RKLLM Python Client Guide

本指南面向日常业务代码，建议优先使用 `rkllm_sdk.client`。

## 最小示例

```python
from rkllm_sdk.client import LLMConfig, RKLLMClient, SamplingConfig

cfg = LLMConfig(
    model_path="./model.rkllm",
    max_new_tokens=512,
    max_context_len=4096,
    sampling=SamplingConfig(top_k=1, top_p=0.95, temperature=0.8),
)

with RKLLMClient("./librkllmrt.so", cfg) as client:
    session = client.create_session("demo", keep_history=False)
    result = session.generate("你好")
    print(result.text)
```

## 工具调用闭环

1. `configure_function_tools()` 设置系统提示与工具响应标签。
2. `register_tool_from_callable()` 注册 Python 函数。
3. `generate_with_tools()` 自动执行“解析 -> 执行 -> 回灌”。

## 什么时候用 native 层

- 你需要严格贴合底层 C 接口行为。
- 你要调试状态码、结构体和 callback 行为。
- 你需要把异常处理策略交给上层业务自行决定。
