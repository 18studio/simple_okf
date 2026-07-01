# E2E Test Engineering Specification

## 1. Purpose

This document specifies end-to-end tests for Simple OKF. It is a test specification only; product and tooling rules live in [`OKF_RAG_7D_IMPLEMENTATION_SPEC.md`](./OKF_RAG_7D_IMPLEMENTATION_SPEC.md), [`SPEC.md`](./SPEC.md), [`README.md`](./README.md), [`AGENTS.md`](./AGENTS.md), and the agent skills.

E2E tests verify that the CLI, MCP server, skills-as-files, generated artifacts, local RAG entrypoints, and Docker Compose stack behave together according to those canonical contracts.

## 2. Goals and non-goals

### Goals

- Verify integrated OKF/7D contract behavior without redefining that contract here.
- Exercise MCP tools and matching CLI commands against disposable bundles.
- Verify Docker Compose startup/readiness behavior for the local MCP + RAG infrastructure stack.
- Support deterministic automated E2E tests and separate gated live-agent acceptance runs.
- Keep the repository `okf/` bundle immutable during tests unless a test explicitly targets a temporary copy.

### Non-goals

- No production OKF content creation from test scenarios.
- No standalone product roadmap, schema contract, or implementation backlog in this file; those belong in `OKF_RAG_7D_IMPLEMENTATION_SPEC.md` and other canonical docs.
- No replacement for unit tests; E2E focuses on integrated behavior and agent-visible contracts.

## 3. Test profiles

| Profile | Purpose | Required dependencies | Typical command shape |
|---|---|---|---|
| `smoke` | Fast verification of package, CLI validation, graph/index generation, selected RAG paths, and regression tests. | Python dependencies only; temp bundles/local artifacts. | `make smoke`. |
| `e2e` | Deterministic contract E2E for OKF, 7D, MCP tools, skills-as-files, Compose config, and fixture RAG. | Python, temp bundles, local artifacts, Docker Compose CLI. | `make e2e`. |
| `quality` | Retrieval/answer quality and event persistence scenarios for the RAG infrastructure. | ClickHouse, OpenSearch, Qdrant, model config where needed. | `QUALITY_INFRA=1 docker compose up -d ... && make quality`. |
| `live-agent` | Human/LLM acceptance flows using real agent skills and sandbox bundles. | Configured agent runtime, MCP server, full RAG infrastructure. | Gated job with transcript capture and `make live-agent LIVE_AGENT_TRANSCRIPT=...`. |

The human-readable live-agent profile name is `live-agent`; the Make target is `live-agent` and any future pytest marker should use `live_agent`.

## 4. Fixture and sandbox strategy

- Automated tests create temporary bundles, for example `tmp_path/bundles/valid-okf`, `tmp_path/bundles/invalid-status`, and `tmp_path/artifacts`.
- Fixtures cover valid and invalid concept frontmatter, mapped and unmapped types, links, generated indexes/graphs, and RAG metadata. Assertions reference the canonical rules in `SPEC.md` rather than restating them.
- Live-agent scenarios use disposable sandbox bundles under an ignored path such as `artifacts/live-agent-sandboxes/<run-id>/okf` or an external temporary directory.
- Mutation guards snapshot `okf/`, `artifacts/`, and git status before/after tests that must not modify the main bundle.

## 5. Harnesses

- **Fixture builder**: creates minimal OKF bundles with controlled frontmatter, links, and support files.
- **CLI harness**: runs `python -m okf_mcp ...` commands and captures exit code, stdout, stderr, and filesystem side effects.
- **MCP harness**: starts the MCP server against a fixture bundle, invokes tools/resources, and checks side effects only in the temp bundle/artifacts.
- **Skill contract harness**: statically checks `.agents/skills/*/SKILL.md` for required workflow references and uses live-agent scenarios where static checks are insufficient.
- **RAG harness**: inspects/refreshes/retrieves against fixture corpora; quality profile may also verify infrastructure-backed retrieval/event behavior.
- **Compose harness**: validates `docker compose config` and, in non-fast profiles, starts the local stack and waits for health/readiness.

## 6. MCP tool coverage matrix

Every MCP tool should have at least one automated E2E test. Tools that write must run only against temp bundles/artifact directories.

| Tool | Minimum E2E assertion |
|---|---|
| `bundle_info` | Returns active fixture bundle path, counts, validation status, warnings, and errors. |
| `list_concepts` | Lists concepts and filters by type/tag/query, including status metadata. |
| `search_concepts` | Finds known fixture content and excludes support files. |
| `list_directory` | Returns directory entries without escaping bundle root. |
| `read_concept` | Returns frontmatter, body, and metadata for a known concept. |
| `read_existing_doc` | Returns existing doc or `null` for absent doc without throwing. |
| `read_concept_raw` | Returns exact Markdown including frontmatter. |
| `sample_rows` | Reports unsupported sampling clearly for filesystem OKF. |
| `read_support_file` | Reads `index.md`/`log.md` and blocks path traversal. |
| `write_concept_doc` | Writes/merges frontmatter, preserves unknown fields, and enforces canonical validation. |
| `validate_bundle` | Mirrors CLI validation results for valid and invalid fixture bundles. |
| `seven_d_registry` | Returns all seven stages and registered mapped types. |
| `seven_d_mapping_for_type` | Returns mapping for registered types and `null` for unknown types. |
| `list_7d_artifact_concepts` | Lists mapped concepts and filters by stage. |
| `seven_d_stage_report` | Reports stage coverage, validation errors, and static gaps. |
| `seven_d_stage_report_markdown` | Renders equivalent Markdown report. |
| `seven_d_dashboard` | Generates dashboard under temp artifacts and includes stage/gap data. |
| `seven_d_feature_status` | Derives progress from linked artifacts and reports gaps. |
| `validate_7d` | Fails fixture bundles with unmapped types and reports details. |
| `generate_indexes` | Regenerates fixture `index.md` files only. |
| `export_source_documents` | Exports source docs to fixture bundle and is idempotent unless forced. |
| `build_graph` | Produces nodes/edges and optional JSON/HTML under temp artifacts. |
| `rag_readiness` | Reports reachable or intentionally unreachable configured infrastructure. |
| `rag_inspect_corpus` | Counts fixture concepts and excludes support files. |
| `rag_parse_chunks` | Preserves concept metadata and citation/line information. |
| `rag_refresh_index` | Builds fixture RAG artifacts. |
| `rag_retrieve` | Returns relevant fixture results with metadata filters. |
| `rag_answer` | Produces evidence-backed extractive answers and refuses unsupported claims. |
| `rag_get_source` | Returns exact source line ranges for citations. |
| `rag_concept_relationships` | Returns incoming/outgoing relationships to requested depth. |

MCP resources `okf://bundle/info`, `okf://bundle/index`, and `okf://bundle/graph` should be covered as read-only contract checks.

## 7. Representative scenarios

### OKF contract

- A valid fixture bundle passes CLI and MCP validation.
- Invalid fixtures fail with actionable errors for canonical contract violations defined in `SPEC.md`.
- Writing a concept through MCP preserves unknown frontmatter and validates the merged document.

### 7D reporting

- Registry lookup resolves each canonical/common mapped type used by fixtures and templates.
- Stage report and dashboard show required lifecycle coverage gaps separately from validation errors.
- Feature status derives the highest linked registered stage and reports linked gaps.

### RAG and readiness

- `rag inspect` and fixture local retrieval run without live infrastructure unless server readiness is invoked.
- MCP startup/readiness fails clearly when required infrastructure endpoints are unreachable.
- With the Compose stack healthy, MCP readiness succeeds before serving.

### Docker Compose

- `docker compose config` is valid.
- Non-fast profile starts the stack, waits for service health, and verifies the MCP HTTP endpoint/tool access.

### Live-agent acceptance

- Agent runs use a sandbox bundle, record transcript/tool calls, and never mutate repository `okf/`.
- The agent uses repository skills, writes canonical frontmatter, runs required sandbox validations, and reports unresolved gaps.

## 8. CI command examples

```sh
python3 -m py_compile okf_mcp/*.py okf_mcp/rag/*.py okf_mcp/rag/ingestion/*.py okf_mcp/rag/retrieval/*.py
python3 -m okf_mcp validate okf
python3 -m okf_mcp 7d validate --bundle okf
python3 -m okf_mcp indexes okf
python3 -m okf_mcp graph okf --out artifacts/okf/graph.json --html-out artifacts/okf/graph.html
python3 -m okf_mcp rag inspect --env okf_mcp/rag/.env.example --pretty
docker compose config
make smoke
make e2e
make quality
make live-agent LIVE_AGENT_TRANSCRIPT=artifacts/live-agent-sandboxes/<run-id>/transcript.json
```

Do not run infrastructure-heavy profiles in fast local checks unless the environment is known to be available.
