"""ClickHouse event writer for OKF RAG."""

from __future__ import annotations

import json
from typing import Any

from okf_mcp.rag.events import RagEvent
from okf_mcp.rag.http import RagHttpError, post_text


class ClickHouseEventWriter:
    def __init__(
        self,
        *,
        url: str,
        database: str,
        table: str,
        user: str = "",
        password: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.url = url
        self.database = database
        self.table = table
        self.user = user
        self.password = password
        self.timeout = timeout

    @property
    def qualified_table(self) -> str:
        if not self.database or not self.table:
            raise RagHttpError("ClickHouse database/table is not configured")
        return f"{self.database}.{self.table}"

    def ensure_schema(self) -> dict[str, Any]:
        if not self.database:
            raise RagHttpError("RAG_CLICKHOUSE_DATABASE is not configured")
        if not self.table:
            raise RagHttpError("RAG_CLICKHOUSE_EVENTS_TABLE is not configured")
        post_text(
            self.url,
            query=f"CREATE DATABASE IF NOT EXISTS {self.database}",
            user=self.user,
            password=self.password,
            timeout=self.timeout,
        )
        post_text(
            self.url,
            query=f"""
CREATE TABLE IF NOT EXISTS {self.qualified_table} (
    event_id String,
    correlation_id String,
    timestamp DateTime64(0, 'UTC'),
    event_type LowCardinality(String),
    status LowCardinality(String),
    query String,
    retrieval_mode LowCardinality(String),
    filters String,
    corpus_digest String,
    retrieved String,
    citations String,
    answer String,
    metrics String,
    evaluator String,
    timings_ms String,
    error String,
    raw String
) ENGINE = MergeTree
ORDER BY (timestamp, correlation_id, event_id)
""".strip(),
            user=self.user,
            password=self.password,
            timeout=self.timeout,
        )
        return {"database": self.database, "table": self.table}

    def write_event(self, event: RagEvent) -> dict[str, Any]:
        self.ensure_schema()
        row = event.to_clickhouse_row()
        body = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        post_text(
            self.url,
            query=f"INSERT INTO {self.qualified_table} FORMAT JSONEachRow",
            body=body,
            user=self.user,
            password=self.password,
            timeout=self.timeout,
        )
        return {"written": 1, "event_id": event.event_id, "table": self.qualified_table}
