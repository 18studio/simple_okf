# OKF reference memory

Эта заметка сохраняет только релевантный контекст про OKF и инструменты вокруг него.

## OKF

**OKF — Open Knowledge Format**: минимальный переносимый формат знаний как набора обычных файлов:

```text
Markdown + YAML frontmatter + directories + Markdown links
```

Цель:

- человекочитаемость;
- удобство для LLM/агентов;
- Git-versioning;
- переносимость между системами;
- независимость от vendor/API/database/agent framework.

## Knowledge Bundle

Knowledge Bundle — самодостаточная директория с concept-документами.

```text
my_bundle/
├── index.md
├── datasets/
│   ├── index.md
│   └── sales.md
└── tables/
    ├── index.md
    ├── orders.md
    └── customers.md
```

## Concept

Concept — единица знания, Markdown-файл с YAML frontmatter.

Concept может описывать:

- источник-документ;
- требование;
- API operation;
- data entity;
- business/access rule;
- user flow;
- UI screen/component;
- ADR;
- deployment requirement;
- traceability/gap;
- glossary term.

Concept ID — путь файла внутри bundle без `.md`.

Например `api/operations/create-project.md` имеет concept ID `api/operations/create-project`.

## Concept frontmatter

Минимум по OKF:

```yaml
---
type: Reference
---
```

Рекомендуемый формат в этом шаблоне:

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

Неизвестные поля разрешены. Потребители OKF должны быть tolerant к расширениям.

## Links as graph

OKF не вводит отдельную graph schema. Связи выражаются Markdown-ссылками.

```md
This operation creates [Project](../../data/entities/project.md)
and is governed by [RULE-004](../../requirements/rules/RULE-004.md).
```

Тип отношения задаётся окружающим текстом: depends on, creates, governed by, implements, verifies, related to.

## index.md

`index.md` — навигационный файл, не обычный concept.

Назначение:

- progressive disclosure;
- агент сначала читает индекс;
- затем открывает нужные concepts;
- человек навигируется без специальной UI.

## log.md

`log.md` — опциональный журнал изменений в bundle или директории. Не concept.

## OKF reference agent

Upstream reference implementation находится в `GoogleCloudPlatform/knowledge-catalog/okf/src/reference_agent/`.

Возможности:

- генерация OKF bundle из BigQuery и web sources;
- web enrichment;
- генерация `index.md`;
- visualizer в self-contained `viz.html`;
- tools для чтения/записи concept-документов.

Установка из `okf/` upstream repo:

```bash
python3.13 -m venv .venv
.venv/bin/pip install --index-url https://pypi.org/simple/ -e '.[dev]'
```

BigQuery auth:

```bash
gcloud auth application-default login
gcloud config set project <project-id>
```

Gemini:

```bash
export GEMINI_API_KEY=...
```

или Vertex AI:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=<project-id>
export GOOGLE_CLOUD_LOCATION=<region>
```

Пример enrich:

```bash
.venv/bin/python -m reference_agent enrich \
  --source bq \
  --dataset bigquery-public-data.ga4_obfuscated_sample_ecommerce \
  --out ./bundles/ga4 \
  --no-web
```

Visualizer:

```bash
.venv/bin/python -m reference_agent visualize \
  --bundle ./bundles/ga4
```

## kcmd / Metadata as Code

`toolbox/mdcode/` — Metadata as Code tool. Это не OKF, но близкий инструмент вокруг metadata-as-files.

Назначение:

- локальный snapshot metadata;
- pull/push с Google Knowledge Catalog / Dataplex;
- YAML entries + Markdown sidecars;
- MCP server для агентов.

Snapshot structure:

```text
workspace/
├── catalog.yaml
└── catalog/
```

CLI:

```bash
kcmd init --bigquery-dataset <project.dataset> --pull
kcmd pull
kcmd push
kcmd push --validate-only
kcmd mcp --path /path/to/catalog-snapshot
```

Auth:

```bash
gcloud auth application-default login
gcloud config set project <project-id>
```

MCP tools, доступные в прочитанной версии:

- `list-entries`
- `lookup-entry`
- `modify-entry`

MCP config shape:

```json
{
  "mcpServers": {
    "kcmd": {
      "command": "kcmd",
      "args": ["mcp", "--path", "snapshots/kcmd/catalog-snapshot"]
    }
  }
}
```
