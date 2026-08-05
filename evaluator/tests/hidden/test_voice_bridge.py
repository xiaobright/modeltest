#!/usr/bin/env python3
"""F4: voice/assistant must fetch current session in the same flow as sensitive context."""
from __future__ import annotations

import ast
import os
import re
import unittest
from pathlib import Path


_CURRENT_RE = re.compile(
    r"/api/v3/session/current|session/current|fetch_current_session|get_current_session",
    re.I,
)
_CONTEXT_RE = re.compile(
    r"context/chat|GATEWAY_CHAT_CONTEXT|fetch_gateway_chat_context|build_gateway_context_params",
    re.I,
)
_FLOW_RE = re.compile(
    r"(session/current|fetch_current_session|get_current_session)"
    r"[\s\S]{0,800}"
    r"(context/chat|GATEWAY_CHAT_CONTEXT|fetch_gateway_chat_context|build_gateway_context_params)"
    r"|"
    r"(context/chat|GATEWAY_CHAT_CONTEXT|fetch_gateway_chat_context|build_gateway_context_params)"
    r"[\s\S]{0,800}"
    r"(session/current|fetch_current_session|get_current_session)",
    re.I,
)


def _function_spans(text: str) -> list[tuple[str, str]]:
    """Return (name, source) for top-level and nested functions via AST."""
    out: list[tuple[str, str]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            src = ast.get_source_segment(text, node) or ""
            if src:
                out.append((node.name, src))
    return out


class VoiceBridgeTest(unittest.TestCase):
    def test_voice_fetches_current_session_before_sensitive_context(self):
        project = Path(os.environ["PROJECT_DIR"]).resolve()
        voice_py = project / "voice" / "voice_assistant_integrated.py"
        self.assertTrue(voice_py.is_file(), "voice_assistant_integrated.py missing")
        text = voice_py.read_text(encoding="utf-8", errors="replace")

        has_current = bool(_CURRENT_RE.search(text))
        self.assertTrue(
            has_current,
            "voice module must reference /api/v3/session/current (or fetch_current_session / "
            "get_current_session) so sensitive context can use an explicit session_id",
        )

        # Require a single flow: current-session fetch linked to context request.
        # Accept: (1) regex proximity in file, or (2) same function body contains both.
        flow_ok = bool(_FLOW_RE.search(text))
        same_fn = False
        for _name, src in _function_spans(text):
            if _CURRENT_RE.search(src) and _CONTEXT_RE.search(src):
                same_fn = True
                break

        self.assertTrue(
            flow_ok or same_fn,
            "voice must obtain current session in the *same request flow* that builds/fetches "
            "sensitive chat context (same function, or clear sequential call chain). "
            "Merely mentioning session_id elsewhere is not enough.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
