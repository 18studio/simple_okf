# OKF Project Template Specification

Template version: `0.4`

## Purpose

This repository defines a minimal project template for maintaining knowledge in OKF format.

The template is intentionally limited to:

- OKF bundle structure;
- Markdown concepts with YAML frontmatter;
- a 7D process registry over OKF concept types;
- Markdown links as a graph;
- a FastMCP server for agent access to the bundle;
- a local OKF-aware RAG layer over concepts;
- a multi-app CLI and console commands in the `okf_mcp` package as fallback tools;
- a project skill for agents.

The template establishes the local filesystem contract for OKF and does not require external services to read or validate the bundle.

## Required template components

### 1. OKF bundle structure

The main bundle is located here:

```text
okf/
```

Base structure:

```text
okf/
├── index.md
├── log.md
├── documents/
├── requirements/
│   ├── functions/
│   ├── flows/
│   ├── rules/
│   └── access/
├── data/
│   └── entities/
├── api/
│   └── operations/
├── architecture/
│   └── adr/
└── ui/
    ├── ux/
    ├── design-system/
    └── uikit/
```

### 2. Concept format

Each concept is a Markdown file with YAML frontmatter.

Minimum OKF format:

```md
---
type: Reference
status: draft
---

Concept body.
```

Recommended format in this template:

```md
---
type: API Operation
status: draft
title: API-042 — Create project
description: Operation contract for project creation.
resource: system/API.md#api-042
tags: [api, operation, project]
timestamp: 2026-06-25T00:00:00Z
requirement_id: API-042
source_path: system/API.md
owner_document: API.md
---

# Overview

...
```

Rules:

- `type` is required and must be registered in the 7D type registry; unmapped
  concept types are validation errors.
- `status` is required. Allowed values are exactly `draft`, `to-review`,
  `not-valid`, `valid`, `rejected`, and `accepted`.
- `status` describes document/artifact review state, not runtime implementation
  progress.
- Recommended non-blocking status transitions are `draft` -> `to-review` ->
  (`valid` or `not-valid`), with `accepted` or `rejected` available for final
  product/stakeholder disposition. Tools validate only allowed values, not the
  transition path.
- `title`, `description`, and `timestamp` are recommended.
- unknown frontmatter fields are allowed; producer-specific fields must be
  preserved during editing.

### 3. 7D process registry

7D describes only the process stages for cloud-service feature elaboration. It
must not change the OKF concept format. Do not add 7D-specific fields such as
`process`, `stage`, `stage_order`, `artifact_key`, `gate_decision`, or `raci` to
concept frontmatter solely to support 7D.

The 7D stage for a concept is derived from its existing `type` value by a
separate registry table. The type remains the artifact name and does not embed
extra stage or ownership metadata. Every concept type used in this repository
must be present in the registry. An unmapped type is a validation error in both
OKF validation and 7D validation. Missing required lifecycle artifacts are
reported separately as lifecycle coverage gaps, not as OKF format errors.

Stages are sequential:

| Order | Stage | Meaning |
|---:|---|---|
| 1 | Discover | Problem, user, value, and investment discovery. |
| 2 | Design | Product behavior, architecture, constraints, scenarios, and readiness design. |
| 3 | Develop | Implementation and initial quality verification. |
| 4 | Deploy | Safe deployment to preview or another limited release contour. |
| 5 | Day-to-day | Real usage, feedback collection, and improvement planning. |
| 6 | Defend | Production-grade security, reliability, support, and GA readiness. |
| 7 | Decommission | Managed shutdown, migration, and final completion confirmation. |

Artifact-type registry:

| OKF `type` | 7D stage | Coverage required? | R — Responsible | A — Accountable | C — Consulted | I — Informed |
|---|---|---|---|---|---|---|
| Product Brief | Discover | yes | PM | PM | Support / GTM, Tech Lead | Sponsor |
| Go / No-Go to Design | Discover | yes | PM | Sponsor | Tech Lead, Security, SRE | Support / GTM |
| PRD | Design | yes | PM | PM | Tech Lead, QA, Support / GTM | Sponsor |
| Architecture & NFR | Design | yes | Tech Lead / Architect | Tech Lead / Architect | SRE, Security, QA | PM |
| Release Candidate | Develop | yes | Tech Lead / Engineering | Tech Lead | QA, Security, SRE | PM |
| Test Report | Develop | yes | QA | QA | Tech Lead, PM | SRE |
| Deployment & Rollback Plan | Deploy | yes | SRE | SRE | Tech Lead, QA, Security | PM |
| Preview Launch Package | Deploy | yes | PM | PM | QA, Support / GTM, SRE | Sponsor |
| Usage & Feedback Report | Day-to-day | yes | PM, Support / GTM | PM | SRE, QA, Tech Lead | Sponsor |
| Improvement Backlog | Day-to-day | yes | PM | PM | Tech Lead, QA, Support / GTM | Sponsor |
| GA Readiness Checklist | Defend | yes | PM | PM | Tech Lead, SRE, QA, Security, Support / GTM | Sponsor |
| Security & Reliability Approval | Defend | yes | Security, SRE | Security / SRE | Tech Lead, QA | PM, Sponsor |
| Decommission / Migration Plan | Decommission | yes | PM, Tech Lead, SRE | PM | Security, Support / GTM | Sponsor |
| Final Shutdown Report | Decommission | yes | PM, SRE | PM | Tech Lead, Security | Sponsor |
| Source Document | Discover | no | PM | PM | Tech Lead | Sponsor |
| Reference | Discover | no | PM | PM | Tech Lead | Sponsor |
| Glossary Term | Discover | no | PM | PM | Tech Lead | Sponsor |
| Gap | Discover | no | PM | PM | Tech Lead, QA | Sponsor |
| Requirement | Design | no | PM | PM | Tech Lead, QA | Sponsor |
| Function Requirement | Design | no | PM | PM | Tech Lead, QA | Sponsor |
| User Flow | Design | no | PM | PM | UX, Tech Lead, QA | Sponsor |
| Business Rule | Design | no | PM | PM | Tech Lead, QA | Sponsor |
| Access Rule | Design | no | PM | PM | Security, Tech Lead, QA | Sponsor |
| Data Entity | Design | no | Tech Lead | Tech Lead | PM, QA | Sponsor |
| API Operation | Design | no | Tech Lead | Tech Lead | PM, QA, Security | Sponsor |
| UX Screen | Design | no | UX | PM | Tech Lead, QA | Sponsor |
| UI Component | Design | no | UX | PM | Tech Lead, QA | Sponsor |
| Architecture Decision | Design | no | Tech Lead / Architect | Tech Lead / Architect | PM, SRE, Security, QA | Sponsor |
| Traceability Row | Design | no | PM, QA | PM | Tech Lead | Sponsor |
| Deployment Requirement | Deploy | no | SRE | SRE | Tech Lead, QA, Security | PM, Sponsor |

A feature's 7D progress is derived from the highest-order registered artifact
type among concepts linked to that feature. Reports and dashboards distinguish:

- validation errors: missing `type`, missing/invalid `status`, unmapped types,
  malformed frontmatter, and disallowed 7D-specific frontmatter guidance;
- lifecycle coverage gaps: required lifecycle artifact types with no matching
  concept. Optional/support mapped types do not create lifecycle coverage gaps.

The MCP server exposes 7D helper tools over this registry. These tools must read
normal OKF concepts and derive 7D state from `frontmatter.type` and Markdown
links.

### 4. Navigation files

`index.md` is a directory navigation file. It is not considered a concept.

`log.md` is a changelog. It is not considered a concept.

### 5. Links as graph

Relationships are expressed with Markdown links:

```md
Creates [Project](../../data/entities/project.md)
and is governed by [ACCESS-005](../../requirements/access/ACCESS-005.md).
```

The relationship type is defined by the surrounding text. Relative links are preferred for internal relationships.

### 6. Project Skills

OKF skill:

```text
.agents/skills/okf/SKILL.md
```

Use cases:

- create/edit OKF concepts;
- validate the OKF bundle;
- regenerate indexes;
- export canonical documents;
- generate graph JSON;
- navigate the bundle as an agent-readable knowledge base.

7D skill:

```text
.agents/skills/7d/SKILL.md
```

Use cases:

- validate 7D registry usage;
- generate reports by 7D lifecycle stage;
- derive a feature's 7D progress from linked OKF artifacts;
- guide creation or editing of 7D lifecycle artifacts without changing OKF
  concept format.

### 7. Skill templates and references

Project skills store only agent instructions, templates, and references:

```text
.agents/skills/okf/SKILL.md
.agents/skills/okf/templates/
.agents/skills/okf/references/
.agents/skills/7d/SKILL.md
```

Executable helper commands belong to the MCP package multi-app CLI:

```text
okf_mcp/__main__.py
okf_mcp/cli.py
```

The canonical CLI implementation is `okf_mcp/cli.py`. Installable console scripts
enter directly through `okf_mcp.cli:*` entrypoints.

### 8. OKF-aware RAG

The local RAG layer uses OKF concepts as its corpus. The runtime environment is loaded from this file:

```text
okf_mcp/rag/.env
```

The `okf_mcp/rag/.env` file must not be committed. An example is stored in:

```text
okf_mcp/rag/.env.example
```

Minimum local corpus variables:

```dotenv
RAG_BUNDLE_DIR=okf
RAG_ARTIFACTS_DIR=artifacts/rag
RAG_RETRIEVAL_RESULT_LIMIT=10
RAG_ANSWER_EVIDENCE_LIMIT=5
```

Required infrastructure settings for MCP server startup readiness:

```dotenv
RAG_CLICKHOUSE_URL=http://clickhouse:8123
RAG_CLICKHOUSE_USER=default
RAG_CLICKHOUSE_PASSWORD=
RAG_CLICKHOUSE_DATABASE=okf_rag
RAG_CLICKHOUSE_EVENTS_TABLE=rag_events
RAG_OPENSEARCH_URL=http://opensearch:9200
RAG_OPENSEARCH_USER=
RAG_OPENSEARCH_PASSWORD=
RAG_OPENSEARCH_INDEX=okf-concepts
RAG_QDRANT_URL=http://qdrant:6333
RAG_QDRANT_API_KEY=
RAG_QDRANT_COLLECTION=okf-concepts
```

Docker Compose uses service-name URLs. Host-side local CLI or server runs must
override these URLs in an uncommitted `.env` with host-reachable values such as
`http://127.0.0.1:8123`, `http://127.0.0.1:9200`, and
`http://127.0.0.1:6333`. Pure OKF commands such as validation, indexing, graph
generation, and `rag inspect` must not require live infrastructure. MCP server
startup must fail clearly if ClickHouse `/ping`, OpenSearch `/_cluster/health`,
or Qdrant `/readyz`/`/collections` is unreachable.

The RAG parser must:

- exclude `index.md` and `log.md`;
- preserve `concept_id`, `type`, `status`, `title`, `description`, `tags`, `requirement_id`, `resource`, and `source_path`;
- include frontmatter context in searchable chunks;
- resolve Markdown links between concepts as graph context.

### 9. FastMCP server

The MCP server is located here:

```text
okf_mcp/
```

The server provides tools for reading, searching, writing, and validating the OKF bundle:

```text
bundle_info
list_concepts
search_concepts
list_directory
read_concept
read_existing_doc
read_concept_raw
sample_rows
read_support_file
write_concept_doc
validate_bundle
seven_d_registry
seven_d_mapping_for_type
list_7d_artifact_concepts
seven_d_stage_report
seven_d_stage_report_markdown
seven_d_dashboard
seven_d_feature_status
validate_7d
generate_indexes
export_source_documents
build_graph
rag_readiness
rag_inspect_corpus
rag_parse_chunks
rag_refresh_index
rag_retrieve
rag_answer
rag_get_source
rag_concept_relationships
```

The server also provides resources:

```text
okf://bundle/info
okf://bundle/index
okf://bundle/graph
```

## Tooling contract

The primary agent-facing contract is MCP:

```text
python3 -m okf_mcp validate          -> validate_bundle
python3 -m okf_mcp indexes           -> generate_indexes
python3 -m okf_mcp export            -> export_source_documents
python3 -m okf_mcp graph             -> build_graph JSON to stdout by default; use --out/--html-out to write artifacts
python3 -m okf_mcp 7d ...            -> seven_d_stage_report / seven_d_dashboard / validate_7d / seven_d_feature_status
python3 -m okf_mcp rag ...           -> local OKF RAG inspect / refresh / retrieve
```

Multi-app CLI fallback:

```bash
python3 -m okf_mcp validate okf
python3 -m okf_mcp indexes okf
python3 -m okf_mcp export system --out okf
python3 -m okf_mcp graph okf --out artifacts/okf/graph.json --html-out artifacts/okf/graph.html
python3 -m okf_mcp rag inspect --pretty
python3 -m okf_mcp rag refresh --pretty
python3 -m okf_mcp rag retrieve "project access" --pretty
python3 -m okf_mcp 7d report --bundle okf
python3 -m okf_mcp 7d dashboard --bundle okf --out artifacts/7d-dashboard.html
```

MCP stdio server:

```bash
okf-mcp --bundle okf
```

MCP HTTP server:

```bash
okf-mcp --bundle okf --transport http --host 127.0.0.1 --port 8000
```
