from __future__ import annotations

import argparse
import pathlib
import signal
import sys

# Allow direct execution: python tools/chat_demo.py ...
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rkllm_sdk import (
    LLMConfig,
    LLMCallState,
    RKLLMClient,
    SamplingConfig,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python RKLLM demo (ctypes binding)")
    parser.add_argument("model_path", help="Path to .rkllm model")
    parser.add_argument("max_new_tokens", type=int, help="Maximum generated tokens")
    parser.add_argument("max_context_len", type=int, help="Maximum context length")
    parser.add_argument(
        "--so",
        default="librkllmrt.so",
        help="Path to RKLLM runtime shared library (default: librkllmrt.so)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use stream_generate to print incremental chunks",
    )
    parser.add_argument(
        "--keep-history",
        action="store_true",
        help="Enable runtime keep_history mode",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config = LLMConfig(
        model_path=args.model_path,
        max_new_tokens=args.max_new_tokens,
        max_context_len=args.max_context_len,
        sampling=SamplingConfig(
            top_k=1,
            top_p=0.95,
            temperature=0.8,
            repeat_penalty=1.1,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        ),
        skip_special_token=True,
        base_domain_id=0,
        embed_flash=1,
    )

    print("rkllm init start")
    client = RKLLMClient(args.so, config)
    session = client.create_session(session_id="demo", keep_history=args.keep_history)
    print("rkllm init success")

    def exit_handler(signum, frame):
        del signum, frame
        print("程序即将退出")
        client.destroy()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, exit_handler)

    pre_input = [
        "现有一笼子，里面有鸡和兔子若干只，数一数，共有头14个，腿38条，求鸡和兔子各有多少只？",
        "有28位小朋友排成一行,从左边开始数第10位是学豆,从右边开始数他是第几位?",
    ]

    print("\\n**********************可输入以下问题对应序号获取回答/或自定义输入********************\\n")
    for i, text in enumerate(pre_input):
        print(f"[{i}] {text}")
    print("\\n*************************************************************************\\n")

    # LoRA usage example:
    # client.load_lora("qwen0.5b_fp16_lora.rkllm", "test", scale=1.0)

    # Prompt cache usage example:
    # client.load_prompt_cache("./prompt_cache.bin")

    try:
        while True:
            input_str = input("\\nuser: ")
            if input_str == "exit":
                break

            if input_str == "clear":
                session.clear(keep_system_prompt=True)
                continue

            if input_str.isdigit():
                idx = int(input_str)
                if 0 <= idx < len(pre_input):
                    input_str = pre_input[idx]
                    print(input_str)

            print("robot: ", end="", flush=True)
            if args.stream:
                for chunk in session.stream_generate(input_str):
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                    if chunk.state == LLMCallState.RKLLM_RUN_ERROR:
                        print("\\nrun error")
                        break
                print("")
            else:
                result = session.generate(input_str)
                print(result.text)
    finally:
        client.destroy()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
