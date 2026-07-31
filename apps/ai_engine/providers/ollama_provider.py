from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from apps.ai_engine.providers.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str = "llama3.2") -> None:
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model

    def complete(self, prompt: str, **kwargs: Any) -> str:
        payload = {
            "model": kwargs.get("model") or self.model,
            "prompt": prompt,
            "stream": False,
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response") or ""
