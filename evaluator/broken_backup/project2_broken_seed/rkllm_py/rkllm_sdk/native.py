from __future__ import annotations

"""Low-level RKLLM ctypes bindings.

This module is a direct Python translation of core definitions from `rkllm.h`.
It intentionally stays close to the C ABI and avoids high-level business logic.
"""

import ctypes
from ctypes import (
    POINTER,
    Structure,
    Union,
    byref,
    c_bool,
    c_char_p,
    c_float,
    c_int,
    c_int8,
    c_int32,
    c_size_t,
    c_uint8,
    c_uint32,
    c_void_p,
)
from enum import IntEnum
from typing import Any, Callable, Optional, Sequence, Tuple


class LLMCallState(IntEnum):
    """State values returned by RKLLM callback."""

    RKLLM_RUN_NORMAL = 0
    RKLLM_RUN_WAITING = 1
    RKLLM_RUN_FINISH = 2
    RKLLM_RUN_ERROR = 3


class RKLLMInputType(IntEnum):
    """Input data mode for RKLLMInput union."""

    RKLLM_INPUT_PROMPT = 0
    RKLLM_INPUT_TOKEN = 1
    RKLLM_INPUT_EMBED = 2
    RKLLM_INPUT_MULTIMODAL = 3


class RKLLMInferMode(IntEnum):
    """Inference mode values."""

    RKLLM_INFER_GENERATE = 0
    RKLLM_INFER_GET_LAST_HIDDEN_LAYER = 1
    RKLLM_INFER_GET_LOGITS = 2


CPU0 = 1 << 0
CPU1 = 1 << 1
CPU2 = 1 << 2
CPU3 = 1 << 3
CPU4 = 1 << 4
CPU5 = 1 << 5
CPU6 = 1 << 6
CPU7 = 1 << 7


class RKLLMExtendParam(Structure):
    """Extra runtime parameters for RKLLM."""

    _fields_ = [
        ("base_domain_id", c_int32),
        ("embed_flash", c_int8),
        ("enabled_cpus_num", c_int8),
        ("enabled_cpus_mask", c_uint32),
        ("n_batch", c_uint8),
        ("use_cross_attn", c_int8),
        ("reserved", c_uint8 * 104),
    ]


class RKLLMParam(Structure):
    """Model initialization parameters."""

    _fields_ = [
        ("model_path", c_char_p),
        ("max_context_len", c_int32),
        ("max_new_tokens", c_int32),
        ("top_k", c_int32),
        ("n_keep", c_int32),
        ("top_p", c_float),
        ("temperature", c_float),
        ("repeat_penalty", c_float),
        ("frequency_penalty", c_float),
        ("presence_penalty", c_float),
        ("mirostat", c_int32),
        ("mirostat_tau", c_float),
        ("mirostat_eta", c_float),
        ("skip_special_token", c_bool),
        ("is_async", c_bool),
        ("img_start", c_char_p),
        ("img_end", c_char_p),
        ("img_content", c_char_p),
        ("extend_param", RKLLMExtendParam),
    ]


class RKLLMLoraAdapter(Structure):
    """LoRA adapter information."""

    _fields_ = [
        ("lora_adapter_path", c_char_p),
        ("lora_adapter_name", c_char_p),
        ("scale", c_float),
    ]


class RKLLMEmbedInput(Structure):
    """Embedding input buffer."""

    _fields_ = [("embed", POINTER(c_float)), ("n_tokens", c_size_t)]


class RKLLMTokenInput(Structure):
    """Token-id input buffer."""

    _fields_ = [("input_ids", POINTER(c_int32)), ("n_tokens", c_size_t)]


class RKLLMMultiModalInput(Structure):
    """Multimodal prompt+image embedding input."""

    _fields_ = [
        ("prompt", c_char_p),
        ("image_embed", POINTER(c_float)),
        ("n_image_tokens", c_size_t),
        ("n_image", c_size_t),
        ("image_width", c_size_t),
        ("image_height", c_size_t),
    ]


class RKLLMInputData(Union):
    """Union payload for RKLLMInput."""

    _fields_ = [
        ("prompt_input", c_char_p),
        ("embed_input", RKLLMEmbedInput),
        ("token_input", RKLLMTokenInput),
        ("multimodal_input", RKLLMMultiModalInput),
    ]


class RKLLMInput(Structure):
    """Unified inference input."""

    _anonymous_ = ("data",)
    _fields_ = [
        ("role", c_char_p),
        ("enable_thinking", c_bool),
        ("input_type", c_int),
        ("data", RKLLMInputData),
    ]


class RKLLMLoraParam(Structure):
    """Runtime LoRA selection parameters."""

    _fields_ = [("lora_adapter_name", c_char_p)]


class RKLLMPromptCacheParam(Structure):
    """Prompt cache save parameters."""

    _fields_ = [("save_prompt_cache", c_int), ("prompt_cache_path", c_char_p)]


class RKLLMCrossAttnParam(Structure):
    """Cross attention cache pointers for decoder."""

    _fields_ = [
        ("encoder_k_cache", POINTER(c_float)),
        ("encoder_v_cache", POINTER(c_float)),
        ("encoder_mask", POINTER(c_float)),
        ("encoder_pos", POINTER(c_int32)),
        ("num_tokens", c_int),
    ]


class RKLLMInferParam(Structure):
    """Inference invocation parameters."""

    _fields_ = [
        ("mode", c_int),
        ("lora_params", POINTER(RKLLMLoraParam)),
        ("prompt_cache_params", POINTER(RKLLMPromptCacheParam)),
        ("keep_history", c_int),
    ]


class RKLLMResultLastHiddenLayer(Structure):
    """Hidden states result payload."""

    _fields_ = [
        ("hidden_states", POINTER(c_float)),
        ("embd_size", c_int),
        ("num_tokens", c_int),
    ]


class RKLLMResultLogits(Structure):
    """Logits result payload."""

    _fields_ = [
        ("logits", POINTER(c_float)),
        ("vocab_size", c_int),
        ("num_tokens", c_int),
    ]


class RKLLMPerfStat(Structure):
    """Performance stats from native runtime."""

    _fields_ = [
        ("prefill_time_ms", c_float),
        ("prefill_tokens", c_int),
        ("generate_time_ms", c_float),
        ("generate_tokens", c_int),
        ("memory_usage_mb", c_float),
    ]


class RKLLMResult(Structure):
    """Raw callback result payload."""

    _fields_ = [
        ("text", c_char_p),
        ("token_id", c_int32),
        ("last_hidden_layer", RKLLMResultLastHiddenLayer),
        ("logits", RKLLMResultLogits),
        ("perf", RKLLMPerfStat),
    ]


LLMResultCallback = ctypes.CFUNCTYPE(c_int, POINTER(RKLLMResult), c_void_p, c_int)


class RKLLM:
    """Minimal low-level wrapper around librkllmrt.so.

    This class mirrors the C API one-to-one.
    Return values are native status codes and are not converted to exceptions.
    """

    def __init__(self, so_path: str):
        """Load shared library and bind symbols.

        Args:
            so_path: Absolute or relative path to `librkllmrt.so`.
        """
        self._lib = ctypes.CDLL(so_path)
        self._handle = c_void_p()
        self._callback_ref: Optional[Any] = None
        self._bind_symbols()

    @property
    def handle(self) -> c_void_p:
        """Return native model handle."""
        return self._handle

    @property
    def lib(self):
        """Return loaded CDLL instance for advanced usage."""
        return self._lib

    def _bind_symbols(self) -> None:
        self._lib.rkllm_createDefaultParam.argtypes = []
        self._lib.rkllm_createDefaultParam.restype = RKLLMParam

        self._lib.rkllm_init.argtypes = [POINTER(c_void_p), POINTER(RKLLMParam), LLMResultCallback]
        self._lib.rkllm_init.restype = c_int

        self._lib.rkllm_load_lora.argtypes = [c_void_p, POINTER(RKLLMLoraAdapter)]
        self._lib.rkllm_load_lora.restype = c_int

        self._lib.rkllm_load_prompt_cache.argtypes = [c_void_p, c_char_p]
        self._lib.rkllm_load_prompt_cache.restype = c_int

        self._lib.rkllm_release_prompt_cache.argtypes = [c_void_p]
        self._lib.rkllm_release_prompt_cache.restype = c_int

        self._lib.rkllm_destroy.argtypes = [c_void_p]
        self._lib.rkllm_destroy.restype = c_int

        self._lib.rkllm_run.argtypes = [c_void_p, POINTER(RKLLMInput), POINTER(RKLLMInferParam), c_void_p]
        self._lib.rkllm_run.restype = c_int

        self._lib.rkllm_run_async.argtypes = [c_void_p, POINTER(RKLLMInput), POINTER(RKLLMInferParam), c_void_p]
        self._lib.rkllm_run_async.restype = c_int

        self._lib.rkllm_abort.argtypes = [c_void_p]
        self._lib.rkllm_abort.restype = c_int

        self._lib.rkllm_is_running.argtypes = [c_void_p]
        self._lib.rkllm_is_running.restype = c_int

        self._lib.rkllm_clear_kv_cache.argtypes = [c_void_p, c_int, POINTER(c_int), POINTER(c_int)]
        self._lib.rkllm_clear_kv_cache.restype = c_int

        self._lib.rkllm_get_kv_cache_size.argtypes = [c_void_p, POINTER(c_int)]
        self._lib.rkllm_get_kv_cache_size.restype = c_int

        self._lib.rkllm_set_chat_template.argtypes = [c_void_p, c_char_p, c_char_p, c_char_p]
        self._lib.rkllm_set_chat_template.restype = c_int

        self._lib.rkllm_set_function_tools.argtypes = [c_void_p, c_char_p, c_char_p, c_char_p]
        self._lib.rkllm_set_function_tools.restype = c_int

        self._lib.rkllm_set_cross_attn_params.argtypes = [c_void_p, POINTER(RKLLMCrossAttnParam)]
        self._lib.rkllm_set_cross_attn_params.restype = c_int

    def create_default_param(self) -> RKLLMParam:
        """Return default-initialized `RKLLMParam` from native runtime."""
        return self._lib.rkllm_createDefaultParam()

    def init(self, param: RKLLMParam, callback: Callable[[Any, c_void_p, int], int]) -> int:
        """Initialize runtime.

        Args:
            param: Initialized model parameter struct.
            callback: Callback function compatible with `LLMResultCallback`.

        Returns:
            0 on success, non-zero on failure.
        """
        self._callback_ref = LLMResultCallback(callback)
        return self._lib.rkllm_init(byref(self._handle), byref(param), self._callback_ref)

    def load_lora(self, adapter: RKLLMLoraAdapter) -> int:
        """Load LoRA adapter into native runtime."""
        return self._lib.rkllm_load_lora(self._handle, byref(adapter))

    def load_prompt_cache(self, prompt_cache_path: str) -> int:
        """Load prompt cache file from path."""
        return self._lib.rkllm_load_prompt_cache(self._handle, prompt_cache_path.encode("utf-8"))

    def release_prompt_cache(self) -> int:
        """Release loaded prompt cache resources."""
        return self._lib.rkllm_release_prompt_cache(self._handle)

    def destroy(self) -> int:
        """Destroy native runtime handle and release resources."""
        if not self._handle:
            return 0
        ret = self._lib.rkllm_destroy(self._handle)
        self._handle = c_void_p()
        return ret

    def run(self, rkllm_input: RKLLMInput, infer_param: Optional[RKLLMInferParam] = None, userdata: Optional[int] = None) -> int:
        """Run synchronous inference.

        Returns:
            0 on success, non-zero on failure.
        """
        infer_ptr = byref(infer_param) if infer_param is not None else None
        user_ptr = c_void_p(userdata) if userdata is not None else None
        return self._lib.rkllm_run(self._handle, byref(rkllm_input), infer_ptr, user_ptr)

    def run_async(self, rkllm_input: RKLLMInput, infer_param: Optional[RKLLMInferParam] = None, userdata: Optional[int] = None) -> int:
        """Run asynchronous inference."""
        infer_ptr = byref(infer_param) if infer_param is not None else None
        user_ptr = c_void_p(userdata) if userdata is not None else None
        return self._lib.rkllm_run_async(self._handle, byref(rkllm_input), infer_ptr, user_ptr)

    def abort(self) -> int:
        """Abort current inference."""
        return self._lib.rkllm_abort(self._handle)

    def is_running(self) -> int:
        """Check whether runtime is currently running."""
        return self._lib.rkllm_is_running(self._handle)

    def clear_kv_cache(
        self,
        keep_system_prompt: int = 1,
        start_pos: Optional[Sequence[int]] = None,
        end_pos: Optional[Sequence[int]] = None,
    ) -> int:
        """Clear full or partial KV cache.

        Args:
            keep_system_prompt: Preserve system prompt cache when full-clear.
            start_pos: Start indices for each batch item.
            end_pos: End indices for each batch item.

        Returns:
            0 on success, non-zero on failure.
        """
        start_arr = None
        end_arr = None
        if start_pos is not None or end_pos is not None:
            if start_pos is None or end_pos is None:
                raise ValueError("start_pos and end_pos must be both None or both provided")
            if len(start_pos) != len(end_pos):
                raise ValueError("start_pos and end_pos length mismatch")
            start_arr = (c_int * len(start_pos))(*start_pos)
            end_arr = (c_int * len(end_pos))(*end_pos)
        return self._lib.rkllm_clear_kv_cache(self._handle, keep_system_prompt, start_arr, end_arr)

    def get_kv_cache_size(self, n_batch: int) -> Tuple[int, list[int]]:
        """Get KV cache size per batch.

        Args:
            n_batch: Number of batch slots.

        Returns:
            Tuple of `(ret_code, cache_size_list)`.
        """
        if n_batch <= 0:
            raise ValueError("n_batch must be > 0")
        out = (c_int * n_batch)()
        ret = self._lib.rkllm_get_kv_cache_size(self._handle, out)
        return ret, list(out)

    def set_chat_template(self, system_prompt: str, prompt_prefix: str, prompt_postfix: str) -> int:
        """Set runtime chat template fields."""
        return self._lib.rkllm_set_chat_template(
            self._handle,
            system_prompt.encode("utf-8"),
            prompt_prefix.encode("utf-8"),
            prompt_postfix.encode("utf-8"),
        )

    def set_function_tools(self, system_prompt: str, tools_json: str, tool_response_str: str) -> int:
        """Set function-calling tool schema and tool response marker."""
        return self._lib.rkllm_set_function_tools(
            self._handle,
            system_prompt.encode("utf-8"),
            tools_json.encode("utf-8"),
            tool_response_str.encode("utf-8"),
        )

    def set_cross_attn_params(self, cross_attn_param: RKLLMCrossAttnParam) -> int:
        """Bind cross-attention encoder caches for decoder inference."""
        return self._lib.rkllm_set_cross_attn_params(self._handle, byref(cross_attn_param))

    @staticmethod
    def build_prompt_input(text: str, role: str = "user", enable_thinking: bool = False):
        """Build `RKLLMInput` prompt payload.

        Returns:
            `(rkllm_input, keepalive_dict)` where keepalive_dict holds bytes references
            that should remain alive while native runtime reads input.
        """
        role_b = role.encode("utf-8")
        prompt_b = text.encode("utf-8")

        rkllm_input = RKLLMInput()
        rkllm_input.role = role_b
        rkllm_input.enable_thinking = enable_thinking
        rkllm_input.input_type = RKLLMInputType.RKLLM_INPUT_PROMPT
        rkllm_input.prompt_input = prompt_b

        keepalive = {"role": role_b, "prompt": prompt_b}
        return rkllm_input, keepalive


__all__ = [
    "CPU0",
    "CPU1",
    "CPU2",
    "CPU3",
    "CPU4",
    "CPU5",
    "CPU6",
    "CPU7",
    "LLMCallState",
    "RKLLMInputType",
    "RKLLMInferMode",
    "RKLLMExtendParam",
    "RKLLMParam",
    "RKLLMLoraAdapter",
    "RKLLMEmbedInput",
    "RKLLMTokenInput",
    "RKLLMMultiModalInput",
    "RKLLMInput",
    "RKLLMLoraParam",
    "RKLLMPromptCacheParam",
    "RKLLMCrossAttnParam",
    "RKLLMInferParam",
    "RKLLMResultLastHiddenLayer",
    "RKLLMResultLogits",
    "RKLLMPerfStat",
    "RKLLMResult",
    "LLMResultCallback",
    "RKLLM",
]
