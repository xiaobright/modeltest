# RKLLM Python QuickStart

当前目录已经重构为三层：

- `rkllm_sdk/native.py`：原生 ctypes 绑定层（贴近 C API）。
- `rkllm_sdk/client.py`：会话化客户端层（同步、流式、异步、工具调用）。
- `tools/`：可直接运行的脚本（交互 Demo、自检）。

## 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

## 2. 运行交互 Demo

```bash
python tools/chat_demo.py <model_path> <max_new_tokens> <max_context_len> --so <so_path>
```

示例：

```bash
python tools/chat_demo.py ./Qwen3-1.7B_W8A8_RK3588.rkllm 1280 4096 --so ./librkllmrt.so
```

流式输出：

```bash
python tools/chat_demo.py <model_path> <max_new_tokens> <max_context_len> --so <so_path> --stream
```

保留 KV 历史：

```bash
python tools/chat_demo.py <model_path> <max_new_tokens> <max_context_len> --so <so_path> --keep-history
```

## 3. 运行自检脚本

```bash
python tools/selftest.py --so <so_path> --model <model_path> --max-new-tokens 256 --max-context-len 4096
```

额外验证工具调用闭环：

```bash
python tools/selftest.py --so <so_path> --model <model_path> --run-tool-loop
```
