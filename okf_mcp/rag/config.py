"""Configuration for OKF RAG tools.

The real local environment is intentionally loaded from `okf_mcp/rag/.env`.
Docker Compose can also inject the same keys through env_file/process env.
Secrets are never stored in this package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class RagConfigError(RuntimeError):
    """Raised when RAG configuration is missing or invalid."""


@dataclass(frozen=True)
class RagSettings:
    project_root: Path
    env_file: Path
    bundle_dir: Path
    artifacts_dir: Path
    retrieval_result_limit: int = 10
    answer_evidence_limit: int = 5
    clickhouse_url: str = ""
    clickhouse_user: str = ""
    clickhouse_password: str = ""
    clickhouse_database: str = ""
    clickhouse_events_table: str = ""
    opensearch_url: str = ""
    opensearch_user: str = ""
    opensearch_password: str = ""
    opensearch_index: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = ""
    retrieval_mode: str = "local"
    evaluation_mode: str = "disabled"
    event_storage_mode: str = "disabled"
    evaluation_threshold: float = 0.5
    embedding_model: str = "deterministic-hash-v1"
    embedding_dimensions: int = 64
    hybrid_keyword_weight: float = 0.5
    hybrid_semantic_weight: float = 0.5
    infrastructure_timeout_seconds: float = 10.0


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_env_file() -> Path:
    return project_root() / "okf_mcp" / "rag" / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _path_from_env(root: Path, values: dict[str, str], key: str, default: str) -> Path:
    raw = values.get(key, default).strip()
    if not raw:
        raise RagConfigError(f"{key} must not be empty")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


_LEGACY_RAG_ARTIFACT_DIRS = {
    "rag/artifacts",
    "./rag/artifacts",
    "okf_mcp/rag/artifacts",
    "./okf_mcp/rag/artifacts",
    "artifacts",
    "./artifacts",
}


def _rag_artifacts_dir_from_env(root: Path, values: dict[str, str]) -> Path:
    raw = values.get("RAG_ARTIFACTS_DIR", "artifacts/rag").strip()
    if not raw:
        raise RagConfigError("RAG_ARTIFACTS_DIR must not be empty")
    if raw in _LEGACY_RAG_ARTIFACT_DIRS:
        raw = "artifacts/rag"

    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()

    artifacts_root = (root / "artifacts").resolve()
    try:
        resolved.relative_to(artifacts_root)
    except ValueError as exc:
        raise RagConfigError(
            "RAG_ARTIFACTS_DIR must resolve inside repository artifacts/: "
            f"{values.get('RAG_ARTIFACTS_DIR', 'artifacts/rag')!r} -> {resolved}"
        ) from exc
    return resolved


def _apply_process_env(values: dict[str, str]) -> dict[str, str]:
    merged = dict(values)
    for key, value in os.environ.items():
        if key.startswith("RAG_") or key == "OPENAI_API_KEY":
            merged[key] = value
    return merged


def _str_from_env(values: dict[str, str], key: str, default: str = "") -> str:
    return values.get(key, default).strip()


def _float_from_env(values: dict[str, str], key: str, default: float) -> float:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RagConfigError(f"{key} must be a number") from exc
    if value < 0:
        raise RagConfigError(f"{key} must be non-negative")
    return value


def _choice_from_env(values: dict[str, str], key: str, default: str, choices: set[str]) -> str:
    value = values.get(key, default).strip().casefold()
    if not value:
        value = default
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise RagConfigError(f"{key} must be one of: {allowed}")
    return value


def _int_from_env(values: dict[str, str], key: str, default: int) -> int:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RagConfigError(f"{key} must be an integer") from exc
    if value < 1:
        raise RagConfigError(f"{key} must be at least 1")
    return value


def _require_keys(values: dict[str, str], keys: tuple[str, ...], *, reason: str) -> None:
    missing = [key for key in keys if not values.get(key, "").strip()]
    if missing:
        raise RagConfigError(f"{reason} requires: {', '.join(missing)}")


def load_settings(env_file: Path | None = None) -> RagSettings:
    root = project_root()
    explicit_env_file = env_file is not None
    selected_env = (env_file or default_env_file()).resolve()
    if selected_env.exists():
        file_values = _parse_env_file(selected_env)
    elif explicit_env_file:
        display = selected_env.relative_to(root) if selected_env.is_relative_to(root) else selected_env
        raise RagConfigError(
            f"RAG env file not found: {display}. Create it from okf_mcp/rag/.env.example."
        )
    else:
        file_values = {}
    values = _apply_process_env(file_values)
    retrieval_mode = _choice_from_env(values, "RAG_RETRIEVAL_MODE", "local", {"local", "keyword", "semantic", "hybrid"})
    event_storage_mode = _choice_from_env(values, "RAG_EVENT_STORAGE_MODE", "disabled", {"disabled", "best-effort", "required"})
    if retrieval_mode in {"keyword", "hybrid"}:
        _require_keys(values, ("RAG_OPENSEARCH_URL", "RAG_OPENSEARCH_INDEX"), reason=f"RAG_RETRIEVAL_MODE={retrieval_mode}")
    if retrieval_mode in {"semantic", "hybrid"}:
        _require_keys(values, ("RAG_QDRANT_URL", "RAG_QDRANT_COLLECTION"), reason=f"RAG_RETRIEVAL_MODE={retrieval_mode}")
    if event_storage_mode != "disabled":
        _require_keys(
            values,
            ("RAG_CLICKHOUSE_URL", "RAG_CLICKHOUSE_DATABASE", "RAG_CLICKHOUSE_EVENTS_TABLE"),
            reason=f"RAG_EVENT_STORAGE_MODE={event_storage_mode}",
        )
    bundle_dir = _path_from_env(root, values, "RAG_BUNDLE_DIR", "okf")
    artifacts_dir = _rag_artifacts_dir_from_env(root, values)
    if not bundle_dir.is_dir():
        raise RagConfigError(f"RAG_BUNDLE_DIR does not exist or is not a directory: {bundle_dir}")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return RagSettings(
        project_root=root,
        env_file=selected_env,
        bundle_dir=bundle_dir,
        artifacts_dir=artifacts_dir,
        retrieval_result_limit=_int_from_env(values, "RAG_RETRIEVAL_RESULT_LIMIT", 10),
        answer_evidence_limit=_int_from_env(values, "RAG_ANSWER_EVIDENCE_LIMIT", 5),
        clickhouse_url=_str_from_env(values, "RAG_CLICKHOUSE_URL"),
        clickhouse_user=_str_from_env(values, "RAG_CLICKHOUSE_USER"),
        clickhouse_password=_str_from_env(values, "RAG_CLICKHOUSE_PASSWORD"),
        clickhouse_database=_str_from_env(values, "RAG_CLICKHOUSE_DATABASE"),
        clickhouse_events_table=_str_from_env(values, "RAG_CLICKHOUSE_EVENTS_TABLE"),
        opensearch_url=_str_from_env(values, "RAG_OPENSEARCH_URL"),
        opensearch_user=_str_from_env(values, "RAG_OPENSEARCH_USER"),
        opensearch_password=_str_from_env(values, "RAG_OPENSEARCH_PASSWORD"),
        opensearch_index=_str_from_env(values, "RAG_OPENSEARCH_INDEX"),
        qdrant_url=_str_from_env(values, "RAG_QDRANT_URL"),
        qdrant_api_key=_str_from_env(values, "RAG_QDRANT_API_KEY"),
        qdrant_collection=_str_from_env(values, "RAG_QDRANT_COLLECTION"),
        retrieval_mode=retrieval_mode,
        evaluation_mode=_choice_from_env(values, "RAG_EVALUATION_MODE", "disabled", {"disabled", "sample", "always", "fail-on-threshold"}),
        event_storage_mode=event_storage_mode,
        evaluation_threshold=_float_from_env(values, "RAG_EVALUATION_THRESHOLD", 0.5),
        embedding_model=_str_from_env(values, "RAG_EMBEDDING_MODEL", "deterministic-hash-v1") or "deterministic-hash-v1",
        embedding_dimensions=_int_from_env(values, "RAG_EMBEDDING_DIMENSIONS", 64),
        hybrid_keyword_weight=_float_from_env(values, "RAG_HYBRID_KEYWORD_WEIGHT", 0.5),
        hybrid_semantic_weight=_float_from_env(values, "RAG_HYBRID_SEMANTIC_WEIGHT", 0.5),
        infrastructure_timeout_seconds=_float_from_env(values, "RAG_INFRASTRUCTURE_TIMEOUT_SECONDS", 10.0),
    )
