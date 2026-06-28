# OKF Project Template Specification

Версия шаблона: `0.3`

## Назначение

Этот репозиторий задаёт минимальный шаблон проекта для ведения знаний в формате OKF.

Шаблон намеренно ограничен:

- OKF bundle structure;
- Markdown concepts с YAML frontmatter;
- Markdown links как graph;
- FastMCP server для агентного доступа к bundle;
- локальный OKF-aware RAG layer поверх concepts;
- CLI scripts внутри MCP-пакета как fallback;
- project skill для агентов.

Шаблон фиксирует локальный файловый контракт OKF и не требует внешних сервисов для чтения или проверки bundle.

## Обязательные части шаблона

### 1. OKF bundle structure

Основной bundle расположен здесь:

```text
okf/
```

Базовая структура:

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

Каждый concept — Markdown-файл с YAML frontmatter.

Минимум по OKF:

```md
---
type: Reference
---

Concept body.
```

Рекомендуемый формат в этом шаблоне:

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

Правила:

- `type` обязателен;
- `title`, `description`, `timestamp` рекомендуются;
- неизвестные frontmatter-поля разрешены;
- producer-specific поля должны сохраняться при редактировании.

### 3. Navigation files

`index.md` — навигационный файл директории. Не считается concept.

`log.md` — changelog. Не считается concept.

### 4. Links as graph

Связи задаются Markdown-ссылками:

```md
Creates [Project](../../data/entities/project.md)
and is governed by [ACCESS-005](../../requirements/access/ACCESS-005.md).
```

Тип отношения задаётся окружающим текстом. Для внутренних связей предпочтительны относительные ссылки.

### 5. OKF Skill

Project skill:

```text
.agents/skills/okf/SKILL.md
```

Use cases:

- create/edit OKF concepts;
- validate OKF bundle;
- regenerate indexes;
- export canonical docs;
- generate graph JSON;
- navigate bundle as an agent-readable knowledge base.

### 6. Skill templates and references

Skill хранит только инструкции, шаблоны и reference-материалы:

```text
.agents/skills/okf/SKILL.md
.agents/skills/okf/templates/
.agents/skills/okf/references/
```

Функции бывших skill scripts перенесены в MCP server/tools. CLI fallback scripts лежат здесь:

```text
mcp/scripts/
```

### 7. OKF-aware RAG

Локальный RAG layer использует OKF concepts как corpus. Реальное окружение загружается из файла:

```text
mcp/rag/.env
```

Файл `mcp/rag/.env` не должен коммититься. Пример хранится в:

```text
mcp/rag/.env.example
```

Минимальные переменные:

```dotenv
RAG_BUNDLE_DIR=okf
RAG_ARTIFACTS_DIR=mcp/rag/artifacts
RAG_RETRIEVAL_RESULT_LIMIT=10
RAG_ANSWER_EVIDENCE_LIMIT=5
```

RAG parser обязан:

- исключать `index.md` и `log.md`;
- сохранять `concept_id`, `type`, `title`, `description`, `tags`, `requirement_id`, `resource`, `source_path`;
- включать frontmatter context в searchable chunks;
- резолвить Markdown-ссылки между concepts как graph context.

### 8. FastMCP server

MCP server расположен здесь:

```text
mcp/
```

Server предоставляет tools для чтения, поиска, записи и проверки OKF bundle:

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

Server также предоставляет resources:

```text
okf://bundle/info
okf://bundle/index
okf://bundle/graph
```

## Tooling contract

Primary agent-facing contract is MCP:

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
