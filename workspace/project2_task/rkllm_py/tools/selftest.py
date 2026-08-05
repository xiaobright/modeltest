from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import traceback
from typing import Any

# Allow direct execution: python tools/selftest.py ...
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rkllm_sdk.client import LLMConfig, RKLLMClient, SamplingConfig
from rkllm_sdk.native import LLMCallState, RKLLM, RKLLMInferMode, RKLLMInferParam


class TestFailure(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TestFailure(message)


def test_lowlevel_sync(so: str, model: str, max_new_tokens: int, max_context_len: int) -> None:
    chunks: list[str] = []

    def cb(result_ptr, userdata, state):
        del userdata
        if state == LLMCallState.RKLLM_RUN_NORMAL and result_ptr and result_ptr.contents.text:
            chunks.append(result_ptr.contents.text.decode("utf-8", errors="ignore"))
        return 0

    llm = RKLLM(so)
    try:
        param = llm.create_default_param()
        param.model_path = model.encode("utf-8")
        param.max_new_tokens = max_new_tokens
        param.max_context_len = max_context_len
        param.top_k = 1
        param.top_p = 0.95
        param.temperature = 0.8
        param.repeat_penalty = 1.1
        param.frequency_penalty = 0.0
        param.presence_penalty = 0.0
        param.skip_special_token = True
        param.extend_param.base_domain_id = 0
        param.extend_param.embed_flash = 1

        ret = llm.init(param, cb)
        require(ret == 0, f"lowlevel init failed: {ret}")

        inp, keepalive = llm.build_prompt_input("你好", role="user")
        infer = RKLLMInferParam()
        infer.mode = RKLLMInferMode.RKLLM_INFER_GENERATE
        infer.keep_history = 0
        ret = llm.run(inp, infer)
        _ = keepalive
        require(ret == 0, f"lowlevel run failed: {ret}")
        require(len("".join(chunks)) > 0, "lowlevel callback did not produce text")
    finally:
        llm.destroy()


async def test_highlevel_async(client: RKLLMClient) -> None:
    session = client.create_session("async-test", keep_history=False)

    result = await session.async_generate("你好")
    require(len(result.text) > 0, "async_generate returned empty text")

    text = ""
    async for chunk in session.async_stream_generate("请用一句话自我介绍"):
        text += chunk.text
    require(len(text) > 0, "async_stream_generate returned empty stream text")


def test_highlevel_sync_and_stream(client: RKLLMClient) -> None:
    session = client.create_session("sync-test", keep_history=False)

    result = session.generate("你好")
    require(len(result.text) > 0, "generate returned empty text")
    require(result.request_id != "", "generate request_id is empty")

    stream_text = ""
    saw_finish = False
    for chunk in session.stream_generate("请说一句简短的话"):
        stream_text += chunk.text
        if chunk.state == LLMCallState.RKLLM_RUN_FINISH:
            saw_finish = True
    require(len(stream_text) > 0, "stream_generate returned empty text")
    require(saw_finish or len(stream_text) > 0, "stream_generate has no finish and no text")


def test_tool_registration_and_dispatch(client: RKLLMClient) -> None:
    def add(a: int, b: int) -> int:
        return a + b

    client.configure_function_tools(system_prompt="You are a helpful assistant.")
    client.register_tool_from_callable(add, description="Add two integers")

    parsed = client.extract_tool_calls("<tool_call>{\"name\":\"add\",\"arguments\":{\"a\":2,\"b\":3}}</tool_call>")
    require(len(parsed) == 1, "extract_tool_calls failed")
    exec_res = client.execute_tool_call(parsed[0])
    require(exec_res.result == 5, "execute_tool_call result mismatch")


def test_tool_loop_optional(client: RKLLMClient) -> None:
    def get_current_temperature(location: str, unit: str = "celsius") -> dict[str, Any]:
        return {"temperature": 26.1, "location": location, "unit": unit}

    client.configure_function_tools(system_prompt="You are a helpful assistant.")
    client.register_tool_from_callable(get_current_temperature)

    session = client.create_session("tool-loop", keep_history=False)
    result = session.generate_with_tools("请调用工具查询北京当前温度", max_rounds=3)
    require(len(result.text) > 0, "generate_with_tools returned empty text")


def run_test(name: str, fn) -> tuple[str, bool, str]:
    try:
        fn()
        return name, True, "PASS"
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        return name, False, f"FAIL: {exc}\n{tb}"


def main() -> int:
    parser = argparse.ArgumentParser(description="RKLLM wrapper self-test on board")
    parser.add_argument("--so", required=True, help="Path to librkllmrt.so")
    parser.add_argument("--model", required=True, help="Path to .rkllm model")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--max-context-len", type=int, default=4096)
    parser.add_argument("--run-tool-loop", action="store_true", help="Run end-to-end tool loop test")
    args = parser.parse_args()

    results: list[tuple[str, bool, str]] = []

    results.append(
        run_test(
            "lowlevel_sync",
            lambda: test_lowlevel_sync(args.so, args.model, args.max_new_tokens, args.max_context_len),
        )
    )

    cfg = LLMConfig(
        model_path=args.model,
        max_new_tokens=args.max_new_tokens,
        max_context_len=args.max_context_len,
        sampling=SamplingConfig(top_k=1, top_p=0.95, temperature=0.8, repeat_penalty=1.1),
        skip_special_token=True,
        base_domain_id=0,
        embed_flash=1,
    )

    with RKLLMClient(args.so, cfg) as client:
        results.append(run_test("highlevel_sync_and_stream", lambda: test_highlevel_sync_and_stream(client)))
        results.append(run_test("tool_registration_dispatch", lambda: test_tool_registration_and_dispatch(client)))
        results.append(run_test("highlevel_async", lambda: asyncio.run(test_highlevel_async(client))))
        if args.run_tool_loop:
            results.append(run_test("tool_loop_optional", lambda: test_tool_loop_optional(client)))

    print("\n===== RKLLM SELFTEST REPORT =====")
    failed = 0
    for name, ok, msg in results:
        print(f"[{name}] {msg.splitlines()[0]}")
        if not ok:
            failed += 1
            print(msg)

    summary = {
        "total": len(results),
        "failed": failed,
        "passed": len(results) - failed,
        "status": "PASS" if failed == 0 else "FAIL",
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
