# Simple OKF Template

Шаблон проекта для ведения знаний в формате **OKF — Open Knowledge Format**.

OKF здесь используется как переносимый knowledge bundle:

```text
Markdown + YAML frontmatter + directories + Markdown links
```

Проект содержит только OKF-формат и локальные инструменты для работы с ним:

1. структуру директории под OKF bundle;
2. шаблоны OKF concept-файлов;
3. скрипты для валидации, генерации индексов, экспорта Markdown-документов и построения graph JSON;
4. project skill для агентов: `.agents/skills/okf/SKILL.md`.

Шаблон сфокусирован на локальных файлах, Git-friendly workflow и агентной навигации по Markdown-ссылкам.

## Структура

```text
.
├── okf/
│   └── platform-system/          # основной OKF bundle
├── scripts/                      # локальные OKF-утилиты
├── templates/
│   └── okf/                      # шаблоны concept-файлов
├── docs/                         # краткая справка по OKF
└── .agents/skills/okf/           # skill для обращения с OKF
```

## Быстрый старт

Проверить OKF bundle:

```bash
python3 scripts/validate_okf.py okf/platform-system
```

Сгенерировать `index.md` по директориям:

```bash
python3 scripts/generate_okf_indexes.py okf/platform-system
```

Экспортировать документы из `system/`, если такая директория есть:

```bash
python3 scripts/export_okf.py --source system --out okf/platform-system
```

Построить JSON-граф concepts и Markdown-ссылок:

```bash
python3 scripts/generate_okf_graph.py okf/platform-system --out okf/platform-system/graph.json
```

## OKF правила проекта

- `okf/platform-system/` — основной bundle.
- Каждый concept — Markdown-файл с YAML frontmatter.
- `index.md` — навигационный файл, не concept.
- `log.md` — опциональный журнал изменений, не concept.
- Минимально обязательное поле OKF: `type`.
- В этом шаблоне дополнительно рекомендуется: `title`, `description`, `timestamp`.
- Связи выражаются Markdown-ссылками между concept-файлами.
- Для graph tooling и валидатора предпочтительны относительные ссылки.

## Шаблоны concepts

```text
templates/okf/concept.md
templates/okf/source-document.md
templates/okf/requirement.md
templates/okf/api-operation.md
templates/okf/data-entity.md
```

## Локальные инструменты

```text
scripts/validate_okf.py           # проверяет frontmatter, type, ссылки, дубликаты requirement_id
scripts/generate_okf_indexes.py   # пересобирает index.md в директориях bundle
scripts/export_okf.py             # экспортирует system/*.md как Source Document concepts
scripts/generate_okf_graph.py     # строит graph.json из concepts и Markdown-ссылок
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
