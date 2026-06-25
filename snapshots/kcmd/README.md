# kcmd snapshots

Эта директория предназначена для локальных Metadata as Code snapshots.

Ожидаемая структура для настроенного MCP:

```text
snapshots/kcmd/catalog-snapshot/
├── catalog.yaml
└── catalog/
```

Создать snapshot для BigQuery dataset:

```bash
mkdir -p snapshots/kcmd/catalog-snapshot
cd snapshots/kcmd/catalog-snapshot
kcmd init --bigquery-dataset <project.dataset> --pull
```

Запустить MCP server вручную из корня проекта:

```bash
kcmd mcp --path snapshots/kcmd/catalog-snapshot
```

Опубликовать изменения:

```bash
cd snapshots/kcmd/catalog-snapshot
kcmd push --validate-only
kcmd push
```

Auth:

```bash
gcloud auth application-default login
gcloud config set project <project-id>
```
