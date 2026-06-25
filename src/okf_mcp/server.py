from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from okf_mcp import __version__
from okf_mcp.okf import OKFBundle

DEFAULT_BUNDLE = os.environ.get("OKF_BUNDLE", "okr")


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

        `frontmatter.type` is required. If `merge_frontmatter` is true and the
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
    def build_graph(write: bool = False, out_path: str = "graph.json") -> dict[str, Any]:
        """Build the OKF concept/link graph.

        If `write` is true, also write the graph JSON inside the bundle at
        `out_path` (defaults to `graph.json`).
        """
        if write:
            return bundle.write_graph(out_path)
        return bundle.build_graph()

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
4. Call generate_indexes(), build_graph(write=True), and validate_bundle() after file changes.

Rules:
- frontmatter.type is required.
- Prefer title, description, timestamp, tags, resource when supported by evidence.
- Use relative Markdown links for internal OKF links.
- Do not invent domain facts, citations, schema details, or requirement IDs.

Source notes:
{source_notes}
"""

    return mcp


mcp = create_mcp()
