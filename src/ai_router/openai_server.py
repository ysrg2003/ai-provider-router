from __future__ import annotations

import json
import os
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .router import AIRouter, AllProvidersFailed

ROUTER_MODEL_ID = "ai-provider-router"
MAX_REQUEST_BYTES = 1_000_000


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") in {"text", "input_text"}:
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content or "")


def messages_to_prompts(messages: Any) -> tuple[str, str]:
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty array")
    system_parts: list[str] = []
    conversation_parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("each message must be an object")
        role = str(message.get("role", "user"))
        content = _content_to_text(message.get("content"))
        if not content.strip():
            continue
        if role == "system":
            system_parts.append(content)
        else:
            conversation_parts.append(f"{role}: {content}")
    user_prompt = "\n\n".join(conversation_parts).strip()
    if not user_prompt:
        raise ValueError("messages must contain non-empty user or conversation content")
    return "\n\n".join(system_parts).strip(), user_prompt


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def openai_error(message: str, error_type: str = "invalid_request_error", code: str | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"message": message, "type": error_type}
    if code:
        error["code"] = code
    return {"error": error}


class RouterHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        router: AIRouter,
        local_api_key: str | None,
        default_provider: str | None = None,
        default_model: str | None = None,
    ) -> None:
        super().__init__(server_address, RouterRequestHandler)
        self.router = router
        self.local_api_key = local_api_key.strip() if local_api_key else ""
        self.default_provider = default_provider.strip() if default_provider else None
        self.default_model = default_model.strip() if default_model else None


class RouterRequestHandler(BaseHTTPRequestHandler):
    server: RouterHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        # Keep secrets and request bodies out of terminal logs.
        super().log_message("%s", format % args)

    def _authorized(self) -> bool:
        expected = self.server.local_api_key
        if not expected:
            return True
        actual = self.headers.get("Authorization", "")
        return secrets.compare_digest(actual, f"Bearer {expected}")

    def _send(self, status: int, payload: dict[str, Any], extra_headers: dict[str, str] | None = None) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._send(HTTPStatus.UNAUTHORIZED, openai_error("Invalid local router API key", code="invalid_api_key"))
        return False

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        if self.path in {"/health", "/v1/health"}:
            self._send(HTTPStatus.OK, {"status": "ok", "service": "ai-provider-router"})
            return
        if self.path == "/v1/models":
            self._send(HTTPStatus.OK, {
                "object": "list",
                "data": [{
                    "id": ROUTER_MODEL_ID,
                    "object": "model",
                    "created": 0,
                    "owned_by": "ai-provider-router",
                }],
            })
            return
        self._send(HTTPStatus.NOT_FOUND, openai_error("Unknown endpoint", code="not_found"))

    def do_POST(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        if self.path != "/v1/chat/completions":
            self._send(HTTPStatus.NOT_FOUND, openai_error("Unknown endpoint", code="not_found"))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("request body must be between 1 byte and 1 MB")
            raw = self.rfile.read(length)
            request = json.loads(raw.decode("utf-8"))
            messages = request.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages must be a non-empty array")
            tools = request.get("tools")
            if tools is not None and not isinstance(tools, list):
                raise ValueError("tools must be an array when provided")
            result = self.server.router.complete_chat(
                chain="default",
                messages=messages,
                tools=tools,
                tool_choice=request.get("tool_choice"),
                parallel_tool_calls=request.get("parallel_tool_calls"),
                operation="vscode_chat_completion",
                provider=request.get("router_provider") or self.server.default_provider,
                model=request.get("router_model") or self.server.default_model,
            )
            text = result.get("content")
            if not isinstance(text, str):
                text = None
            tool_calls = result.get("tool_calls") or []
            if not text and not tool_calls:
                text = json.dumps(result, ensure_ascii=False)
            message: dict[str, Any] = {"role": "assistant", "content": text}
            if tool_calls:
                message["tool_calls"] = tool_calls
            response = {
                "id": f"chatcmpl-{secrets.token_hex(12)}",
                "object": "chat.completion",
                "created": 0,
                "model": ROUTER_MODEL_ID,
                "router_provider": result.get("provider"),
                "router_model": result.get("model"),
                "router_route": result.get("route", "default"),
                "choices": [{
                    "index": 0,
                    "message": message,
                    "finish_reason": result.get("finish_reason") or ("tool_calls" if tool_calls else "stop"),
                }],
            }
            if request.get("stream") is True:
                self._send_stream(
                    response,
                    text or "",
                    tool_calls,
                    extra_headers={
                        "X-AI-Router-Provider": str(result.get("provider", "")),
                        "X-AI-Router-Model": str(result.get("model", "")),
                    },
                )
            else:
                self._send(
                    HTTPStatus.OK,
                    response,
                    extra_headers={
                        "X-AI-Router-Provider": str(result.get("provider", "")),
                        "X-AI-Router-Model": str(result.get("model", "")),
                    },
                )
        except AllProvidersFailed as exc:
            self._send(HTTPStatus.BAD_GATEWAY, openai_error(str(exc), error_type="provider_error", code="all_providers_failed"))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, openai_error(str(exc)))
        except Exception as exc:  # noqa: BLE001 - safe local API boundary
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, openai_error(type(exc).__name__, error_type="server_error"))

    def _send_stream(
        self,
        response: dict[str, Any],
        text: str,
        tool_calls: list[dict[str, Any]] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        chunks: list[dict[str, Any]] = [{
            "id": response["id"],
            "object": "chat.completion.chunk",
            "created": 0,
            "model": ROUTER_MODEL_ID,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }]
        if text:
            chunks.append({
                "id": response["id"],
                "object": "chat.completion.chunk",
                "created": 0,
                "model": ROUTER_MODEL_ID,
                "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
            })
        for index, tool_call in enumerate(tool_calls or []):
            function = tool_call.get("function") if isinstance(tool_call, dict) else {}
            if not isinstance(function, dict):
                function = {}
            chunks.append({
                "id": response["id"],
                "object": "chat.completion.chunk",
                "created": 0,
                "model": ROUTER_MODEL_ID,
                "choices": [{"index": 0, "delta": {"tool_calls": [{
                    "index": index,
                    "id": tool_call.get("id", f"call_{index}"),
                    "type": "function",
                    "function": {
                        "name": function.get("name", ""),
                        "arguments": function.get("arguments", "{}"),
                    },
                }]}, "finish_reason": None}],
            })
        chunks.append({
            "id": response["id"],
            "object": "chat.completion.chunk",
            "created": 0,
            "model": ROUTER_MODEL_ID,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls" if tool_calls else "stop"}],
        })
        payload = "".join(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
        body = payload.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(
    *,
    config_dir: str,
    state_db: str,
    host: str,
    port: int,
    local_api_key: str = "",
    provider: str | None = None,
    model: str | None = None,
) -> None:
    normalized_host = host.strip() or "127.0.0.1"
    router = AIRouter(config_dir=config_dir, state_db=state_db)
    key = local_api_key.strip() or os.getenv("AI_ROUTER_LOCAL_API_KEY", "").strip()
    if normalized_host not in {"127.0.0.1", "localhost", "::1"} and not key:
        router.close()
        raise ValueError("--local-api-key is required when --host is not loopback")
    server = RouterHTTPServer((normalized_host, port), router, key, provider, model)
    print(json.dumps({
        "status": "listening",
        "base_url": f"http://{normalized_host}:{port}/v1",
        "model": ROUTER_MODEL_ID,
        "provider_selection": provider or "auto",
        "model_selection": model or "auto",
        "auth": "bearer" if key else "none-loopback-only",
    }, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        router.close()
