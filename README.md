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
