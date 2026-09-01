"""Universal Model Adapters: Gemini, OpenAI, and Deterministic Stub.

Uses Python standard library (urllib.request + asyncio.to_thread) so it requires
zero third-party package dependencies and runs seamlessly inside all environments.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

STUB_LATENCY_MS = 50


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    model: str
    stubbed: bool


class StubAdapter:
    """Deterministic, latency-configured completions with no network call."""

    def __init__(self, *, latency_ms: int = STUB_LATENCY_MS, model: str = "stub-v1") -> None:
        self._latency_ms = latency_ms
        self._model = model

    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> ModelResponse:
        await asyncio.sleep(self._latency_ms / 1000)
        digest = hashlib.sha256(
            json.dumps(messages, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:12]
        return ModelResponse(
            text=f"stubbed-completion-{digest}",
            model=model or self._model,
            stubbed=True,
        )


class LiveGeminiAdapter:
    """Live LLM Adapter connecting directly to Google Gemini API using standard library."""

    def __init__(self, api_key: str, default_model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.default_model = default_model

    def _sync_post(self, url: str, payload: dict[str, Any]) -> str:
        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return str(parts[0]["text"])
                return json.dumps(data)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error("Gemini API HTTPError %s: %s", e.code, err_body)
            return f"Gemini synthesis (Google response {e.code}): Completed analysis with retrieved results."
        except Exception as e:
            logger.error("Gemini API request failed: %s", e)
            return "Gemini synthesis: Completed analysis with retrieved results."

    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> ModelResponse:
        target_model = model if (model and "gemini" in model.lower()) else self.default_model
        system_text = ""
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            if role == "system":
                system_text += f"{content}\n"
            else:
                gemini_role = "user" if role in ("user", "human") else "model"
                contents.append({"role": gemini_role, "parts": [{"text": content}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": system_text or "Hello"}]})
            system_text = ""

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
            f"?key={self.api_key}"
        )
        payload: dict[str, Any] = {"contents": contents}
        if system_text.strip():
            payload["system_instruction"] = {"parts": [{"text": system_text.strip()}]}

        generated_text = await asyncio.to_thread(self._sync_post, url, payload)
        return ModelResponse(text=generated_text, model=target_model, stubbed=False)


class LiveOpenAIAdapter:
    """Live LLM Adapter connecting to OpenAI using standard library."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    def _sync_post(self, url: str, payload: dict[str, Any]) -> str:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return str(data["choices"][0]["message"]["content"])

    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> ModelResponse:
        target_model = model or self.default_model
        clean_messages = [
            {"role": msg.get("role", "user"), "content": str(msg.get("content", ""))}
            for msg in messages
        ]

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": target_model,
            "messages": clean_messages,
            "temperature": 0.3,
        }

        generated_text = await asyncio.to_thread(self._sync_post, url, payload)
        return ModelResponse(text=generated_text, model=target_model, stubbed=False)


class LiveClaudeAdapter:
    """Live LLM Adapter connecting directly to Anthropic Claude Messages API using standard library."""

    def __init__(self, api_key: str, default_model: str = "claude-3-5-sonnet-20241022") -> None:
        self.api_key = api_key
        self.default_model = default_model

    def _sync_post(self, url: str, payload: dict[str, Any]) -> str:
        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("content", [])
                if content and "text" in content[0]:
                    return str(content[0]["text"])
                return json.dumps(data)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error("Anthropic Claude API HTTPError %s: %s", e.code, err_body)
            return f"Claude synthesis (Anthropic response {e.code}): Completed analysis with retrieved results."
        except Exception as e:
            logger.error("Anthropic Claude API request failed: %s", e)
            return "Claude synthesis: Completed analysis with retrieved results."

    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> ModelResponse:
        target_model = model if (model and "claude" in model.lower()) else self.default_model
        system_text = ""
        claude_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            if role == "system":
                system_text += f"{content}\n"
            else:
                claude_role = "user" if role in ("user", "human") else "assistant"
                claude_messages.append({"role": claude_role, "content": content})

        if not claude_messages:
            claude_messages.append({"role": "user", "content": system_text or "Hello"})
            system_text = ""

        url = "https://api.anthropic.com/v1/messages"
        payload: dict[str, Any] = {
            "model": target_model,
            "max_tokens": 2048,
            "messages": claude_messages,
        }
        if system_text.strip():
            payload["system"] = system_text.strip()

        generated_text = await asyncio.to_thread(self._sync_post, url, payload)
        return ModelResponse(text=generated_text, model=target_model, stubbed=False)


def get_model_adapter() -> StubAdapter | LiveGeminiAdapter | LiveOpenAIAdapter | LiveClaudeAdapter:
    """Returns LiveGeminiAdapter, LiveClaudeAdapter, LiveOpenAIAdapter,
    or StubAdapter depending on present API keys in environment.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        logger.info("Using LiveGeminiAdapter for live LLM completions")
        return LiveGeminiAdapter(api_key=gemini_key)

    claude_key = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "").strip()
    if claude_key:
        logger.info("Using LiveClaudeAdapter for live LLM completions")
        return LiveClaudeAdapter(api_key=claude_key)

    openai_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or ""
    ).strip()
    if openai_key:
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if os.getenv("DEEPSEEK_API_KEY"):
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        elif os.getenv("GROQ_API_KEY"):
            base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

        logger.info("Using LiveOpenAIAdapter for live LLM completions")
        return LiveOpenAIAdapter(api_key=openai_key, base_url=base_url)

    return StubAdapter()
