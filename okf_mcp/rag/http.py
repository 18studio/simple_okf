"""Small stdlib HTTP helpers for optional RAG infrastructure clients."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RagHttpError(RuntimeError):
    """Raised when an infrastructure HTTP request fails."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    text: str

    def json(self) -> Any:
        if not self.text.strip():
            return None
        return json.loads(self.text)


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def request_json(
    method: str,
    base_url: str,
    path: str = "",
    *,
    payload: Any | None = None,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    user: str = "",
    password: str = "",
    bearer_token: str = "",
    timeout: float = 10.0,
    expected: tuple[int, ...] = (200,),
) -> HttpResponse:
    if not base_url.strip():
        raise RagHttpError("base URL is not configured")
    url = _join_url(base_url, path)
    if query:
        url += "?" + urlencode(query)
    req_headers = dict(headers or {})
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    if user:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        req_headers["Authorization"] = f"Basic {token}"
    if bearer_token:
        req_headers["api-key"] = bearer_token
    request = Request(url, data=data, method=method.upper(), headers=req_headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local/dev infra URL from env.
            text = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if int(exc.code) in expected:
            return HttpResponse(status=int(exc.code), text=body)
        raise RagHttpError(f"{method.upper()} {url} failed with HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise RagHttpError(f"{method.upper()} {url} failed: {exc.reason}") from exc
    if status not in expected:
        raise RagHttpError(f"{method.upper()} {url} returned HTTP {status}: {text[:500]}")
    return HttpResponse(status=status, text=text)


def post_text(
    base_url: str,
    *,
    query: str,
    body: str = "",
    user: str = "",
    password: str = "",
    timeout: float = 10.0,
    expected: tuple[int, ...] = (200,),
) -> HttpResponse:
    if not base_url.strip():
        raise RagHttpError("base URL is not configured")
    url = base_url.rstrip("/") + "/?" + urlencode({"query": query})
    req_headers: dict[str, str] = {"Content-Type": "text/plain; charset=utf-8"}
    if user:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        req_headers["Authorization"] = f"Basic {token}"
    request = Request(url, data=body.encode("utf-8"), method="POST", headers=req_headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local/dev infra URL from env.
            text = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
    except HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        if int(exc.code) in expected:
            return HttpResponse(status=int(exc.code), text=body_text)
        raise RagHttpError(f"POST {url} failed with HTTP {exc.code}: {body_text[:500]}") from exc
    except URLError as exc:
        raise RagHttpError(f"POST {url} failed: {exc.reason}") from exc
    if status not in expected:
        raise RagHttpError(f"POST {url} returned HTTP {status}: {text[:500]}")
    return HttpResponse(status=status, text=text)
