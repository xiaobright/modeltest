# rkllm_py (refactored)

This directory has been cleaned and reorganized.

## Structure

- `rkllm_sdk/`
- `tools/`
- `docs/`
- `requirements.txt`

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python tools/chat_demo.py ./Qwen3-1.7B_W8A8_RK3588.rkllm 1280 4096 --so ./librkllmrt.so
```

## Self-test

```bash
python tools/selftest.py --so ./librkllmrt.so --model ./Qwen3-1.7B_W8A8_RK3588.rkllm --run-tool-loop
```
