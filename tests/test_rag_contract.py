from __future__ import annotations

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from okf_mcp.cli import server_main
from okf_mcp.rag.config import RagConfigError, load_settings
from okf_mcp.rag.embeddings import build_embedding_provider
from okf_mcp.rag.events import DeterministicRagEvaluator, RagEvent
from okf_mcp.rag.models import OKFChunkRecord, OKFRetrievalHit
from okf_mcp.rag.readiness import RagReadinessError, check_rag_readiness
from okf_mcp.rag.retrieval.hybrid import OKFRagRetriever
from okf_mcp.rag.storage.opensearch import OpenSearchStore
from okf_mcp.rag.storage.qdrant import QdrantStore


class RagContractTests(unittest.TestCase):
    def _bundle(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        root = base / "okf"
        root.mkdir()
        (root / "feature.md").write_text(
            "---\n"
            "type: Function Requirement\n"
            "status: draft\n"
            "title: Feature Search\n"
            "tags: [search]\n"
            "---\n\n"
            "# Feature Search\n\nUsers can search OKF knowledge.\n",
            encoding="utf-8",
        )
        env = base / ".env"
        artifacts_dir = Path("artifacts") / f"rag-test-{base.name}"
        self.addCleanup(lambda: shutil.rmtree(artifacts_dir, ignore_errors=True))
        env.write_text(
            f"RAG_BUNDLE_DIR={root}\n"
            f"RAG_ARTIFACTS_DIR={artifacts_dir.as_posix()}\n"
            "RAG_RETRIEVAL_MODE=local\n"
            "RAG_EVENT_STORAGE_MODE=disabled\n",
            encoding="utf-8",
        )
        return tmp, root, env

    def test_local_refresh_and_retrieve_are_infra_free(self) -> None:
        tmp, _root, env = self._bundle()
        with tmp:
            settings = load_settings(env)
            retriever = OKFRagRetriever(settings)
            refreshed = retriever.refresh_index(settings.artifacts_dir)
            self.assertEqual(refreshed["mode"], "local")
            self.assertEqual(refreshed["opensearch"], None)
            self.assertEqual(refreshed["qdrant"], None)
            result = retriever.retrieve("search", limit=3)
            self.assertEqual(result["mode"], "local")
            self.assertGreaterEqual(len(result["hits"]), 1)
            self.assertEqual(result["event_storage"]["status"], "disabled")

    def test_infrastructure_mode_requires_backend_settings(self) -> None:
        tmp, _root, env = self._bundle()
        with tmp:
            env.write_text(env.read_text(encoding="utf-8") + "RAG_RETRIEVAL_MODE=keyword\n", encoding="utf-8")
            with self.assertRaises(RagConfigError):
                load_settings(env)

    def test_event_shape_serializes_clickhouse_json_fields(self) -> None:
        event = RagEvent.create(
            event_type="retrieve",
            status="passed",
            query="search",
            retrieval_mode="local",
            filters={"tag": "search"},
            retrieved=[{"concept_id": "feature", "score": 1.0}],
        )
        row = event.to_clickhouse_row()
        for key in (
            "event_id",
            "correlation_id",
            "timestamp",
            "event_type",
            "status",
            "query",
            "retrieval_mode",
            "filters",
            "corpus_digest",
            "retrieved",
            "citations",
            "answer",
            "metrics",
            "evaluator",
            "timings_ms",
            "error",
            "raw",
        ):
            self.assertIn(key, row)
        for json_field in ("filters", "retrieved", "citations", "metrics", "evaluator", "timings_ms", "raw"):
            self.assertIsInstance(row[json_field], str)
        self.assertIn("search", row["filters"])
        self.assertIsInstance(row["retrieved"], str)

    def test_deterministic_evaluator_emits_required_metrics(self) -> None:
        evaluator = DeterministicRagEvaluator(threshold=0.1)
        metrics = evaluator.evaluate(
            question="search OKF",
            answer="Found search OKF evidence",
            hits=[{"content": "search OKF knowledge"}],
            citations=[{"concept_id": "feature"}],
        )
        names = {metric.name for metric in metrics}
        self.assertEqual(
            names,
            {
                "context_precision",
                "context_recall",
                "faithfulness",
                "answer_relevancy",
                "citation_coverage",
                "factual_correctness",
            },
        )
        self.assertTrue(all(isinstance(metric.threshold, float) for metric in metrics))
        self.assertTrue(all(isinstance(metric.passed, bool) for metric in metrics))

    def test_compose_published_ports_are_loopback_bound(self) -> None:
        compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
        services = compose.get("services", {})
        published = []
        for service in services.values():
            for item in service.get("ports", []) or []:
                if isinstance(item, dict):
                    published.append(str(item.get("host_ip") or ""))
                else:
                    published.append(str(item).split(":", 1)[0])
        self.assertTrue(published)
        self.assertTrue(all(host == "127.0.0.1" for host in published))

    def test_process_env_can_supply_settings_without_env_file(self) -> None:
        tmp, root, _env = self._bundle()
        with tmp:
            with patch.dict(os.environ, {"RAG_BUNDLE_DIR": str(root)}, clear=False):
                settings = load_settings()
            self.assertEqual(settings.retrieval_mode, "local")
            self.assertEqual(settings.bundle_dir, root.resolve())

    def test_readiness_requires_all_three_infrastructure_services(self) -> None:
        tmp, root, env = self._bundle()
        with tmp:
            env.write_text(
                f"RAG_BUNDLE_DIR={root}\n"
                "RAG_CLICKHOUSE_URL=http://127.0.0.1:9\n"
                "RAG_CLICKHOUSE_DATABASE=okf_rag\n"
                "RAG_CLICKHOUSE_EVENTS_TABLE=rag_events\n"
                "RAG_OPENSEARCH_URL=http://127.0.0.1:9\n"
                "RAG_OPENSEARCH_INDEX=okf-concepts\n"
                "RAG_QDRANT_URL=http://127.0.0.1:9\n"
                "RAG_QDRANT_COLLECTION=okf-concepts\n",
                encoding="utf-8",
            )
            settings = load_settings(env)
            with self.assertRaises(RagReadinessError) as ctx:
                check_rag_readiness(settings, timeout=0.05)
            message = str(ctx.exception)
            self.assertIn("clickhouse", message)
            self.assertIn("opensearch", message)
            self.assertIn("qdrant", message)

    def test_server_startup_fails_before_ready_when_infra_unreachable(self) -> None:
        env = {
            "RAG_BUNDLE_DIR": "okf",
            "RAG_CLICKHOUSE_URL": "http://127.0.0.1:9",
            "RAG_CLICKHOUSE_DATABASE": "okf_rag",
            "RAG_CLICKHOUSE_EVENTS_TABLE": "rag_events",
            "RAG_OPENSEARCH_URL": "http://127.0.0.1:9",
            "RAG_OPENSEARCH_INDEX": "okf-concepts",
            "RAG_QDRANT_URL": "http://127.0.0.1:9",
            "RAG_QDRANT_COLLECTION": "okf-concepts",
        }
        stderr = io.StringIO()
        with patch.dict(os.environ, env, clear=False), contextlib.redirect_stderr(stderr):
            code = server_main(["--bundle", "okf", "--transport", "http", "--host", "127.0.0.1", "--port", "0"])
        self.assertEqual(code, 2)
        self.assertIn("MCP startup readiness failed", stderr.getvalue())

    def test_hybrid_merge_uses_rank_fusion_not_global_score_scale(self) -> None:
        tmp, _root, env = self._bundle()
        with tmp:
            settings = load_settings(env)
            retriever = OKFRagRetriever(settings)
            chunk_a = OKFChunkRecord(
                chunk_id="a",
                concept_id="a",
                path="a.md",
                type="Function Requirement",
                status="draft",
                title="A",
                description="",
                tags=(),
                requirement_id=None,
                resource=None,
                source_path=None,
                heading_path=(),
                anchor="",
                line_start=1,
                line_end=1,
                content="keyword",
                contextualized_content="keyword",
                internal_links=(),
                linked_concept_ids=(),
                token_count=1,
                content_digest="a",
            )
            chunk_b = OKFChunkRecord(**{**chunk_a.to_dict(), "chunk_id": "b", "concept_id": "b", "path": "b.md", "title": "B", "content_digest": "b"})
            merged = retriever._merge_hits(
                [
                    OKFRetrievalHit(chunk=chunk_a, score=1000.0, reasons=("opensearch",)),
                    OKFRetrievalHit(chunk=chunk_b, score=0.99, reasons=("qdrant",)),
                ],
                limit=2,
                mode="hybrid",
            )
            self.assertEqual({hit.chunk.chunk_id for hit in merged}, {"a", "b"})
            self.assertGreater(merged[1].score, 0)

    def test_qdrant_refresh_recreates_collection_before_upsert(self) -> None:
        calls = []

        def fake_request(method, base_url, path="", **kwargs):
            calls.append((method, path, kwargs.get("expected")))

            class Response:
                def json(self):
                    return {}

            return Response()

        chunk = OKFChunkRecord(
            chunk_id="a",
            concept_id="a",
            path="a.md",
            type="Function Requirement",
            status="draft",
            title="A",
            description="",
            tags=(),
            requirement_id=None,
            resource=None,
            source_path=None,
            heading_path=(),
            anchor="",
            line_start=1,
            line_end=1,
            content="keyword",
            contextualized_content="keyword",
            internal_links=(),
            linked_concept_ids=(),
            token_count=1,
            content_digest="a",
        )
        with patch("okf_mcp.rag.storage.qdrant.request_json", fake_request):
            QdrantStore(url="http://example", collection="col", vector_size=8).index_chunks(
                (chunk,), build_embedding_provider(dimensions=8)
            )
        self.assertEqual(calls[0][0], "DELETE")
        self.assertEqual(calls[0][1], "collections/col")

    def test_opensearch_refresh_recreates_index_before_upsert(self) -> None:
        calls = []

        def fake_request(method, base_url, path="", **kwargs):
            calls.append((method, path, kwargs.get("expected")))

            class Response:
                def json(self):
                    return {}

            return Response()

        chunk = OKFChunkRecord(
            chunk_id="a",
            concept_id="a",
            path="a.md",
            type="Function Requirement",
            status="draft",
            title="A",
            description="",
            tags=(),
            requirement_id=None,
            resource=None,
            source_path=None,
            heading_path=(),
            anchor="",
            line_start=1,
            line_end=1,
            content="keyword",
            contextualized_content="keyword",
            internal_links=(),
            linked_concept_ids=(),
            token_count=1,
            content_digest="a",
        )
        with patch("okf_mcp.rag.storage.opensearch.request_json", fake_request):
            OpenSearchStore(url="http://example", index="idx").index_chunks((chunk,))
        self.assertEqual(calls[0][0], "DELETE")
        self.assertEqual(calls[0][1], "idx")


if __name__ == "__main__":
    unittest.main()
