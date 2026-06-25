---
name: okf-open-knowledge-format
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
docs/OKF_REFERENCE.md
```

For the vendored OKF spec/reference material, see:

```text
.agents/skills/okf/references/spec-v01.md
.agents/skills/okf/references/examples.md
.agents/skills/okf/references/conversion.md
```

## Project layout

Main bundle:

```text
okf/platform-system/
```

Local tools:

```text
scripts/validate_okf.py
scripts/generate_okf_indexes.py
scripts/export_okf.py
scripts/generate_okf_graph.py
```

Templates:

```text
templates/okf/concept.md
templates/okf/source-document.md
templates/okf/requirement.md
templates/okf/api-operation.md
templates/okf/data-entity.md
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

Project convention: prefer relative links for internal bundle links because local scripts validate and graph them reliably.

## Workflow: inspect existing bundle

1. Read `okf/platform-system/index.md`.
2. Read the nearest relevant directory `index.md`.
3. Open only the concepts needed for the task.
4. Follow Markdown links when relationships matter.
5. Use `docs/OKF_REFERENCE.md` for project conventions.

## Workflow: create a concept

1. Choose the correct directory under `okf/platform-system/`.
2. Choose a stable filename and concept ID.
3. Start from a template in `templates/okf/` when applicable.
4. Add frontmatter with at least `type`; preferably include `title`, `description`, `timestamp`, `tags`, and source fields.
5. Write concise Markdown body sections.
6. Add relative links to related concepts when relationship evidence exists.
7. Add citations only when there is a real source.
8. Run validation and regenerate indexes.

Commands:

```bash
python3 scripts/validate_okf.py okf/platform-system
python3 scripts/generate_okf_indexes.py okf/platform-system
python3 scripts/validate_okf.py okf/platform-system
```

## Workflow: edit a concept

1. Preserve existing unknown frontmatter keys.
2. Preserve stable IDs unless the user explicitly approves a rename.
3. Update links if files move.
4. Do not delete citations or schema details unless they are incorrect or obsolete.
5. Re-run validation.

## Workflow: export canonical Markdown docs

If the repository has a `system/` directory or another source directory of Markdown files, convert those files into `Source Document` concepts:

```bash
python3 scripts/export_okf.py --source system --out okf/platform-system
python3 scripts/generate_okf_indexes.py okf/platform-system
python3 scripts/validate_okf.py okf/platform-system
```

Generated concepts go under:

```text
okf/platform-system/documents/
```

Do not treat generated OKF output as more canonical than its source unless the user explicitly changes the ownership model.

## Workflow: generate graph

Build graph JSON from concepts and internal Markdown links:

```bash
python3 scripts/generate_okf_graph.py okf/platform-system --out okf/platform-system/graph.json
```

Use the graph for visualization, navigation, and connectivity checks. The graph is derived output and can be regenerated.

## Validation expectations

Before finishing OKF work, run:

```bash
python3 scripts/validate_okf.py okf/platform-system
```

When adding/removing/renaming concept files, also run:

```bash
python3 scripts/generate_okf_indexes.py okf/platform-system
python3 scripts/generate_okf_graph.py okf/platform-system --out okf/platform-system/graph.json
python3 scripts/validate_okf.py okf/platform-system
```

Report commands run and results.

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
