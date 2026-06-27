---
name: okf
description: >
  Work with Open Knowledge Format (OKF) bundles. Use when the user mentions
  OKF, Open Knowledge Format, knowledge bundle, OKF bundle, agent-readable
  knowledge, LLM wiki, validation, indexing, graph generation, search,
  reading, or writing OKF concepts. All OKF information and operations must
  go through the MCP server named simple-okf from .mcp.json.
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

Project OKF content must be read and changed through the MCP server named `simple-okf`. Use local reference files only for format rules, not as the source of project knowledge.

## MCP entrypoint

Use the MCP server named:

```text
simple-okf
```

`simple-okf` is configured in `.mcp.json`. Call OKF tools by this MCP name. Do not use local OKF files or script paths as the source of project information.

Core operations:

```text
simple-okf.read_support_file(...)
simple-okf.list_directory(...)
simple-okf.list_concepts(...)
simple-okf.search_concepts(...)
simple-okf.read_concept(...)
simple-okf.write_concept_doc(...)
simple-okf.validate_bundle()
simple-okf.generate_indexes()
simple-okf.export_source_documents(...)
simple-okf.build_graph(write=true, out_path="graph.json", html=true, html_out_path="graph.html")
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

For agent work, call the MCP server named `simple-okf`.

Preferred `simple-okf` MCP tools:

- `simple-okf.read_support_file(path="index.md")` for navigation.
- `simple-okf.list_directory(directory="")` for directory browsing.
- `simple-okf.list_concepts(...)` and `simple-okf.search_concepts(query, limit)` for discovery.
- `simple-okf.read_concept(concept_id)` / `simple-okf.read_existing_doc(concept_id)` / `simple-okf.read_concept_raw(concept_id)` for reading.
- `simple-okf.write_concept_doc(concept_id, frontmatter, body, ...)` for writing.
- `simple-okf.validate_bundle()` for validation.
- `simple-okf.generate_indexes()` for indexes.
- `simple-okf.export_source_documents(source="system", force=false)` for source-document import.
- `simple-okf.build_graph(write=true, out_path="graph.json", html=true, html_out_path="graph.html")` for graph JSON and HTML report generation.

If `simple-okf` is unavailable, report that MCP is unavailable instead of silently switching to local files.

## Workflow: inspect existing bundle

1. Call `simple-okf.read_support_file(path="index.md")`.
2. Call `simple-okf.list_directory(...)`.
3. Open only the concepts needed for the task via `simple-okf.read_concept(...)` or `simple-okf.read_concept_raw(...)`.
4. Follow Markdown links when relationships matter by reading linked concepts through `simple-okf`.

## Workflow: create a concept

1. Discover the correct location with `simple-okf.list_directory(...)` and `simple-okf.list_concepts(...)`.
2. Choose a stable concept ID.
3. Add frontmatter with at least `type`; preferably include `title`, `description`, `timestamp`, `tags`, and source fields.
4. Write concise Markdown body sections.
5. Add relative links to related concepts when relationship evidence exists.
6. Add citations only when there is a real source.
7. Write via `simple-okf.write_concept_doc(...)`.
8. Run `simple-okf.generate_indexes()` and `simple-okf.validate_bundle()`.

## Workflow: edit a concept

1. Preserve existing unknown frontmatter keys.
2. Preserve stable IDs unless the user explicitly approves a rename.
3. Update links if concept IDs move.
4. Do not delete citations or schema details unless they are incorrect or obsolete.
5. Write via `simple-okf.write_concept_doc(...)` and run `simple-okf.validate_bundle()`.

## Workflow: export canonical Markdown docs

Convert source Markdown documents into `Source Document` concepts via `simple-okf`:

```text
simple-okf.export_source_documents(source="system", force=false)
simple-okf.generate_indexes()
simple-okf.validate_bundle()
```

Do not treat generated OKF output as more canonical than its source unless the user explicitly changes the ownership model.

## Workflow: generate graph

Build graph JSON and HTML report from concepts and internal Markdown links via `simple-okf`:

```text
simple-okf.build_graph(write=true, out_path="graph.json", html=true, html_out_path="graph.html")
```

Use the graph report for visualization, navigation, and connectivity checks. The graph is derived output and can be regenerated.

## Validation expectations

Before finishing OKF work, run validation through `simple-okf`:

```text
simple-okf.validate_bundle()
```

When adding/removing/renaming concepts, also run:

```text
simple-okf.generate_indexes()
simple-okf.build_graph(write=true, out_path="graph.json", html=true, html_out_path="graph.html")
simple-okf.validate_bundle()
```

Report `simple-okf` MCP tool calls and results.

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
