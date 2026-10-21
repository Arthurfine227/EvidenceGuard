from __future__ import annotations

import json
import os
import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


def load_local_config() -> None:
    """Read only project-specific keys; shell environment takes precedence."""
    path = Path(__file__).resolve().parents[2] / '.env.local'
    if not path.is_file():
        return
    allowed = {'EVIDENCEPILOT_API_KEY', 'EVIDENCEPILOT_MODEL', 'EVIDENCEPILOT_BASE_URL'}
    for line in path.read_text(encoding='utf-8').splitlines():
        key, separator, value = line.partition('=')
        if separator and key.strip() in allowed:
            os.environ.setdefault(key.strip(), value.strip())


class ProviderError(RuntimeError):
    pass


@dataclass
class OpenAICompatibleProvider:
    """Small dependency-free client for OpenAI-compatible chat endpoints."""

    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 60
    request_metadata: list = field(default_factory=list, repr=False)

    @classmethod
    def from_environment(cls) -> "OpenAICompatibleProvider | None":
        load_local_config()
        key = os.getenv("EVIDENCEPILOT_API_KEY", "").strip()
        model = os.getenv("EVIDENCEPILOT_MODEL", "").strip()
        if not key or not model:
            return None
        return cls(
            api_key=key,
            model=model,
            base_url=os.getenv("EVIDENCEPILOT_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        )

    def complete_json(self, system: str, user: str, max_tokens: int = 2048) -> dict:
        request_data = {
                "model": self.model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
                "max_tokens": max_tokens,
            }
        if urlsplit(self.base_url).hostname == 'api.deepseek.com':
            # Keep the baseline and connectivity check in non-thinking mode.
            request_data['thinking'] = {'type': 'disabled'}
        body = json.dumps(request_data).encode('utf-8')
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Avoid echoing server response bodies or credentials in diagnostics.
            raise ProviderError(f"LLM endpoint returned HTTP {exc.code}") from None
        except TimeoutError:
            raise ProviderError(f'LLM request timed out after {self.timeout_seconds}s') from None
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.gaierror):
                category = 'DNS lookup failed'
            elif isinstance(reason, ssl.SSLError):
                category = 'TLS certificate/connection failed'
            elif isinstance(reason, (TimeoutError, socket.timeout)):
                category = f'connection timed out after {self.timeout_seconds}s'
            else:
                category = 'network/proxy connection failed (' + type(reason).__name__ + ')'
            raise ProviderError('LLM request failed: ' + category) from None
        except json.JSONDecodeError:
            raise ProviderError('Endpoint response was not valid JSON') from None
        try:
            self.request_metadata.append({'model_returned': payload.get('model'),
                'usage': payload.get('usage', {}),
                'finish_reason': payload.get('choices', [{}])[0].get('finish_reason')})
            content = payload["choices"][0]["message"]["content"]
            if not content:
                raise ProviderError('Endpoint returned empty message content')
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ProviderError('Endpoint returned JSON, but not a JSON object')
            return result
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("Endpoint returned an unexpected response") from exc

    def complete_tools(self, messages: list, tools: list, max_tokens: int = 1024) -> dict:
        """Native function calls with caller-managed assistant/tool message history."""
        data = {'model': self.model, 'messages': messages, 'tools': tools,
                'tool_choice': 'auto', 'temperature': 0, 'max_tokens': max_tokens}
        if urlsplit(self.base_url).hostname == 'api.deepseek.com':
            data['thinking'] = {'type': 'disabled'}
        request = urllib.request.Request(self.base_url + '/chat/completions',
            data=json.dumps(data).encode('utf-8'), headers={
                'Authorization': 'Bearer ' + self.api_key, 'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            raise ProviderError(f'LLM endpoint returned HTTP {exc.code}') from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError('Native tool request failed: ' + type(exc).__name__) from None
        try:
            choice = payload['choices'][0]
            self.request_metadata.append({'model_returned': payload.get('model'),
                'usage': payload.get('usage', {}), 'finish_reason': choice.get('finish_reason')})
            if choice.get('finish_reason') == 'length':
                raise ProviderError('Native response exceeded output token budget')
            message = choice['message']
            if message.get('role') != 'assistant':
                raise ProviderError('Expected assistant response')
            return {key: message[key] for key in ('role', 'content', 'tool_calls') if key in message}
        except (KeyError, IndexError, TypeError):
            raise ProviderError('Unexpected native tool response') from None

