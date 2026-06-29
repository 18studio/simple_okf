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
6. `.agents/skills/7d/SKILL.md` defines 7D lifecycle workflow rules over OKF.
7. `AGENTS.md` defines repository-local working rules for coding agents.

When these files disagree, update the canonical owner instead of duplicating the
same rule in a secondary location.

## Repository Boundaries

- Keep the primary OKF bundle under `okf/`.
- Keep the MCP server, multi-app CLI, OKF helpers, and RAG implementation under `mcp/`.
- Do not reintroduce `src/okf_mcp/`; this project is standardized on `mcp/`.
- Keep OKF agent instructions, templates, and references under
  `.agents/skills/okf/`.
- Keep 7D lifecycle agent instructions under `.agents/skills/7d/`.
- Keep canonical CLI app implementation in `mcp/cli.py` and reusable implementation in `mcp/` modules.
- Keep installable console-script bootstrapping in `simple_okf_mcp/cli.py` so console commands avoid the upstream MCP SDK `mcp` namespace collision while delegating to `mcp/cli.py`.
- Keep local RAG configuration examples under `mcp/rag/`.
- Do not create a top-level `rag/` directory for this project.
- Keep generated artifacts under repository `artifacts/`, including
  `artifacts/okf/graph.json`, `artifacts/okf/graph.html`,
  `artifacts/7d-dashboard.html`, and `artifacts/rag/*`.
- Never commit local secrets. `mcp/rag/.env` is local-only and ignored.

## OKF Bundle Rules

- Each concept is one Markdown file under `okf/` with YAML frontmatter.
- `index.md` and `log.md` are support files, not concepts.
- The minimum required concept frontmatter key is `type`.
- Recommended keys are `title`, `description`, and `timestamp`.
- Preserve unknown frontmatter fields when editing existing concepts.
- Write OKF concept and support documentation in English. Before creating or
  updating OKF documents from non-English input, translate the content into
  English while preserving meaning.
- Use relative Markdown links for internal OKF relationships.
- Do not invent requirement IDs, schema details, citations, source paths, or
  domain facts.

Concept IDs are bundle-relative paths without `.md`, for example:

```text
requirements/functions/FUNC-001
api/operations/create-project
```

## 7D Process Rules

7D is a process registry over existing OKF concept types. It does not change the
OKF concept format.

- Do not add 7D-specific frontmatter keys such as `process`, `stage`,
  `stage_order`, `artifact_key`, `gate_decision`, or `raci` solely to support
  7D.
- Do not create generic 7D concept types such as `Lifecycle Artifact`,
  `Lifecycle Check`, `Role`, or `Decision Gate` when the artifact type is known.
- Use the existing `type` field as the artifact type, for example `PRD`,
  `Architecture & NFR`, or `Test Report`.
- Resolve 7D stage and responsibility from the registry table in `SPEC.md` or
  the MCP 7D tools, not from per-concept 7D metadata.
- Derive a feature's 7D progress from linked artifact concepts and their types;
  if the type is not in the registry, report a gap.
- Keep 7D behavior out of `.agents/skills/okf/SKILL.md`; use the dedicated
  `.agents/skills/7d/SKILL.md` workflow for 7D operations while keeping
  `SPEC.md` as the repository-level source for 7D rules.

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
seven_d_registry
seven_d_mapping_for_type
list_7d_artifact_concepts
seven_d_stage_report
seven_d_stage_report_markdown
seven_d_dashboard
seven_d_feature_status
validate_7d
generate_indexes
build_graph
```

If MCP is unavailable, use the local multi-app CLI (`python3 -m mcp ...`) and
report that CLI fallback was used.

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
- Default RAG artifacts belong under `artifacts/rag/`.
- RAG tools must treat OKF concepts as the corpus and exclude `index.md` and
  `log.md`.
- RAG parser output must preserve `concept_id`, `type`, `title`, `description`,
  `tags`, `requirement_id`, `resource`, and `source_path` when present.
- RAG answers must cite OKF concepts and line ranges when evidence is available.
- Do not treat RAG search results as more authoritative than the source concept
  files.

Useful CLI commands:

```sh
python3 -m mcp rag inspect --pretty
python3 -m mcp rag refresh --pretty
python3 -m mcp rag retrieve "query" --pretty
python3 -m mcp rag retrieve "query" --answer --pretty
```

## Code Ownership

| Area | Owner / contract |
|---|---|
| OKF filesystem model, parser, validator, graph generation | `mcp/okf.py` |
| FastMCP tool surface | `mcp/server.py` |
| MCP multi-app entrypoint | `mcp/__main__.py`, `mcp/cli.py` |
| Console-script bootstrap | `simple_okf_mcp/cli.py` delegates to `mcp/cli.py` while avoiding the upstream MCP SDK `mcp` namespace collision |
| OKF-aware local RAG | `mcp/rag/` |
| Default knowledge bundle | `okf/` |
| Agent OKF skill and templates | `.agents/skills/okf/` |
| Agent 7D workflow skill | `.agents/skills/7d/` |
| Packaging and console scripts | `pyproject.toml`, `simple_okf_mcp/cli.py` |

Avoid duplicating core OKF logic in CLI code. CLI commands should call shared
library code from `mcp/okf.py` or `mcp/rag/`.

## Change Classification

Before editing, classify the request:

- **OKF content change**: creates, edits, moves, or deletes concepts in `okf/`.
  Follow OKF workflows, regenerate indexes/graph when needed, and validate.
- **OKF tooling change**: changes `mcp/okf.py`, MCP tools, `mcp/cli.py`,
  `simple_okf_mcp/`, or package configuration. Run Python compile checks and
  relevant CLI smoke tests.
- **RAG tooling change**: changes `mcp/rag/` or RAG CLI behavior. Test with an env
  file and ensure `mcp/rag/.env` remains uncommitted.
- **Agent instruction change**: changes `AGENTS.md`, `.agents/skills/okf/`, or
  `.agents/skills/7d/`. Keep rules consistent with `README.md` and `SPEC.md`.
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
python3 -m py_compile mcp/*.py simple_okf_mcp/*.py mcp/rag/*.py mcp/rag/ingestion/*.py mcp/rag/retrieval/*.py
python3 -m mcp validate okf
python3 -m mcp graph okf --out artifacts/okf/graph.json --html-out artifacts/okf/graph.html
git diff --check
git status --short
git diff --stat
```

For RAG changes, also smoke-test with a local env file. If `mcp/rag/.env` is not
available, either use a temporary env file via `--env` or report that RAG runtime
validation was skipped because the local env file is absent.

For OKF content additions/removals/renames, also run:

```sh
python3 -m mcp indexes okf
python3 -m mcp graph okf --out artifacts/okf/graph.json --html-out artifacts/okf/graph.html
python3 -m mcp validate okf
```

## Reporting

When finishing work, report:

1. files changed;
2. commands run and results;
3. whether OKF validation passed;
4. whether indexes/graph/RAG artifacts were regenerated;
5. remaining gaps or follow-up questions.
