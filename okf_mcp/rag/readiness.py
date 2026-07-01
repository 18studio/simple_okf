"""Small stdlib readiness probes for local RAG infrastructure."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .config import RagSettings


class RagReadinessError(RuntimeError):
    """Raised when required RAG infrastructure is not reachable."""


@dataclass(frozen=True)
class ReadinessProbeResult:
    name: str
    ok: bool
    url: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "url": self.url, "detail": self.detail}


def _require(value: str, key: str) -> str:
    if not value.strip():
        raise RagReadinessError(f"{key} is required for MCP startup readiness")
    return value.strip()


def _request(url: str, *, timeout: float, user: str = "", password: str = "", headers: dict[str, str] | None = None) -> tuple[int, str]:
    request_headers = dict(headers or {})
    if user:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        request_headers["Authorization"] = f"Basic {token}"
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URLs come from local config.
        body = response.read(512 * 1024).decode("utf-8", errors="replace")
        return int(response.status), body


def _probe(name: str, url: str, *, timeout: float, user: str = "", password: str = "") -> ReadinessProbeResult:
    try:
        status, body = _request(url, timeout=timeout, user=user, password=password)
    except HTTPError as exc:
        return ReadinessProbeResult(name, False, url, f"HTTP {exc.code}: {exc.reason}")
    except (OSError, URLError, TimeoutError) as exc:
        return ReadinessProbeResult(name, False, url, str(exc))
    if 200 <= status < 300:
        return ReadinessProbeResult(name, True, url, body.strip()[:500] or f"HTTP {status}")
    return ReadinessProbeResult(name, False, url, f"HTTP {status}: {body.strip()[:500]}")


def probe_clickhouse(settings: RagSettings, *, timeout: float = 2.0) -> ReadinessProbeResult:
    base = _require(settings.clickhouse_url, "RAG_CLICKHOUSE_URL").rstrip("/") + "/"
    url = urljoin(base, "ping")
    return _probe("clickhouse", url, timeout=timeout, user=settings.clickhouse_user, password=settings.clickhouse_password)


def probe_opensearch(settings: RagSettings, *, timeout: float = 2.0) -> ReadinessProbeResult:
    base = _require(settings.opensearch_url, "RAG_OPENSEARCH_URL").rstrip("/") + "/"
    _require(settings.opensearch_index, "RAG_OPENSEARCH_INDEX")
    url = urljoin(base, "_cluster/health")
    result = _probe("opensearch", url, timeout=timeout, user=settings.opensearch_user, password=settings.opensearch_password)
    if not result.ok:
        return result
    try:
        payload = json.loads(result.detail)
    except json.JSONDecodeError:
        return result
    status = str(payload.get("status") or "").lower()
    if status == "red":
        return ReadinessProbeResult("opensearch", False, url, "cluster health is red")
    return ReadinessProbeResult("opensearch", True, url, f"cluster health is {status or 'unknown'}")


def probe_qdrant(settings: RagSettings, *, timeout: float = 2.0) -> ReadinessProbeResult:
    base = _require(settings.qdrant_url, "RAG_QDRANT_URL").rstrip("/") + "/"
    _require(settings.qdrant_collection, "RAG_QDRANT_COLLECTION")
    headers = {"api-key": settings.qdrant_api_key} if settings.qdrant_api_key else None
    readyz_url = urljoin(base, "readyz")
    try:
        status, body = _request(readyz_url, timeout=timeout, headers=headers)
        if 200 <= status < 300:
            return ReadinessProbeResult("qdrant", True, readyz_url, body.strip()[:500] or f"HTTP {status}")
    except HTTPError as exc:
        if exc.code not in {404, 405}:
            return ReadinessProbeResult("qdrant", False, readyz_url, f"HTTP {exc.code}: {exc.reason}")
    except (OSError, URLError, TimeoutError) as exc:
        return ReadinessProbeResult("qdrant", False, readyz_url, str(exc))

    collections_url = urljoin(base, "collections")
    try:
        status, body = _request(collections_url, timeout=timeout, headers=headers)
    except HTTPError as exc:
        return ReadinessProbeResult("qdrant", False, collections_url, f"HTTP {exc.code}: {exc.reason}")
    except (OSError, URLError, TimeoutError) as exc:
        return ReadinessProbeResult("qdrant", False, collections_url, str(exc))
    if 200 <= status < 300:
        return ReadinessProbeResult("qdrant", True, collections_url, body.strip()[:500] or f"HTTP {status}")
    return ReadinessProbeResult("qdrant", False, collections_url, f"HTTP {status}: {body.strip()[:500]}")


def check_rag_readiness(settings: RagSettings, *, timeout: float = 2.0) -> dict[str, Any]:
    """Run all required RAG infrastructure readiness probes."""

    probes = [
        probe_clickhouse(settings, timeout=timeout),
        probe_opensearch(settings, timeout=timeout),
        probe_qdrant(settings, timeout=timeout),
    ]
    payload = {"ok": all(probe.ok for probe in probes), "probes": [probe.to_dict() for probe in probes]}
    if not payload["ok"]:
        failed = "; ".join(f"{probe.name} ({probe.url}): {probe.detail}" for probe in probes if not probe.ok)
        raise RagReadinessError(f"RAG infrastructure readiness failed: {failed}")
    return payload
