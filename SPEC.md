# OKF Project Template Specification

Template version: `0.3`

## Purpose

This repository defines a minimal project template for maintaining knowledge in OKF format.

The template is intentionally limited to:

- OKF bundle structure;
- Markdown concepts with YAML frontmatter;
- Markdown links as a graph;
- a FastMCP server for agent access to the bundle;
- a local OKF-aware RAG layer over concepts;
- CLI scripts inside the MCP package as a fallback;
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
---

Concept body.
```

Recommended format in this template:

```md
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

# Overview

...
```

Rules:

- `type` is required;
- `title`, `description`, and `timestamp` are recommended;
- unknown frontmatter fields are allowed;
- producer-specific fields must be preserved during editing.

### 3. Navigation files

`index.md` is a directory navigation file. It is not considered a concept.

`log.md` is a changelog. It is not considered a concept.

### 4. Links as graph

Relationships are expressed with Markdown links:

```md
Creates [Project](../../data/entities/project.md)
and is governed by [ACCESS-005](../../requirements/access/ACCESS-005.md).
```

The relationship type is defined by the surrounding text. Relative links are preferred for internal relationships.

### 5. OKF Skill

Project skill:

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

### 6. Skill templates and references

The skill stores only instructions, templates, and reference materials:

```text
.agents/skills/okf/SKILL.md
.agents/skills/okf/templates/
.agents/skills/okf/references/
```

The functionality of the former skill scripts has been moved to the MCP server/tools. CLI fallback scripts are located here:

```text
mcp/scripts/
```

### 7. OKF-aware RAG

The local RAG layer uses OKF concepts as its corpus. The runtime environment is loaded from this file:

```text
mcp/rag/.env
```

The `mcp/rag/.env` file must not be committed. An example is stored in:

```text
mcp/rag/.env.example
```

Minimum variables:

```dotenv
RAG_BUNDLE_DIR=okf
RAG_ARTIFACTS_DIR=mcp/rag/artifacts
RAG_RETRIEVAL_RESULT_LIMIT=10
RAG_ANSWER_EVIDENCE_LIMIT=5
```

The RAG parser must:

- exclude `index.md` and `log.md`;
- preserve `concept_id`, `type`, `title`, `description`, `tags`, `requirement_id`, `resource`, and `source_path`;
- include frontmatter context in searchable chunks;
- resolve Markdown links between concepts as graph context.

### 8. FastMCP server

The MCP server is located here:

```text
mcp/
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
generate_indexes
export_source_documents
build_graph
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
validate_okf.py           -> validate_bundle
generate_okf_indexes.py   -> generate_indexes
export_okf.py             -> export_source_documents
generate_okf_graph.py     -> build_graph(write=true, out_path="graph.json")
```

CLI fallback:

```bash
python3 mcp/scripts/validate_okf.py okf
python3 mcp/scripts/generate_okf_indexes.py okf
python3 mcp/scripts/export_okf.py --source system --out okf
python3 mcp/scripts/generate_okf_graph.py okf --out okf/graph.json
python3 mcp/scripts/inspect_rag_corpus.py --pretty
python3 mcp/scripts/refresh_rag_index.py --pretty
python3 mcp/scripts/rag_retrieve.py "project access" --pretty
```

MCP stdio server:

```bash
okf-mcp --bundle okf
```

MCP HTTP server:

```bash
okf-mcp --bundle okf --transport http --host 127.0.0.1 --port 8000
```
