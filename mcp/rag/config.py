"""Configuration for OKF RAG tools.

The real local environment is intentionally loaded from `mcp/rag/.env`.
Secrets are never stored in this package.
"""

from __future__ import annotations

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


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_env_file() -> Path:
    return project_root() / "mcp" / "rag" / ".env"


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
    "mcp/rag/artifacts",
    "./mcp/rag/artifacts",
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


def load_settings(env_file: Path | None = None) -> RagSettings:
    root = project_root()
    selected_env = (env_file or default_env_file()).resolve()
    if not selected_env.exists():
        display = selected_env.relative_to(root) if selected_env.is_relative_to(root) else selected_env
        raise RagConfigError(
            f"RAG env file not found: {display}. Create it from mcp/rag/.env.example."
        )
    values = _parse_env_file(selected_env)
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
    )
