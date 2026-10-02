"""Shared Lambda/HTTP helpers: parsing, error format, response building. No AWS calls here."""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from pydantic import ValidationError

from ..simulation.interventions import ScenarioError

MAX_BODY = int(os.environ.get("MAX_SIMULATION_INPUT_SIZE", "65536"))


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        self.status, self.code, self.message, self.details = status, code, message, details


def response(status: int, body: Any, content_type: str = "application/json", headers: dict | None = None) -> dict:
    payload = body if isinstance(body, str) else json.dumps(body, separators=(",", ":"))
    h = {"Content-Type": content_type, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    h.update(headers or {})
    return {"statusCode": status, "headers": h, "body": payload}


def error_response(err: ApiError) -> dict:
    body = {"error": {"code": err.code, "message": err.message}}
    if err.details:
        body["error"]["details"] = err.details
    return response(err.status, body)


def parse_body(event: dict) -> dict:
    raw = event.get("body") or ""
    if event.get("isBase64Encoded") and raw:
        raw = base64.b64decode(raw).decode("utf-8", errors="replace")
    if len(raw.encode("utf-8")) > MAX_BODY:
        raise ApiError(413, "payload_too_large", f"Request body exceeds {MAX_BODY} bytes")
    if not raw.strip():
        raise ApiError(400, "empty_body", "A JSON body is required")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ApiError(400, "invalid_json", "Request body is not valid JSON")
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "JSON body must be an object")
    return data


def validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        details = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()[:8]]
        raise ApiError(422, "validation_error", "Request validation failed", details)


def safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ScenarioError as exc:
        raise ApiError(422, "scenario_error", str(exc))


def route_of(event: dict) -> tuple[str, str]:
    rc = event.get("requestContext", {}).get("http", {})
    method = (rc.get("method") or event.get("httpMethod") or "GET").upper()
    path = event.get("rawPath") or event.get("path") or "/"
    stage = event.get("requestContext", {}).get("stage")
    if stage and stage != "$default" and path.startswith(f"/{stage}/"):
        path = path[len(stage) + 1:]
    return method, path.rstrip("/") or "/"
