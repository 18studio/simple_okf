<div align="center">

# Simple OKF Template

**Локальный шаблон и MCP-инструменты для ведения agent-readable knowledge bundle в Open Knowledge Format.**

[![GitHub](https://img.shields.io/badge/GitHub-18studio%2Fsimple_okf-181717?logo=github)](https://github.com/18studio/simple_okf)
[![Issues](https://img.shields.io/github/issues/18studio/simple_okf)](https://github.com/18studio/simple_okf/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/18studio/simple_okf)](https://github.com/18studio/simple_okf/pulls)
[![Last Commit](https://img.shields.io/github/last-commit/18studio/simple_okf)](https://github.com/18studio/simple_okf/commits/master)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](./pyproject.toml)

</div>

## Что это

Короче: клонируешь и запускаешь в своём AI-окружении. Я использую Pi.

Есть навык (skill): вызываешь его и можешь в правильном формате создавать документы, собирать контекст и искать через MCP.

В MCP есть команды для дискретных действий и поиска по RAG.

RAG помогает искать по ID и содержанию. Это особенно полезно, если запускать субагентов и для каждого прохода вытаскивать контекст документов.

## Локальный запуск

### Требования

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/)
- `make` — опционально, но удобнее для типовых команд

### Быстрый старт

```sh
git clone git@github.com:18studio/simple_okf.git
cd simple_okf
make init
```

`make init` установит зависимости через `uv`, создаст локальный `okf_mcp/rag/.env` из примера, проверит OKF-бандл и обновит локальный RAG-индекс.

Если `make` не нужен, те же шаги можно выполнить вручную:

```sh
uv sync
cp okf_mcp/rag/.env.example okf_mcp/rag/.env
uv run python -m okf_mcp validate okf
uv run python -m okf_mcp rag inspect --pretty
uv run python -m okf_mcp rag refresh --pretty
```

### Запуск MCP-сервера

Для stdio-транспорта:

```sh
uv run python -m okf_mcp server --bundle okf
```

Для HTTP-транспорта:

```sh
uv run python -m okf_mcp server --bundle okf --transport http --host 127.0.0.1 --port 8000
```

В Pi и других MCP-клиентах можно использовать готовую конфигурацию из [`.mcp.json`](./.mcp.json): сервер называется `simple-okf`.

### Запуск через Docker Compose

Если не хочется ставить Python/uv локально, можно поднять HTTP MCP-сервер через Docker Compose:

```sh
docker compose up --build
```

Сервис слушает `http://127.0.0.1:8000`. Compose не поднимает внешние сервисы вроде OpenSearch, Qdrant или OpenAI: текущий RAG работает локально с OKF-бандлом и JSON-артефактами.

Compose загружает переменные из [`okf_mcp/rag/.env.example`](./okf_mcp/rag/.env.example) через `env_file`.

Подключены локальные директории:

- `./okf` → `/app/okf`
- `./artifacts` → `/app/artifacts`

Остановить сервис:

```sh
docker compose down
```

### Переменные окружения

Основной локальный env-файл для RAG — `okf_mcp/rag/.env`. Он создаётся из примера [`okf_mcp/rag/.env.example`](./okf_mcp/rag/.env.example) и не должен попадать в git:

```sh
cp okf_mcp/rag/.env.example okf_mcp/rag/.env
```

Для разового запуска RAG с другим env-файлом используйте флаг `--env`:

```sh
uv run python -m okf_mcp rag inspect --env /path/to/.env --pretty
```

| Переменная | Где задаётся | Значение в `.env.example` | Описание |
|---|---|---|---|
| `OKF_BUNDLE` | shell env / Compose `env_file` | `okf` | Путь к OKF-бандлу для MCP-сервера, если не передан `--bundle`. |
| `RAG_BUNDLE_DIR` | `okf_mcp/rag/.env` / Compose `env_file` | `okf` | OKF-бандл, который RAG-инструменты инспектируют, индексируют и по которому ищут. Относительные пути считаются от корня репозитория при CLI-запуске и от `/app` при Docker Compose. Директория должна существовать. |
| `RAG_ARTIFACTS_DIR` | `okf_mcp/rag/.env` / Compose `env_file` | `artifacts/rag` | Директория для локальных RAG-артефактов. Должна резолвиться внутрь директории `artifacts/`. |
| `RAG_RETRIEVAL_RESULT_LIMIT` | `okf_mcp/rag/.env` / Compose `env_file` | `10` | Количество результатов по умолчанию для `rag retrieve`, если не передан `--limit`. Значение должно быть целым числом `>= 1`. |
| `RAG_ANSWER_EVIDENCE_LIMIT` | `okf_mcp/rag/.env` / Compose `env_file` | `5` | Количество фрагментов-доказательств для extractive-ответа RAG. Значение должно быть целым числом `>= 1`. |
| `RAG_OPENSEARCH_URL` | `okf_mcp/rag/.env` / Compose `env_file` | пусто | Зарезервировано для OpenSearch в будущей indexed RAG-интеграции. В Docker Compose по умолчанию пусто, потому что внешний OpenSearch не запускается и текущий локальный поиск его не использует. |
| `RAG_QDRANT_URL` | `okf_mcp/rag/.env` / Compose `env_file` | пусто | Зарезервировано для Qdrant в будущем векторном индексе. В Docker Compose по умолчанию пусто, потому что внешний Qdrant не запускается и текущий локальный поиск его не использует. |
| `OPENAI_API_KEY` | `okf_mcp/rag/.env` / Compose `env_file` | пусто | Зарезервированный секрет для будущей generative RAG-интеграции. Не коммитьте реальное значение. В Docker Compose по умолчанию пусто, потому что OpenAI не нужен для текущего локального поиска. |
| `RAG_EMBEDDING_MODEL` | `okf_mcp/rag/.env` / Compose `env_file` | пусто | Зарезервировано: модель эмбеддингов для будущей generative/indexed RAG-интеграции. |
| `RAG_EMBEDDING_DIMENSIONS` | `okf_mcp/rag/.env` / Compose `env_file` | пусто | Зарезервировано: размерность эмбеддингов для будущего векторного индекса. |
| `RAG_GENERATION_MODEL` | `okf_mcp/rag/.env` / Compose `env_file` | пусто | Зарезервировано: модель генерации ответов для будущей generative RAG-интеграции. |
| `RAG_REPHRASER_MODEL` | `okf_mcp/rag/.env` / Compose `env_file` | пусто | Зарезервировано: модель переформулирования запросов для будущей generative RAG-интеграции. |

### HLD-схема сервиса

Simple OKF — это локальный сервис для ведения agent-readable knowledge base. На HLD-уровне у него одна граница системы: сервис принимает запросы, работает с OKF-бандлом как с источником истины и создаёт производные артефакты для навигации, поиска и отчётности.

```mermaid
flowchart TB
    clients["Агенты и разработчики"]

    service["Simple OKF service\nлокальный MCP/CLI сервис\n\nОсновные функции:\nOKF management\nQuality automation\nLocal RAG\n7D reporting"]

    bundle["OKF-бандл\nканоничные Markdown-концепты"]
    artifacts["Производные артефакты\nиндексы, граф, dashboard, RAG-индекс"]
    external["Будущие внешние RAG-интеграции"]

    clients -->|"запросы"| service
    service -->|"читает и изменяет"| bundle
    service -->|"создаёт и обновляет"| artifacts
    service -. "опционально в будущем" .-> external
```

На схеме:

- **Агенты и разработчики** — потребители сервиса через MCP API или CLI.
- **Simple OKF service** — единственная запускаемая система; внутри неё находятся OKF tooling, Local RAG и 7D-отчётность.
- **OKF-бандл** — источник истины; знания хранятся как Markdown-концепты.
- **Производные артефакты** — пересобираемые файлы для индексов, графа, dashboard и локального RAG.
- **Будущие внешние RAG-интеграции** — не входят в текущий локальный запуск.

### Полезные команды

```sh
make validate       # проверить Python-модули и OKF-бандл
make indexes        # пересобрать okf/**/index.md
make graph          # собрать artifacts/okf/graph.json и graph.html
make rag-check      # проверить и обновить локальный RAG-индекс
make 7d-report      # вывести компактный отчет по 7D-стадиям
make 7d-dashboard   # собрать artifacts/7d-dashboard.html
```

## Документация

- LLM-контракт проекта: [SPEC.md](./SPEC.md)
- Правила для агентов: [AGENTS.md](./AGENTS.md)
- Основной OKF-бандл: [`okf/`](./okf/)
- MCP и CLI: [`okf_mcp/`](./okf_mcp/)

Если что, пишите issues и предлагайте PR.

Коля
