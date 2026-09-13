"""Local OpenAI-compatible bridge from OpenCode to the v0 Platform API.

OpenCode sends requests to /v1/chat/completions, while the current v0
Platform API exposes v0/v0-gpt-5 through /v1/chats. This small stdlib-only
proxy translates between the two request/response shapes.

The v0 API key is read only from V0_API_KEY and is never logged.
"""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HOST = os.getenv("V0_OPENCODE_PROXY_HOST", "127.0.0.1")
PORT = int(os.getenv("V0_OPENCODE_PROXY_PORT", "8765"))
V0_API_URL = "https://api.v0.dev/v1/chats"
V0_MODEL_ID = os.getenv("V0_MODEL_ID", "v0/v0-gpt-5")
TIMEOUT_SECONDS = int(os.getenv("V0_OPENCODE_PROXY_TIMEOUT", "180"))


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _message_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(json.dumps(item, ensure_ascii=False))
        return "".join(parts)
    return str(content)


def _messages_to_prompt(messages: object) -> tuple[str | None, str]:
    if not isinstance(messages, list):
        return None, str(messages)

    system_parts: list[str] = []
    transcript: list[str] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user"))
        content = _message_content(item.get("content", ""))
        if role == "system":
            system_parts.append(content)
            continue
        if role == "tool":
            tool_name = item.get("name", "tool")
            transcript.append(f"TOOL RESULT ({tool_name}):\n{content}")
            continue
        transcript.append(f"{role.upper()}:\n{content}")

    system = "\n\n".join(part for part in system_parts if part) or None
    prompt = "\n\n".join(part for part in transcript if part)
    return system, prompt


def _v0_request(payload: dict[str, object]) -> dict[str, object]:
    token = os.getenv("V0_API_KEY")
    if not token:
        raise RuntimeError("V0_API_KEY is not set")

    request_body: dict[str, object] = {
        "message": payload.get("message", ""),
        "modelConfiguration": {
            "modelId": V0_MODEL_ID,
            "imageGenerations": False,
            "thinking": False,
        },
        "chatPrivacy": "private",
        "responseMode": "sync",
    }
    if payload.get("system"):
        request_body["system"] = payload["system"]
    if payload.get("tools"):
        request_body["tools"] = payload["tools"]
    if payload.get("tool_choice") is not None:
        request_body["tool_choice"] = payload["tool_choice"]

    request = Request(
        V0_API_URL,
        data=_json_bytes(request_body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"v0 returned HTTP {error.code}: {details}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach v0: {error.reason}") from error


def _assistant_message(result: dict[str, object]) -> dict[str, object]:
    messages = result.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "assistant":
                return message
    return {"role": "assistant", "content": result.get("text", "")}


def _completion_response(request_payload: dict[str, object], result: dict[str, object]) -> dict[str, object]:
    message = _assistant_message(result)
    content = message.get("content", "")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    return {
        "id": result.get("id", f"v0-proxy-{int(time.time())}"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request_payload.get("model", V0_MODEL_ID),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": message.get("finishReason", "stop"),
            }
        ],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "v0-opencode-proxy/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # Do not log request bodies or authorization headers.
        print(f"[v0-proxy] {self.address_string()} {format % args}")

    def _send_json(self, status: int, body: object) -> None:
        data = _json_bytes(body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"ok": True, "model": V0_MODEL_ID})
            return
        if self.path.rstrip("/") == "/v1/models":
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": "v0-gpt-5",
                            "object": "model",
                            "owned_by": "v0",
                        }
                    ],
                },
            )
            return
        self._send_json(404, {"error": {"message": "Not found"}})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "Not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            system, prompt = _messages_to_prompt(payload.get("messages", []))
            translated = dict(payload)
            translated["system"] = system
            translated["message"] = prompt
            result = _v0_request(translated)
            completion = _completion_response(payload, result)

            if payload.get("stream"):
                chunk = {
                    "id": completion["id"],
                    "object": "chat.completion.chunk",
                    "created": completion["created"],
                    "model": completion["model"],
                    "choices": [
                        {
                            "index": 0,
                            "delta": completion["choices"][0]["message"],
                            "finish_reason": None,
                        }
                    ],
                }
                done = {
                    "id": completion["id"],
                    "object": "chat.completion.chunk",
                    "created": completion["created"],
                    "model": completion["model"],
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                body = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\ndata: {json.dumps(done)}\n\ndata: [DONE]\n\n".encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._send_json(200, completion)
        except Exception as error:  # noqa: BLE001
            self._send_json(502, {"error": {"message": str(error)}})


def main() -> None:
    if not os.getenv("V0_API_KEY"):
        raise SystemExit("V0_API_KEY is required")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"v0 OpenCode proxy listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
