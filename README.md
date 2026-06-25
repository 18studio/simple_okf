# Simple OKF Template

Шаблон проекта для ведения знаний в формате **OKF — Open Knowledge Format**.

OKF здесь используется как переносимый knowledge bundle:

```text
Markdown + YAML frontmatter + directories + Markdown links
```

Проект содержит:

1. структуру директории под OKF bundle;
2. конфигурацию `kcmd` MCP для работы с metadata snapshots;
3. project skill для агентов: `.pi/skills/okf/SKILL.md`.

> Контекст по OKF взят из репозитория `GoogleCloudPlatform/knowledge-catalog`, директории `okf/` и `toolbox/mdcode/`. Репозиторий помечен как **not an official Google product**.

## Структура

```text
.
├── okf/
│   └── platform-system/          # основной OKF bundle
├── snapshots/
│   └── kcmd/                     # локальные kcmd snapshots
├── config/
│   └── mcp/                      # MCP конфигурации
├── scripts/                      # утилиты OKF
├── templates/
│   └── okf/                      # шаблоны concept-файлов
├── docs/                         # краткая справка по OKF/kcmd
└── .pi/skills/okf/               # skill для обращения с OKF
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

## kcmd MCP

Шаблон MCP-конфига лежит в:

```text
.mcp.json
config/mcp/kcmd.mcp.json
```

Он ожидает, что команда `kcmd` доступна в `PATH`, а snapshot находится в:

```text
snapshots/kcmd/catalog-snapshot/
├── catalog.yaml
└── catalog/
```

Пример запуска MCP server вручную:

```bash
kcmd mcp --path snapshots/kcmd/catalog-snapshot
```

## OKF правила проекта

- `okf/platform-system/` — основной bundle.
- Каждый concept — Markdown-файл с YAML frontmatter.
- `index.md` — навигационный файл, не concept.
- `log.md` — опциональный журнал изменений, не concept.
- Минимально обязательное поле OKF: `type`.
- В этом шаблоне дополнительно рекомендуется: `title`, `description`, `timestamp`.
- Связи выражаются Markdown-ссылками между concept-файлами.
- Для visualizer и валидатора предпочтительны относительные ссылки.

## Установка OKF reference agent из upstream

Если нужен upstream reference agent:

```bash
mkdir -p external
cd external
git clone https://github.com/GoogleCloudPlatform/knowledge-catalog.git
cd knowledge-catalog/okf

python3.13 -m venv .venv
.venv/bin/pip install --index-url https://pypi.org/simple/ -e '.[dev]'
```

BigQuery auth:

```bash
gcloud auth application-default login
gcloud config set project <project-id>
```

Gemini через API key:

```bash
export GEMINI_API_KEY=...
```

Или через Vertex AI:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=<project-id>
export GOOGLE_CLOUD_LOCATION=<region>
```
