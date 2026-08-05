# RKLLM Python API Reference

本文档描述重构后的两个核心模块。

## 模块

- `rkllm_sdk.native`
- `rkllm_sdk.client`

## rkllm_sdk.native

目标：保持与底层 runtime ABI 对齐，接口返回原始状态码。

核心类型：

- `LLMCallState`
- `RKLLMInferMode`
- `RKLLMParam`
- `RKLLMInput`
- `RKLLMInferParam`
- `RKLLMResult`

核心类：

- `RKLLM`

主要方法：

- `create_default_param()`
- `init(param, callback)`
- `run(rkllm_input, infer_param=None, userdata=None)`
- `run_async(...)`
- `load_lora(adapter)`
- `load_prompt_cache(path)`
- `release_prompt_cache()`
- `clear_kv_cache(keep_system_prompt=1, start_pos=None, end_pos=None)`
- `get_kv_cache_size(n_batch)`
- `set_chat_template(system_prompt, prompt_prefix, prompt_postfix)`
- `set_function_tools(system_prompt, tools_json, tool_response_str)`
- `destroy()`

## rkllm_sdk.client

目标：提供更易用的会话与工具调用封装，失败时抛 `RKLLMError`。

核心数据类：

- `SamplingConfig`
- `LLMConfig`
- `Message`
- `GenerationChunk`
- `GenerationResult`
- `ToolCall`
- `ToolExecutionResult`

核心类：

- `RKLLMClient`
- `RKLLMSession`

高频方法：

- `RKLLMClient.create_session()`
- `RKLLMClient.generate()`
- `RKLLMClient.stream_generate()`
- `RKLLMClient.async_generate()`
- `RKLLMClient.async_stream_generate()`
- `RKLLMClient.register_tool_from_callable()`
- `RKLLMSession.generate()`
- `RKLLMSession.stream_generate()`
- `RKLLMSession.generate_with_tools()`
- `RKLLMSession.clear()`
