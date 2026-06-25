---
name: okf
description: >
  Create, validate, enrich, index, and navigate Open Knowledge Format (OKF)
  bundles — knowledge bases represented as Markdown files with YAML
  frontmatter. Use when the user mentions OKF, Open Knowledge Format,
  knowledge bundle, OKF bundle, agent-readable knowledge, LLM wiki, validate
  OKF, convert Markdown documents to OKF, generate OKF indexes, generate an
  OKF graph, or structure knowledge as local files for AI agent consumption.
metadata:
  version: "2.0"
  scope: local-okf-only
---

# Open Knowledge Format (OKF)

Use this skill for all work with OKF bundles in this repository.

OKF is a vendor-neutral file format for representing knowledge as:

```text
Markdown + YAML frontmatter + directories + Markdown links
```

No server, database, hosted service, or SDK is required to read the bundle. If a tool can read files, it can consume OKF.

For this project's compact reference, read:

```text
references/spec-v01.md
```

For the vendored OKF spec/reference material, see:

```text
references/spec-v01.md
references/examples.md
references/conversion.md
```

## Project layout

Main project-root bundle:

```text
okr/
```

OKF MCP server and fallback CLI scripts:

```text
src/okf_mcp/server.py
src/okf_mcp/scripts/validate_okf.py
src/okf_mcp/scripts/generate_okf_indexes.py
src/okf_mcp/scripts/export_okf.py
src/okf_mcp/scripts/generate_okf_graph.py
```

Use MCP tools first. The CLI scripts are fallback/manual tools only.

MCP tool mapping for former scripts:

```text
validate_okf.py           -> validate_bundle
generate_okf_indexes.py   -> generate_indexes
export_okf.py             -> export_source_documents
generate_okf_graph.py     -> build_graph(write=true, out_path="graph.json")
```

Templates bundled with this skill:

```text
templates/concept.md
templates/source-document.md
templates/requirement.md
templates/api-operation.md
templates/data-entity.md
```

## Core terminology

- **Bundle** — a directory tree of `.md` files; the unit of distribution.
- **Concept** — one Markdown file representing one unit of knowledge.
- **Concept ID** — file path within the bundle, minus `.md` suffix.
- **Frontmatter** — YAML block at the top of a concept file.
- **Body** — Markdown content after the frontmatter.
- **Link** — Markdown link expressing a relationship between concepts.
- **Citation** — link to a source backing a claim in the body.

## Reserved files

| File | Purpose | Concept? |
|------|---------|----------|
| `index.md` | Directory navigation / progressive disclosure | No |
| `log.md` | Change history | No |

Do not treat `index.md` or `log.md` as normal concepts.

## Frontmatter rules

Minimum conformant concept:

```md
---
type: Reference
---

Concept body.
```

Recommended frontmatter in this project:

```yaml
---
type: API Operation
title: API-042 — Create project
description: Operation contract for project creation.
resource: system/API.md#api-042
tags: [api, operation, project]
timestamp: 2026-06-25T00:00:00Z
requirement_id: API-042
source_path: system/API.md
owner_document: API.md
---
```

Rules:

1. `type` is required.
2. `title`, `description`, and `timestamp` are recommended.
3. Unknown frontmatter keys are allowed.
4. Preserve unknown fields when editing existing concepts.
5. Do not invent fields, links, citations, schema details, or requirement IDs.

## Common concept types

Use these types unless the user asks for another taxonomy:

```yaml
type: Source Document
type: Requirement
type: Function Requirement
type: User Flow
type: Business Rule
type: Access Rule
type: Data Entity
type: API Operation
type: UX Screen
type: UI Component
type: Architecture Decision
type: Deployment Requirement
type: Traceability Row
type: Gap
type: Glossary Term
type: Reference
```

Type values are free-form strings. Suggest a clear type, but do not reject a concept only because its type is unfamiliar.

## Links as graph

Relationships are normal Markdown links.

```md
This operation creates [Project](../../data/entities/project.md)
and is governed by [ACCESS-005](../../requirements/access/ACCESS-005.md).
```

The relationship type is expressed by surrounding prose, not by special link syntax.

Project convention: prefer relative links for internal bundle links because MCP validation and graph generation resolve them reliably.

## Workflow: use OKF MCP

For agent work, call the OKF MCP tools instead of running scripts whenever an MCP connection is available.

Preferred MCP tools:

- `read_support_file(path="index.md")` for navigation files.
- `list_directory(directory="")` for directory browsing.
- `list_concepts(...)` and `search_concepts(query, limit)` for discovery.
- `read_concept(concept_id)` / `read_existing_doc(concept_id)` / `read_concept_raw(concept_id)` for reading.
- `write_concept_doc(concept_id, frontmatter, body, ...)` for writing.
- `validate_bundle()` instead of `validate_okf.py`.
- `generate_indexes()` instead of `generate_okf_indexes.py`.
- `export_source_documents(source="system", force=false)` instead of `export_okf.py`.
- `build_graph(write=true, out_path="graph.json")` instead of `generate_okf_graph.py`.

If MCP is unavailable, use the fallback CLI scripts under `src/okf_mcp/scripts/`.

## Workflow: inspect existing bundle

1. Call MCP `read_support_file(path="index.md")` or read `okr/index.md`.
2. Call MCP `list_directory(...)` or read the nearest relevant directory `index.md`.
3. Open only the concepts needed for the task via MCP `read_concept(...)`/`read_concept_raw(...)` or files.
4. Follow Markdown links when relationships matter.
5. Use `references/spec-v01.md` for project conventions.

## Workflow: create a concept

1. Choose the correct directory under `okr/`.
2. Choose a stable filename and concept ID.
3. Start from a template in `templates/` when applicable.
4. Add frontmatter with at least `type`; preferably include `title`, `description`, `timestamp`, `tags`, and source fields.
5. Write concise Markdown body sections.
6. Add relative links to related concepts when relationship evidence exists.
7. Add citations only when there is a real source.
8. Run validation and regenerate indexes.

MCP calls after creating concepts:

```text
validate_bundle()
generate_indexes()
validate_bundle()
```

Fallback CLI commands:

```bash
python3 src/okf_mcp/scripts/validate_okf.py okr
python3 src/okf_mcp/scripts/generate_okf_indexes.py okr
python3 src/okf_mcp/scripts/validate_okf.py okr
```

## Workflow: edit a concept

1. Preserve existing unknown frontmatter keys.
2. Preserve stable IDs unless the user explicitly approves a rename.
3. Update links if files move.
4. Do not delete citations or schema details unless they are incorrect or obsolete.
5. Re-run validation.

## Workflow: export canonical Markdown docs

If the repository has a `system/` directory or another source directory of Markdown files, convert those files into `Source Document` concepts via MCP:

```text
export_source_documents(source="system", force=false)
generate_indexes()
validate_bundle()
```

Fallback CLI commands:

```bash
python3 src/okf_mcp/scripts/export_okf.py --source system --out okr
python3 src/okf_mcp/scripts/generate_okf_indexes.py okr
python3 src/okf_mcp/scripts/validate_okf.py okr
```

Generated concepts go under:

```text
okr/documents/
```

Do not treat generated OKF output as more canonical than its source unless the user explicitly changes the ownership model.

## Workflow: generate graph

Build graph JSON from concepts and internal Markdown links via MCP:

```text
build_graph(write=true, out_path="graph.json")
```

Fallback CLI command:

```bash
python3 src/okf_mcp/scripts/generate_okf_graph.py okr --out okr/graph.json
```

Use the graph for visualization, navigation, and connectivity checks. The graph is derived output and can be regenerated.

## Validation expectations

Before finishing OKF work, run MCP validation:

```text
validate_bundle()
```

When adding/removing/renaming concept files, also run MCP index and graph generation:

```text
generate_indexes()
build_graph(write=true, out_path="graph.json")
validate_bundle()
```

Fallback CLI commands:

```bash
python3 src/okf_mcp/scripts/generate_okf_indexes.py okr
python3 src/okf_mcp/scripts/generate_okf_graph.py okr --out okr/graph.json
python3 src/okf_mcp/scripts/validate_okf.py okr
```

Report MCP tool calls or fallback commands run and results.

## Guardrails

1. Never invent domain facts.
2. Preserve unknown fields.
3. Do not impose a rigid taxonomy beyond project conventions.
4. Prefer minimal, accurate concepts over padded concepts.
5. Broken links may represent missing knowledge, but this project's validator reports them as errors for local quality.
6. Ask before making broad directory or ownership changes.
7. Keep this template local-file-first and OKF-focused.

## Output format for created bundles

When presenting a new or changed OKF bundle, summarize:

1. directory tree;
2. files changed;
3. validation commands and results;
4. remaining gaps or open questions.
