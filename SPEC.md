# OKF Project Template Specification

Версия шаблона: `0.1`

## Назначение

Этот репозиторий задаёт минимальный шаблон проекта для ведения знаний в OKF формате и подключения metadata tooling через `kcmd` MCP.

## Обязательные части шаблона

### 1. OKF bundle structure

Основной bundle расположен здесь:

```text
okf/platform-system/
```

Базовая структура:

```text
okf/platform-system/
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
├── ui/
│   ├── ux/
│   ├── design-system/
│   └── uikit/
└── traceability/
    ├── gaps/
    └── coverage/
```

### 2. Concept format

Каждый concept — Markdown-файл с YAML frontmatter.

Минимум:

```md
---
type: Reference
---

Concept body.
```

Рекомендуемый формат:

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

### 3. Navigation files

`index.md` — навигационный файл директории. Не считается concept.

`log.md` — changelog. Не считается concept.

### 4. Links as graph

Связи задаются Markdown-ссылками:

```md
Creates [Project](../../data/entities/project.md)
and is governed by [ACCESS-005](../../requirements/access/ACCESS-005.md).
```

Для внутренних связей предпочтительны относительные ссылки.

### 5. kcmd MCP

MCP config:

```text
.mcp.json
config/mcp/kcmd.mcp.json
```

Configured server:

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

Expected snapshot:

```text
snapshots/kcmd/catalog-snapshot/
├── catalog.yaml
└── catalog/
```

### 6. OKF Skill

Project skill:

```text
.pi/skills/okf/SKILL.md
```

Use cases:

- create/edit OKF concepts;
- validate OKF bundle;
- regenerate indexes;
- export canonical docs;
- use `kcmd` snapshots when metadata catalog integration is needed.

## Tooling contract

Validation:

```bash
python3 scripts/validate_okf.py okf/platform-system
```

Index generation:

```bash
python3 scripts/generate_okf_indexes.py okf/platform-system
```

Canonical docs export:

```bash
python3 scripts/export_okf.py --source system --out okf/platform-system
```
