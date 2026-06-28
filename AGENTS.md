# Repository Guidelines

## Purpose and Authority

This repository is a local **Simple OKF** template and toolset for maintaining
agent-readable knowledge bundles in Open Knowledge Format.

Documentation and implementation authority is layered:

1. `README.md` is the human entry point and quick-start guide.
2. `SPEC.md` is the repository-level contract for the OKF template and tools.
3. `okf/` is the default OKF bundle and the canonical local knowledge corpus.
4. `mcp/` is the canonical Python package for OKF MCP tools, CLI fallback tools,
   and OKF-aware RAG helpers.
5. `.agents/skills/okf/SKILL.md` defines OKF-specific agent workflow rules.
6. `AGENTS.md` defines repository-local working rules for coding agents.

When these files disagree, update the canonical owner instead of duplicating the
same rule in a secondary location.

## Repository Boundaries

- Keep the primary OKF bundle under `okf/`.
- Keep MCP server, OKF helpers, CLI scripts, and RAG implementation under `mcp/`.
- Do not reintroduce `src/okf_mcp/`; this project is standardized on `mcp/`.
- Keep OKF agent instructions, templates, and references under
  `.agents/skills/okf/`.
- Keep local RAG configuration examples and artifacts under `mcp/rag/`.
- Do not create a top-level `rag/` directory for this project.
- Treat generated files such as `okf/graph.json`, `okf/graph.html`, and
  `mcp/rag/artifacts/*` as derived outputs unless explicitly promoted.
- Never commit local secrets. `mcp/rag/.env` is local-only and ignored.

## OKF Bundle Rules

- Each concept is one Markdown file under `okf/` with YAML frontmatter.
- `index.md` and `log.md` are support files, not concepts.
- The minimum required concept frontmatter key is `type`.
- Recommended keys are `title`, `description`, and `timestamp`.
- Preserve unknown frontmatter fields when editing existing concepts.
- Use relative Markdown links for internal OKF relationships.
- Do not invent requirement IDs, schema details, citations, source paths, or
  domain facts.

Concept IDs are bundle-relative paths without `.md`, for example:

```text
requirements/functions/FUNC-001
api/operations/create-project
```

## OKF Workflows

For OKF content work, prefer the `simple-okf` MCP server when available:

```text
read_support_file
list_directory
list_concepts
search_concepts
read_concept
write_concept_doc
validate_bundle
generate_indexes
build_graph
```

If MCP is unavailable, use the local CLI fallback scripts in `mcp/scripts/` and
report that fallback was used.

Before broad OKF changes:

1. inspect `okf/index.md` or use `list_directory`;
2. find existing concepts before creating new ones;
3. preserve stable concept IDs unless the user explicitly asks for a rename;
4. update related links when moving or renaming concepts;
5. regenerate indexes and graph after concept additions, removals, or renames;
6. validate the bundle before finishing.

## OKF RAG Rules

The OKF-aware RAG layer is implementation/tooling over the OKF bundle. It does
not define canonical knowledge by itself.

- The local RAG environment file is `mcp/rag/.env`.
- The committed example is `mcp/rag/.env.example`.
- Default artifacts belong under `mcp/rag/artifacts/`.
- RAG tools must treat OKF concepts as the corpus and exclude `index.md` and
  `log.md`.
- RAG parser output must preserve `concept_id`, `type`, `title`, `description`,
  `tags`, `requirement_id`, `resource`, and `source_path` when present.
- RAG answers must cite OKF concepts and line ranges when evidence is available.
- Do not treat RAG search results as more authoritative than the source concept
  files.

Useful CLI commands:

```sh
python3 mcp/scripts/inspect_rag_corpus.py --pretty
python3 mcp/scripts/refresh_rag_index.py --pretty
python3 mcp/scripts/rag_retrieve.py "query" --pretty
python3 mcp/scripts/rag_retrieve.py "query" --answer --pretty
```

## Code Ownership

| Area | Owner / contract |
|---|---|
| OKF filesystem model, parser, validator, graph generation | `mcp/okf.py` |
| FastMCP tool surface | `mcp/server.py` |
| MCP entrypoint | `mcp/__main__.py` |
| CLI fallback scripts | `mcp/scripts/` |
| OKF-aware local RAG | `mcp/rag/` |
| Default knowledge bundle | `okf/` |
| Agent OKF skill and templates | `.agents/skills/okf/` |
| Packaging and console scripts | `pyproject.toml` |

Avoid duplicating core OKF logic in scripts. CLI scripts should call shared
library code from `mcp/okf.py` or `mcp/rag/`.

## Change Classification

Before editing, classify the request:

- **OKF content change**: creates, edits, moves, or deletes concepts in `okf/`.
  Follow OKF workflows, regenerate indexes/graph when needed, and validate.
- **OKF tooling change**: changes `mcp/okf.py`, MCP tools, CLI scripts, or
  package configuration. Run Python compile checks and relevant CLI smoke tests.
- **RAG tooling change**: changes `mcp/rag/` or RAG scripts. Test with an env
  file and ensure `mcp/rag/.env` remains uncommitted.
- **Agent instruction change**: changes `AGENTS.md` or `.agents/skills/okf/`.
  Keep rules consistent with `README.md` and `SPEC.md`.
- **Generated-output change**: updates graph/index/artifact files. Ensure the
  generating command is clear and repeatable.

When classification is unclear, ask a focused clarification question.

## Writing and Linking

Use concise Markdown with descriptive headings and short paragraphs.

Linking rules:

- use relative links inside the OKF bundle;
- prefer exact concept links over broad directory links;
- keep links stable when possible;
- do not replace missing exact links with vague links just to silence validation;
- report broken or missing knowledge as a gap when the correct target is unknown.

## Validation

Before completing repository changes, run the relevant subset:

```sh
python3 -m py_compile mcp/__init__.py mcp/__main__.py mcp/okf.py mcp/server.py mcp/scripts/*.py mcp/rag/*.py mcp/rag/ingestion/*.py mcp/rag/retrieval/*.py
python3 mcp/scripts/validate_okf.py okf
python3 mcp/scripts/generate_okf_graph.py okf --out okf/graph.json
git diff --check
git status --short
git diff --stat
```

For RAG changes, also smoke-test with a local env file. If `mcp/rag/.env` is not
available, either use a temporary env file via `--env` or report that RAG runtime
validation was skipped because the local env file is absent.

For OKF content additions/removals/renames, also run:

```sh
python3 mcp/scripts/generate_okf_indexes.py okf
python3 mcp/scripts/generate_okf_graph.py okf --out okf/graph.json
python3 mcp/scripts/validate_okf.py okf
```

## Reporting

When finishing work, report:

1. files changed;
2. commands run and results;
3. whether OKF validation passed;
4. whether indexes/graph/RAG artifacts were regenerated;
5. remaining gaps or follow-up questions.
