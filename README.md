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

### Переменные окружения

Основной локальный env-файл для RAG — `okf_mcp/rag/.env`. Он создаётся из примера [`okf_mcp/rag/.env.example`](./okf_mcp/rag/.env.example) и не должен попадать в git:

```sh
cp okf_mcp/rag/.env.example okf_mcp/rag/.env
```

Для разового запуска RAG с другим env-файлом используйте флаг `--env`:

```sh
uv run python -m okf_mcp rag inspect --env /path/to/.env --pretty
```

| Переменная | Где задаётся | Значение по умолчанию | Статус | Описание |
|---|---|---|---|---|
| `OKF_BUNDLE` | shell env | `okf` | используется | Путь к OKF-бандлу для MCP-сервера, если не передан `--bundle`. Не читается из `okf_mcp/rag/.env`. |
| `RAG_BUNDLE_DIR` | `okf_mcp/rag/.env` | `okf` | используется | OKF-бандл, который RAG-инструменты инспектируют, индексируют и по которому ищут. Относительные пути считаются от корня репозитория. Директория должна существовать. |
| `RAG_ARTIFACTS_DIR` | `okf_mcp/rag/.env` | `artifacts/rag` | используется | Директория для локальных RAG-артефактов. Должна резолвиться внутрь репозиторной директории `artifacts/`. |
| `RAG_RETRIEVAL_RESULT_LIMIT` | `okf_mcp/rag/.env` | `10` | используется | Количество результатов по умолчанию для `rag retrieve`, если не передан `--limit`. Значение должно быть целым числом `>= 1`. |
| `RAG_ANSWER_EVIDENCE_LIMIT` | `okf_mcp/rag/.env` | `5` | используется | Количество фрагментов-доказательств для extractive-ответа RAG. Значение должно быть целым числом `>= 1`. |
| `RAG_OPENSEARCH_URL` | `okf_mcp/rag/.env` | `http://127.0.0.1:9200` | зарезервировано | URL OpenSearch для будущей indexed RAG-интеграции. Текущий локальный поиск его не использует. |
| `RAG_QDRANT_URL` | `okf_mcp/rag/.env` | `http://127.0.0.1:6333` | зарезервировано | URL Qdrant для будущего векторного индекса. Текущий локальный поиск его не использует. |
| `OPENAI_API_KEY` | `okf_mcp/rag/.env` | `your-api-key` | зарезервировано, секрет | API-ключ для будущей generative RAG-интеграции. Не коммитьте реальное значение. Текущий локальный поиск его не использует. |
| `RAG_EMBEDDING_MODEL` | `okf_mcp/rag/.env` | `text-embedding-3-large` | зарезервировано | Модель эмбеддингов для будущей generative/indexed RAG-интеграции. |
| `RAG_EMBEDDING_DIMENSIONS` | `okf_mcp/rag/.env` | `3072` | зарезервировано | Размерность эмбеддингов для будущего векторного индекса. |
| `RAG_GENERATION_MODEL` | `okf_mcp/rag/.env` | `gpt-4.1-mini` | зарезервировано | Модель генерации ответов для будущей generative RAG-интеграции. |
| `RAG_REPHRASER_MODEL` | `okf_mcp/rag/.env` | `gpt-4.1-mini` | зарезервировано | Модель переформулирования запросов для будущей generative RAG-интеграции. |

### HLD-схема env и RAG

```mermaid
flowchart TD
    user["Пользователь / Agent / Pi"] --> entry["CLI или MCP server"]
    okfBundleEnv["Shell env: OKF_BUNDLE"] --> entry
    bundleArg["CLI arg: --bundle"] --> entry

    entry --> okfTools["OKF tools: validate / indexes / graph / 7D"]
    entry --> ragTools["RAG tools: inspect / refresh / retrieve / answer"]

    okfTools --> okfBundle["OKF bundle: okf/"]

    ragEnv["okf_mcp/rag/.env или --env"] --> settings["RAG settings loader"]
    settings --> ragBundle["RAG_BUNDLE_DIR"]
    settings --> ragArtifacts["RAG_ARTIFACTS_DIR"]
    settings --> ragLimits["RAG_*_LIMIT"]
    settings -. reserved .-> futureProviders["OpenSearch / Qdrant / OpenAI"]

    ragTools --> settings
    ragBundle --> okfBundle
    okfBundle --> corpus["OKF concepts -> RAG chunks"]
    corpus --> localIndex["local JSON index"]
    ragArtifacts --> localIndex
    corpus --> results["hits + OKF citations"]
    localIndex --> results
```

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
