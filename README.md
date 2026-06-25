# Simple OKF Template

Шаблон проекта для ведения знаний в формате **OKF — Open Knowledge Format**.

OKF здесь используется как переносимый knowledge bundle:

```text
Markdown + YAML frontmatter + directories + Markdown links
```

Проект содержит OKF-формат и локальные инструменты для работы с ним:

1. структуру директории под OKF bundle;
2. FastMCP-сервер для чтения/поиска/записи OKF concepts;
3. skill для агентов;
4. шаблоны OKF concept-файлов внутри skill;
5. CLI-скрипты внутри MCP-пакета для fallback/ручного запуска.

Шаблон сфокусирован на локальных файлах, Git-friendly workflow и агентной навигации по Markdown-ссылкам.

## Структура

```text
.
├── okr/                         # основной OKF bundle
├── src/okf_mcp/                 # FastMCP server, OKF helpers, CLI scripts
│   └── scripts/
├── pyproject.toml
├── README.md
├── SPEC.md
└── .agents/skills/okf/          # skill, templates, references для OKF
    ├── SKILL.md
    ├── references/
    └── templates/
```

## Быстрый старт

Проверить OKF bundle:

```bash
python3 src/okf_mcp/scripts/validate_okf.py okr
```

Сгенерировать `index.md` по директориям:

```bash
python3 src/okf_mcp/scripts/generate_okf_indexes.py okr
```

Экспортировать документы из `system/`, если такая директория есть:

```bash
python3 src/okf_mcp/scripts/export_okf.py --source system --out okr
```

Построить JSON-граф concepts и Markdown-ссылок:

```bash
python3 src/okf_mcp/scripts/generate_okf_graph.py okr --out okr/graph.json
```

## FastMCP server

Установить зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Запустить MCP по stdio:

```bash
okf-mcp --bundle okr
# или
python3 -m okf_mcp --bundle okr
```

Запустить HTTP transport:

```bash
okf-mcp --bundle okr --transport http --host 127.0.0.1 --port 8000
```

Также можно запускать через FastMCP CLI:

```bash
OKF_BUNDLE=okr fastmcp run src/okf_mcp/server.py:mcp
OKF_BUNDLE=okr fastmcp run src/okf_mcp/server.py:mcp --transport http --port 8000
```

MCP предоставляет tools:

- `bundle_info`
- `list_concepts`
- `search_concepts`
- `list_directory`
- `read_concept`
- `read_existing_doc`
- `read_concept_raw`
- `sample_rows` compatibility stub
- `read_support_file`
- `write_concept_doc`
- `validate_bundle`
- `generate_indexes`
- `export_source_documents`
- `build_graph`

И resources:

- `okf://bundle/info`
- `okf://bundle/index`
- `okf://bundle/graph`

## OKF правила проекта

- `okr/` — основной bundle.
- Каждый concept — Markdown-файл с YAML frontmatter.
- `index.md` — навигационный файл, не concept.
- `log.md` — опциональный журнал изменений, не concept.
- Минимально обязательное поле OKF: `type`.
- В этом шаблоне дополнительно рекомендуется: `title`, `description`, `timestamp`.
- Связи выражаются Markdown-ссылками между concept-файлами.
- Для graph tooling и валидатора предпочтительны относительные ссылки.

## Шаблоны concepts

```text
.agents/skills/okf/templates/concept.md
.agents/skills/okf/templates/source-document.md
.agents/skills/okf/templates/requirement.md
.agents/skills/okf/templates/api-operation.md
.agents/skills/okf/templates/data-entity.md
```

## Локальные инструменты fallback

Основной агентный путь — MCP tools выше. Эти CLI-скрипты лежат внутри MCP-пакета и нужны для ручного запуска или fallback, когда MCP недоступен.

Соответствие MCP tools:

```text
validate_okf.py           -> validate_bundle
generate_okf_indexes.py   -> generate_indexes
export_okf.py             -> export_source_documents
generate_okf_graph.py     -> build_graph(write=true)
```

## CLI scripts

```text
src/okf_mcp/scripts/validate_okf.py           # проверяет frontmatter, type, ссылки, дубликаты requirement_id
src/okf_mcp/scripts/generate_okf_indexes.py   # пересобирает index.md в директориях bundle
src/okf_mcp/scripts/export_okf.py             # экспортирует system/*.md как Source Document concepts
src/okf_mcp/scripts/generate_okf_graph.py     # строит graph.json из concepts и Markdown-ссылок
```

## Минимальный concept

```md
---
type: Reference
title: Example
description: Short description.
timestamp: 2026-06-25T00:00:00Z
---

# Example

Body text with a link to [another concept](./another.md).
```
