import json
import logging
import re
from collections import OrderedDict
from time import monotonic
from uuid import uuid4

from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY = 256 * 1024
logger = logging.getLogger("buildwise")


class JsonCORS(CORSMiddleware):
    def preflight_response(self, request_headers: Headers) -> Response:
        response = super().preflight_response(request_headers)
        if response.status_code == 400:
            headers = dict(response.headers)
            headers.pop("content-length", None)
            headers.pop("content-type", None)
            return JSONResponse(
                {
                    "error": {
                        "code": "cors_denied",
                        "message": "CORS request denied",
                        "correlation_id": request_headers["x-correlation-id"],
                    }
                },
                status_code=400,
                headers=headers,
            )
        return response


class RequestSafety:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.writes: OrderedDict[str, tuple[float, int]] = OrderedDict()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        supplied = headers.get(b"x-correlation-id", b"").decode("latin1")
        correlation = (
            supplied
            if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", supplied)
            else str(uuid4())
        )
        scope.setdefault("state", {})["correlation_id"] = correlation
        scope["headers"] = [
            (k, v) for k, v in scope["headers"] if k.lower() != b"x-correlation-id"
        ] + [(b"x-correlation-id", correlation.encode())]
        started = False

        async def wrapped_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message["headers"] = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() != b"x-correlation-id"
                ] + [(b"x-correlation-id", correlation.encode())]
            await send(message)

        async def reject(status: int, code: str, message: str) -> None:
            body = json.dumps(
                {
                    "error": {
                        "code": code,
                        "message": message,
                        "correlation_id": correlation,
                    }
                }
            ).encode()
            await wrapped_send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await wrapped_send({"type": "http.response.body", "body": body})

        length = headers.get(b"content-length")
        if length:
            try:
                if int(length) < 0:
                    raise ValueError
                if int(length) > MAX_BODY:
                    await reject(413, "body_too_large", "Request body exceeds 256 KB")
                    return
            except ValueError:
                await reject(400, "invalid_content_length", "Invalid Content-Length")
                return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_BODY:
                await reject(413, "body_too_large", "Request body exceeds 256 KB")
                return
            if not message.get("more_body", False):
                break
        if scope["method"] == "POST":
            key = str(scope.get("client", ("unknown",))[0])
            now = monotonic()
            since, count = self.writes.pop(key, (now, 0))
            if now - since >= 60:
                since, count = now, 0
            self.writes[key] = (since, count + 1)
            if len(self.writes) > 10000:
                self.writes.popitem(last=False)
            if count >= 30:
                await reject(429, "rate_limited", "Too many write requests")
                return
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        try:
            await self.app(scope, replay, wrapped_send)
            logger.info("request_completed")
        except Exception:
            logger.error("request_failed")
            if not started:
                await reject(500, "internal_error", "Internal server error")
