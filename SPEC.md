# OKF Project Template Specification

Версия шаблона: `0.2`

## Назначение

Этот репозиторий задаёт минимальный шаблон проекта для ведения знаний в формате OKF.

Шаблон намеренно ограничен:

- OKF bundle structure;
- Markdown concepts с YAML frontmatter;
- Markdown links как graph;
- локальные scripts для работы с bundle;
- project skill для агентов.

Шаблон фиксирует локальный файловый контракт OKF и не требует внешних сервисов для чтения или проверки bundle.

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

Graph extraction:

```bash
python3 scripts/generate_okf_graph.py okf/platform-system --out okf/platform-system/graph.json
```
