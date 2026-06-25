# Simple OKF Template

Шаблон проекта для ведения знаний в формате **OKF — Open Knowledge Format**.

OKF здесь используется как переносимый knowledge bundle:

```text
Markdown + YAML frontmatter + directories + Markdown links
```

Проект содержит только OKF-формат и локальные инструменты для работы с ним:

1. структуру директории под OKF bundle;
2. skill для агентов;
3. шаблоны OKF concept-файлов внутри skill;
4. скрипты для валидации, генерации индексов, экспорта Markdown-документов и построения graph JSON внутри skill.

Шаблон сфокусирован на локальных файлах, Git-friendly workflow и агентной навигации по Markdown-ссылкам.

## Структура

```text
.
├── okr/              # основной OKF bundle
├── README.md
├── SPEC.md
└── .agents/skills/okf/           # skill, scripts, templates, references для OKF
    ├── SKILL.md
    ├── references/
    ├── scripts/
    └── templates/
```

## Быстрый старт

Проверить OKF bundle:

```bash
python3 .agents/skills/okf/scripts/validate_okf.py okr
```

Сгенерировать `index.md` по директориям:

```bash
python3 .agents/skills/okf/scripts/generate_okf_indexes.py okr
```

Экспортировать документы из `system/`, если такая директория есть:

```bash
python3 .agents/skills/okf/scripts/export_okf.py --source system --out okr
```

Построить JSON-граф concepts и Markdown-ссылок:

```bash
python3 .agents/skills/okf/scripts/generate_okf_graph.py okr --out okr/graph.json
```

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

## Локальные инструменты

```text
.agents/skills/okf/scripts/validate_okf.py           # проверяет frontmatter, type, ссылки, дубликаты requirement_id
.agents/skills/okf/scripts/generate_okf_indexes.py   # пересобирает index.md в директориях bundle
.agents/skills/okf/scripts/export_okf.py             # экспортирует system/*.md как Source Document concepts
.agents/skills/okf/scripts/generate_okf_graph.py     # строит graph.json из concepts и Markdown-ссылок
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
