# OKF, 7D, RAG, and Agent Workflow Implementation Specification

## 1. Purpose

This document captures the product and tooling tasks that were identified while designing the E2E test program. It is the implementation specification for the Simple OKF operating model; E2E tests should verify this contract but should not be the canonical place where the contract is defined.

The target system is a single OKF-based documentation and process environment tied to the 7D lifecycle. Agents should be able to use it to create the right documents, track document state, find only the context needed for a task, and surface gaps instead of inventing missing information.

## 2. Problem statement

The project needs to support many documents across product discovery, design, development, deployment, operations, defense, and decommissioning. It is not practical to place every document into every agent context. The system must therefore provide:

- a strict and machine-checkable OKF document contract;
- 7D mapping and gap analysis from document metadata;
- MCP tools for precise retrieval and document operations;
- RAG infrastructure for fast keyword and semantic retrieval;
- continuous quality/audit data for RAG answers;
- skills that guide humans and agents through the documentation process without inventing facts.

## 3. Scope

### In scope

- OKF concept metadata contract.
- 7D type registry and static gap analysis.
- Document status lifecycle semantics.
- Agent skill behavior for `grillme`, `okf`, and `7d` workflows.
- MCP startup readiness for RAG infrastructure.
- Docker Compose local infrastructure for ClickHouse, OpenSearch, and Qdrant.
- RAG architecture direction: OpenSearch keyword search, Qdrant vector search, hybrid retrieval, RAGAS evaluation, and ClickHouse event storage.
- Documentation alignment across `SPEC.md`, `README.md`, `AGENTS.md`, and skill docs.

### Out of scope for this specification

- The E2E test suite design itself; see [`E2E_TEST_SPEC.md`](./E2E_TEST_SPEC.md).
- Full implementation details for every future retriever/reranker algorithm.
- Provider-specific embedding/evaluator LLM configuration beyond environment-driven integration points.

## 4. Canonical OKF concept contract

Every OKF concept is a Markdown file with YAML frontmatter under `okf/`, excluding support files `index.md` and `log.md`.

Required frontmatter:

```yaml
type: Function Requirement
status: draft
```

Rules:

1. `type` is required.
2. `type` must be registered in the 7D type registry.
3. An unmapped `type` is a validation error.
4. `status` is required.
5. Allowed statuses are exactly:
   - `draft`
   - `to-review`
   - `not-valid`
   - `valid`
   - `rejected`
   - `accepted`
6. `status` describes the state of the document or 7D artifact, not runtime implementation progress.
7. Unknown frontmatter fields are allowed and must be preserved when editing existing concepts.
8. `title`, `description`, and `timestamp` remain recommended.

Recommended non-blocking status flow:

```text
draft -> to-review -> valid -> accepted
                  -> not-valid -> draft
                  -> rejected
```

The status transition flow is guidance only for now. Validation checks allowed values, not historical transitions.

## 5. 7D lifecycle contract

7D is a process registry over OKF concept `type` values. It must not require 7D-specific per-concept frontmatter such as `stage`, `process`, `raci`, `stage_order`, or `gate_decision`.

Rules:

1. 7D stage and responsibility are derived from the concept `type` via the registry.
2. Every concept `type` must have a registry mapping.
3. Missing or unmapped concept types are validation errors.
4. Missing required lifecycle artifacts are coverage gaps, not the same thing as invalid OKF syntax.
5. Auxiliary OKF concept types can be mapped to 7D without being required coverage artifacts.
6. Feature progress is derived from linked artifacts and their mapped 7D stages.
7. Static 7D analysis must surface gaps clearly in CLI, MCP tools, stage reports, dashboards, and feature status views.

Required lifecycle artifact types remain the core 7D process artifacts, for example `Product Brief`, `PRD`, `Architecture & NFR`, `Test Report`, `Deployment & Rollback Plan`, and related 7D documents. Common OKF types such as `Function Requirement`, `User Flow`, `Data Entity`, `UX Screen`, `UI Component`, `Architecture Decision`, `Gap`, and `Reference` are mapped so they can participate in retrieval and static analysis without creating false required-artifact gaps.

## 6. Skill workflow requirements

### `grillme`

The `grillme` skill must support a reasoning/interview mode for new features or plans.

Requirements:

- Ask questions in Russian, one at a time.
- Provide a recommended answer with each question.
- Explore the codebase instead of asking if the answer can be found from files.
- Identify which OKF/7D documents are needed for the feature.
- Continue until blocking questions are resolved or explicitly recorded as gaps.
- Do not invent requirements, schema details, citations, source paths, or domain facts.
- After the interview, create or update OKF concepts through the OKF workflow only when enough evidence exists.
- Write unresolved decisions as gaps/open questions, not guessed facts.

### `okf`

The `okf` skill must enforce the OKF contract:

- `type` and `status` are required.
- `type` must map to 7D.
- Unknown frontmatter fields must be preserved.
- Internal links should be relative Markdown links.
- Indexes, graph, and validation should be regenerated after content additions, removals, or relationship changes.

### `7d`

The `7d` skill must provide lifecycle analysis over OKF concepts:

- Resolve stages from `type` only.
- Report unmapped types as validation errors.
- Report missing required lifecycle artifacts as gaps.
- Derive feature progress from linked mapped concepts.
- Avoid adding 7D-specific frontmatter fields.

## 7. MCP and CLI requirements

MCP and CLI behavior must be consistent with the shared OKF library.

Required behavior:

- `write_concept_doc` rejects missing/invalid `status` and unmapped `type` after frontmatter merge.
- `validate_bundle` rejects invalid OKF concepts according to the canonical contract.
- `validate_7d` also rejects concepts that violate the canonical frontmatter contract.
- `read_concept`, `list_concepts`, parsed RAG documents, and graph/dashboard data expose `status` where relevant.
- 7D reports include validation errors and coverage gaps.
- Pure OKF operations such as validation, graph generation, index generation, and local corpus inspection must not require live RAG infrastructure.

## 8. RAG infrastructure architecture

The target RAG architecture has three required infrastructure components:

| Component | Responsibility | Primary data |
|---|---|---|
| OpenSearch | Keyword/full-text search and metadata filtering. | Indexed OKF chunks and metadata. |
| Qdrant | Semantic/vector search. | Embeddings for OKF chunks. |
| ClickHouse | Complete RAG/RAGAS evaluation event storage and analytics. | Retrieval, answer, metric, timing, citation, and error events. |
| Hybrid retriever | Combine OpenSearch and Qdrant results and rerank/merge them into minimal useful context. | Candidate results from OpenSearch and Qdrant. |
| RAGAS evaluator | Score retrieval and answer quality and emit evaluation fields for ClickHouse events. | Retrieved context, answer, question, references/expected facts where available. |

The retrieval path should evolve toward hybrid retrieval:

```text
OKF concepts -> chunks -> OpenSearch index
                    -> Qdrant collection
query -> keyword search + vector search -> merge/rerank -> answer/context
```

RAG must exclude support files `index.md` and `log.md` from the corpus.

RAG chunks should preserve at least:

- `concept_id`
- `type`
- `status`
- `title`
- `description`
- `tags`
- `requirement_id`
- `resource`
- `source_path`
- line ranges/citations where available

## 9. RAGAS and ClickHouse event storage

RAGAS is part of the normal RAG quality model, not only a separate report mode. The long-term system should continuously measure and persist RAG quality data.

ClickHouse should store full evaluation events, not only numeric metrics.

A complete event should include, where applicable:

- event ID and request/correlation ID;
- timestamp;
- bundle/corpus/index version metadata;
- MCP tool or skill name;
- user query/question;
- retrieval mode and filters;
- retrieved concept IDs and chunk IDs;
- retrieved scores and source metadata;
- cited concept IDs and line ranges;
- generated/extractive answer;
- RAGAS metric names, values, thresholds, and pass/fail status;
- evaluator model/config metadata;
- timing data;
- status such as `passed`, `degraded`, or `failed`;
- error details for failed retrieval/evaluation;
- enough raw inputs/outputs to debug and reproduce evaluation failures.

Initial quality metrics should include:

- context precision;
- context recall;
- faithfulness;
- answer relevancy;
- citation coverage;
- factual correctness when a reference answer exists.

## 10. MCP startup readiness

MCP server startup must check availability of all required RAG infrastructure components:

- ClickHouse;
- OpenSearch;
- Qdrant.

Rules:

1. Connection parameters come from `okf_mcp/rag/.env` or process environment.
2. `.env.example` documents all required keys without committing secrets.
3. Docker Compose provides default local infrastructure.
4. Compose service names are the default URLs inside the Compose network.
5. Host-side CLI/server runs must override URLs with host-reachable values such as `127.0.0.1`.
6. If any required component is unavailable during MCP server startup, the server must fail before reporting ready.
7. Pure local OKF/RAG inspection commands may remain infrastructure-free unless they explicitly invoke readiness.

## 11. Docker Compose local stack

The local Compose stack should include:

- `simple-okf` MCP HTTP service;
- `clickhouse`;
- `opensearch`;
- `qdrant`.

Requirements:

- Infrastructure services must have healthchecks.
- `simple-okf` must depend on healthy infrastructure services.
- Published ports should be bound to `127.0.0.1` for local development.
- Local secrets must not be committed.
- The ignored `okf_mcp/rag/.env` file must be easy to derive from `.env.example`.

## 12. Implementation status

This section is a point-in-time implementation snapshot. Refresh it when the implementation changes; canonical behavior remains defined by the requirements above and by `SPEC.md`.

Implemented in the current working tree:

- mandatory `status` validation in OKF concepts;
- allowed status values;
- unmapped `type` validation errors;
- current OKF bundle migrated to `status: draft`;
- common OKF concept types mapped in the 7D registry;
- `validate_7d` frontmatter validation;
- status metadata propagation through OKF/RAG model surfaces;
- RAG infrastructure settings in `.env.example` and config loading;
- MCP startup readiness probes for ClickHouse/OpenSearch/Qdrant;
- Docker Compose local infrastructure services and loopback-bound published ports;
- E2E specification cleanup so E2E rules are separate from product/tooling requirements;
- stdlib OpenSearch indexing and keyword retrieval adapter;
- stdlib Qdrant vector indexing and semantic retrieval adapter;
- deterministic embedding provider for local/test mode;
- hybrid retrieval mode with weighted reciprocal-rank fusion;
- deterministic RAGAS-like evaluator in normal answer flow;
- ClickHouse event schema and best-effort/required event writer;
- CLI and MCP retrieval mode selection for `local`, `keyword`, `semantic`, and `hybrid`;
- regression tests for strict validation, readiness failure, event/evaluator shape, local RAG mode, hybrid merge, and Compose loopback bindings;
- Make targets for smoke/e2e/quality/live-agent profile entrypoints;
- live Docker Compose validation for ClickHouse/OpenSearch/Qdrant readiness plus hybrid refresh/retrieve and ClickHouse event write.

Deferred implementation:

- external embedding provider integration beyond the deterministic provider seam;
- external evaluator/RAGAS package integration beyond the deterministic RAGAS-like evaluator seam;
- production-grade reranker plugin beyond weighted reciprocal-rank fusion;
- CI runner wiring outside this repository's local Make targets.

## 13. Acceptance criteria

The implementation is acceptable when:

- `python3 -m okf_mcp validate okf` passes on the current bundle;
- `python3 -m okf_mcp 7d validate --bundle okf` passes on the current bundle;
- temporary bundles fail validation for missing `status`, invalid `status`, missing `type`, and unmapped `type`;
- `write_concept_doc` rejects invalid merged frontmatter;
- current OKF concepts and templates include valid `status` values;
- 7D reports show validation errors and lifecycle coverage gaps distinctly;
- MCP startup fails clearly when required RAG infrastructure is unavailable;
- `docker compose config` includes ClickHouse, OpenSearch, Qdrant, and MCP service wiring;
- local published ports are not exposed on all host interfaces;
- `E2E_TEST_SPEC.md` remains test-only and points to canonical docs/specs for product behavior.

## 14. Validation commands

Recommended validation commands:

```sh
python3 -m py_compile okf_mcp/*.py okf_mcp/rag/*.py okf_mcp/rag/ingestion/*.py okf_mcp/rag/retrieval/*.py
python3 -m okf_mcp validate okf
python3 -m okf_mcp 7d validate --bundle okf
python3 -m okf_mcp indexes okf
python3 -m okf_mcp graph okf --out artifacts/okf/graph.json --html-out artifacts/okf/graph.html
python3 -m okf_mcp rag inspect --env okf_mcp/rag/.env.example --pretty
python3 -m okf_mcp rag refresh --env okf_mcp/rag/.env.example --pretty
docker compose config
git diff --check
git status --short
git diff --stat
```

For infrastructure runtime validation, run `docker compose up --build` in an environment where Docker startup is expected to be reliable.
