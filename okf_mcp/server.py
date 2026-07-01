from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

if __package__:
    from . import __version__
    from .okf import OKFBundle
    from .rag import OKFRagRetriever, OKFRagCorpus, check_rag_readiness, load_settings
else:  # Allows running this file directly.
    import sys

    project_root = Path(__file__).resolve().parents[1]
    project_root_text = str(project_root)
    if project_root_text not in sys.path:
        sys.path.insert(0, project_root_text)

    from okf_mcp import __version__
    from okf_mcp.okf import OKFBundle
    from okf_mcp.rag import OKFRagRetriever, OKFRagCorpus, check_rag_readiness, load_settings

DEFAULT_BUNDLE = os.environ.get("OKF_BUNDLE", "okf")


def create_mcp(bundle_root: str | Path = DEFAULT_BUNDLE) -> FastMCP:
    """Create a FastMCP server for a local OKF bundle."""

    bundle = OKFBundle(bundle_root)
    mcp = FastMCP("okf-mcp")

    def _bundle_info() -> dict[str, Any]:
        validation = bundle.validate()
        graph = bundle.build_graph()
        return {
            "server": "okf-mcp",
            "version": __version__,
            "bundle": str(bundle.root),
            "concept_count": validation["concept_count"],
            "node_count": graph["node_count"],
            "edge_count": graph["edge_count"],
            "valid": validation["ok"],
            "warnings": validation["warnings"],
            "errors": validation["errors"],
        }

    @mcp.tool
    def bundle_info() -> dict[str, Any]:
        """Return the active OKF bundle path and basic counts."""
        return _bundle_info()

    @mcp.tool
    def list_concepts(
        type_filter: str | None = None,
        tag: str | None = None,
        query: str | None = None,
        include_snippet: bool = False,
    ) -> list[dict[str, Any]]:
        """List OKF concept files with optional type, tag, and text filters.

        Reserved support files (`index.md`, `log.md`) are not returned.
        Concept IDs are bundle-relative paths without the `.md` suffix.
        """
        return bundle.list_concepts(
            type_filter=type_filter,
            tag=tag,
            query=query,
            include_snippet=include_snippet,
        )

    @mcp.tool
    def search_concepts(query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search concept IDs, frontmatter, tags, descriptions, and bodies."""
        return bundle.search_concepts(query, limit=limit)

    @mcp.tool
    def list_directory(directory: str = "") -> dict[str, Any]:
        """List child directories, concepts, and support files under a bundle directory."""
        return bundle.list_directory(directory)

    @mcp.tool
    def read_concept(concept_id: str, include_body: bool = True) -> dict[str, Any]:
        """Read a parsed OKF concept by concept ID.

        Returns frontmatter and, by default, the Markdown body.
        """
        return bundle.read_concept(concept_id, include_body=include_body)

    @mcp.tool
    def read_existing_doc(concept_id: str) -> dict[str, Any] | None:
        """Return an existing OKF document or null if it does not exist.

        This mirrors the reference agent's `read_existing_doc` tool and is
        useful before calling `write_concept_doc` to avoid blind overwrites.
        """
        try:
            doc = bundle.read_concept(concept_id, include_body=True)
        except Exception:
            return None
        return {"frontmatter": doc["frontmatter"], "body": doc.get("body", "")}

    @mcp.tool
    def read_concept_raw(concept_id: str) -> str:
        """Read the raw Markdown source for an OKF concept by concept ID."""
        return bundle.read_raw(concept_id)

    @mcp.tool
    def sample_rows(concept_id: str, n: int = 5) -> dict[str, Any]:
        """Reference-agent compatibility stub for data sources.

        This filesystem OKF MCP does not connect to a database, so sampling is
        unsupported and always returns an explanatory note.
        """
        return {
            "rows": [],
            "note": f"Sampling is not supported by this OKF filesystem MCP for concept {concept_id!r}.",
        }

    @mcp.tool
    def read_support_file(path: str = "index.md") -> dict[str, Any]:
        """Read a support file from the bundle, for example `index.md` or `log.md`."""
        return bundle.read_support_file(path)

    @mcp.tool
    def write_concept_doc(
        concept_id: str,
        frontmatter: dict[str, Any],
        body: str,
        overwrite: bool = True,
        merge_frontmatter: bool = True,
    ) -> dict[str, Any]:
        """Write an OKF concept Markdown file.

        `frontmatter.type` and `frontmatter.status` are required and `type` must
        be mapped in the 7D registry. If `merge_frontmatter` is true and the
        concept already exists, omitted existing keys are preserved while passed
        keys are updated. `timestamp` is filled automatically when omitted.
        """
        return bundle.write_concept(
            concept_id,
            frontmatter,
            body,
            overwrite=overwrite,
            merge_frontmatter=merge_frontmatter,
        )

    @mcp.tool
    def validate_bundle() -> dict[str, Any]:
        """Validate the active OKF bundle and return errors/warnings."""
        return bundle.validate()

    @mcp.tool
    def seven_d_registry() -> dict[str, Any]:
        """Return the 7D stage and OKF artifact-type mapping registry."""
        return bundle.seven_d_registry()

    @mcp.tool
    def seven_d_mapping_for_type(type_name: str) -> dict[str, Any] | None:
        """Return 7D stage and responsibility mapping for an OKF concept type."""
        return bundle.seven_d_mapping_for_type(type_name)

    @mcp.tool
    def list_7d_artifact_concepts(stage: str | None = None) -> list[dict[str, Any]]:
        """List concepts whose `type` is registered in the 7D artifact table."""
        return bundle.list_7d_artifact_concepts(stage=stage)

    @mcp.tool
    def seven_d_stage_report(stage: str | None = None) -> dict[str, Any]:
        """Generate a structured report for 7D lifecycle stage coverage.

        When `stage` is omitted, returns all seven stages. Stage may be either a
        registry key such as `discover` or a display name such as `Discover`.
        """
        return bundle.seven_d_stage_report(stage=stage)

    @mcp.tool
    def seven_d_stage_report_markdown(stage: str | None = None) -> str:
        """Generate a compact Markdown report for 7D lifecycle stage coverage."""
        return bundle.render_seven_d_stage_report(stage=stage)

    @mcp.tool
    def seven_d_dashboard(
        write: bool = True,
        out_path: str = "artifacts/7d-dashboard.html",
        include_html: bool = False,
    ) -> dict[str, Any]:
        """Generate an interactive 7D Kanban dashboard.

        The dashboard is a self-contained HTML view with one column per 7D
        stage. Concept cards open a readonly modal with OKF metadata,
        frontmatter, and document body. When `write` is true, the HTML file is
        written under the repository `artifacts/` directory at `out_path`.
        """
        if write:
            result = bundle.write_seven_d_dashboard_html(out_path)
            if include_html:
                result["html"] = bundle.render_seven_d_dashboard_html()
            return result

        report = bundle.seven_d_stage_report()
        result = {
            "stage_count": report.get("stage_count", 0),
            "registered_artifact_type_count": report.get("registered_artifact_type_count", 0),
            "mapped_concept_count": report.get("mapped_concept_count", 0),
            "gap_count": report.get("gap_count", 0),
            "validation": report.get("validation", {}),
        }
        if include_html:
            result["html"] = bundle.render_seven_d_dashboard_html()
        return result

    @mcp.tool
    def seven_d_feature_status(concept_id: str) -> dict[str, Any]:
        """Derive a concept's 7D progress from linked artifact concept types."""
        return bundle.seven_d_feature_status(concept_id)

    @mcp.tool
    def validate_7d() -> dict[str, Any]:
        """Validate 7D registry usage without requiring 7D-specific frontmatter."""
        return bundle.validate_7d()

    @mcp.tool
    def generate_indexes() -> dict[str, Any]:
        """Regenerate index.md files for every directory in the OKF bundle."""
        return bundle.generate_indexes()

    @mcp.tool
    def export_source_documents(source: str = "system", force: bool = False) -> dict[str, Any]:
        """Export Markdown files from a source directory as OKF Source Document concepts.

        Generated concepts are written under `<bundle>/documents/`. Existing
        generated concepts are skipped unless `force` is true.
        """
        return bundle.export_source_documents(source, force=force)

    @mcp.tool
    def build_graph(
        write: bool = False,
        out_path: str = "artifacts/okf/graph.json",
        html: bool = False,
        html_out_path: str = "artifacts/okf/graph.html",
    ) -> dict[str, Any]:
        """Build the OKF concept/link graph.

        If `write` is true, also write the graph JSON under repository
        `artifacts/` at `out_path`. If `html` is true, also write a
        self-contained HTML graph report at `html_out_path`.
        """
        graph = bundle.write_graph(out_path) if write else bundle.build_graph()
        if html:
            graph_for_html = {
                key: graph[key]
                for key in ("bundle", "node_count", "edge_count", "nodes", "edges")
                if key in graph
            }
            graph["html_report"] = bundle.write_graph_html(html_out_path, graph=graph_for_html)
        return graph

    def _rag_settings_and_retriever() -> tuple[Any, OKFRagRetriever]:
        settings = load_settings()
        return settings, OKFRagRetriever(settings)

    @mcp.tool
    def rag_readiness(timeout_seconds: float = 2.0) -> dict[str, Any]:
        """Check configured ClickHouse, OpenSearch, and Qdrant readiness."""
        settings = load_settings()
        return check_rag_readiness(settings, timeout=timeout_seconds)

    @mcp.tool
    def rag_inspect_corpus(correlation_id: str | None = None) -> dict[str, Any]:
        """Inspect the OKF RAG corpus configured in `okf_mcp/rag/.env`.

        This local tool reads `RAG_BUNDLE_DIR` from `okf_mcp/rag/.env` and treats OKF
        concepts as documents. Support files (`index.md`, `log.md`) are not
        included.
        """
        settings = load_settings()
        inventory = OKFRagCorpus(settings.bundle_dir).inspect(correlation_id or "rag-inspect")
        return {
            "env_file": str(settings.env_file),
            "artifacts_dir": str(settings.artifacts_dir),
            **inventory.to_dict(),
        }

    @mcp.tool
    def rag_parse_chunks() -> dict[str, Any]:
        """Parse the configured OKF bundle into local RAG chunks for diagnostics."""
        settings, retriever = _rag_settings_and_retriever()
        parsed = retriever.parse()
        return {
            "env_file": str(settings.env_file),
            "artifacts_dir": str(settings.artifacts_dir),
            **parsed.to_dict(),
        }

    @mcp.tool
    def rag_refresh_index(mode: str | None = None) -> dict[str, Any]:
        """Write local and optional infrastructure indexes for the configured OKF RAG corpus."""
        settings, retriever = _rag_settings_and_retriever()
        return retriever.refresh_index(settings.artifacts_dir, mode=mode)

    @mcp.tool
    def rag_retrieve(
        query: str,
        limit: int | None = None,
        type_filter: str | None = None,
        tag: str | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve OKF concepts/chunks with local, keyword, semantic, or hybrid search."""
        settings, retriever = _rag_settings_and_retriever()
        return retriever.retrieve(
            query,
            limit=limit or settings.retrieval_result_limit,
            type_filter=type_filter,
            tag=tag,
            mode=mode,
        )

    @mcp.tool
    def rag_answer(question: str, limit: int | None = None, mode: str | None = None) -> dict[str, Any]:
        """Return a deterministic extractive answer with OKF citations and optional evaluation."""
        settings, retriever = _rag_settings_and_retriever()
        return retriever.answer(question, limit=limit or settings.answer_evidence_limit, mode=mode)

    @mcp.tool
    def rag_get_source(
        concept_id: str,
        line_start: int | None = None,
        line_end: int | None = None,
    ) -> dict[str, Any]:
        """Return source lines for an OKF concept citation."""
        _, retriever = _rag_settings_and_retriever()
        return retriever.get_source(concept_id, line_start=line_start, line_end=line_end)

    @mcp.tool
    def rag_concept_relationships(concept_id: str, depth: int = 1) -> dict[str, Any]:
        """Return incoming/outgoing OKF graph relationships for a concept."""
        _, retriever = _rag_settings_and_retriever()
        return retriever.concept_relationships(concept_id, depth=depth)

    @mcp.resource("okf://bundle/info", mime_type="application/json")
    def bundle_info_resource() -> str:
        """Active OKF bundle metadata."""
        return json.dumps(_bundle_info(), ensure_ascii=False)

    @mcp.resource("okf://bundle/index", mime_type="text/markdown")
    def bundle_index_resource() -> str:
        """Root index.md from the active OKF bundle."""
        return bundle.read_support_file("index.md")["text"]

    @mcp.resource("okf://bundle/graph", mime_type="application/json")
    def bundle_graph_resource() -> str:
        """Derived OKF graph JSON for the active bundle."""
        return json.dumps(bundle.build_graph(), ensure_ascii=False)

    @mcp.prompt
    def okf_concept_writer(concept_id: str, source_notes: str = "") -> str:
        """Prompt an LLM client to create or refine one OKF concept via this MCP."""
        return f"""You are writing one Open Knowledge Format (OKF) concept.

Target concept_id: {concept_id}

Workflow:
1. Call read_existing_doc(concept_id) first. If it exists, preserve useful body text and unknown frontmatter keys.
2. Use list_concepts() to discover valid cross-link targets.
3. Write exactly one concept with write_concept_doc(concept_id, frontmatter, body).
4. Call generate_indexes(), build_graph(write=True, html=True), and validate_bundle() after file changes.

Rules:
- frontmatter.type and frontmatter.status are required.
- Use only allowed status values: draft, to-review, not-valid, valid, rejected, accepted.
- Use a type mapped by the 7D registry; do not add 7D-specific frontmatter.
- Prefer title, description, timestamp, tags, resource when supported by evidence.
- Use relative Markdown links for internal OKF links.
- Do not invent domain facts, citations, schema details, or requirement IDs.

Source notes:
{source_notes}
"""

    return mcp


mcp = create_mcp()
