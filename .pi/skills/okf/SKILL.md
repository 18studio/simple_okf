---
name: okf
description: Work with Open Knowledge Format bundles in this project. Use when creating, editing, validating, indexing, or navigating OKF concepts; when converting canonical docs into OKF; or when using kcmd MCP metadata snapshots alongside OKF.
---

# OKF project skill

Use this skill for all tasks involving OKF in this repository.

## Project layout

Main OKF bundle:

```text
okf/platform-system/
```

Supporting files:

```text
docs/OKF_REFERENCE.md          # compact OKF/kcmd memory
scripts/validate_okf.py        # validate concept frontmatter and links
scripts/generate_okf_indexes.py# regenerate index.md files
scripts/export_okf.py          # export system/*.md into OKF Source Document concepts
templates/okf/                 # concept templates
snapshots/kcmd/                # kcmd metadata snapshots
.mcp.json                      # kcmd MCP config template
```

Before unfamiliar OKF work, read:

```text
../../../docs/OKF_REFERENCE.md
```

## OKF rules

- A bundle is a directory of Markdown files with YAML frontmatter.
- `index.md` is navigation, not a concept.
- `log.md` is a changelog, not a concept.
- Concept ID is the path inside the bundle without `.md`.
- Minimum OKF frontmatter: `type`.
- Project recommendation: include `title`, `description`, `timestamp`.
- Unknown frontmatter fields are allowed.
- Relationships are Markdown links.
- Prefer relative links for internal OKF graph edges.

## Common concept types

Use these types unless the user asks otherwise:

```yaml
type: Source Document
type: Requirement
type: Function Requirement
type: User Flow
type: Business Rule
type: Access Rule
type: Data Entity
type: API Operation
type: UX Screen
type: UI Component
type: Architecture Decision
type: Deployment Requirement
type: Traceability Row
type: Gap
type: Glossary Term
```

## Workflow: create or edit concepts

1. Read `okf/platform-system/index.md` and the nearest directory `index.md`.
2. Choose the correct directory and concept ID.
3. Use a template from `../../../templates/okf/` when creating a concept.
4. Add frontmatter with at least `type`, preferably also `title`, `description`, `resource`, `tags`, `timestamp`.
5. Use relative Markdown links to related concepts.
6. Run validation:

```bash
python3 scripts/validate_okf.py okf/platform-system
```

7. Regenerate indexes if concepts were added/removed/renamed:

```bash
python3 scripts/generate_okf_indexes.py okf/platform-system
```

8. Re-run validation.

## Workflow: export canonical docs

If the repository has `system/*.md`, export them into `documents/` concepts:

```bash
python3 scripts/export_okf.py --source system --out okf/platform-system
python3 scripts/generate_okf_indexes.py okf/platform-system
python3 scripts/validate_okf.py okf/platform-system
```

Do not treat generated OKF output as more canonical than the source docs unless the user explicitly changes the ownership model.

## kcmd MCP

kcmd is for Metadata as Code snapshots, not the OKF format itself. Use it when the task involves Google Knowledge Catalog / Dataplex / BigQuery metadata snapshots.

Configured MCP shape:

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

Expected snapshot path:

```text
snapshots/kcmd/catalog-snapshot/
├── catalog.yaml
└── catalog/
```

Useful commands:

```bash
kcmd init --bigquery-dataset <project.dataset> --pull
kcmd pull
kcmd push --validate-only
kcmd push
kcmd mcp --path snapshots/kcmd/catalog-snapshot
```

Auth:

```bash
gcloud auth application-default login
gcloud config set project <project-id>
```

MCP tools expected from the current context:

- `list-entries`
- `lookup-entry`
- `modify-entry`

## Quality checklist

Before finishing an OKF change, ensure:

- concept files have valid frontmatter;
- `type` exists;
- `title`, `description`, `timestamp` exist unless intentionally omitted;
- internal links resolve;
- duplicate `requirement_id` values are not introduced;
- directory `index.md` files are up to date;
- kcmd snapshots are kept under `snapshots/kcmd/`, not mixed into `okf/`.
