PY ?= python3
UV ?= uv
BUNDLE ?= okf
ARTIFACTS_DIR ?= artifacts
RAG_ENV ?= mcp/rag/.env
RAG_QUERY ?= okf

OKF_DIRS := \
	$(BUNDLE)/documents \
	$(BUNDLE)/requirements/functions \
	$(BUNDLE)/requirements/flows \
	$(BUNDLE)/requirements/rules \
	$(BUNDLE)/requirements/access \
	$(BUNDLE)/data/entities \
	$(BUNDLE)/api/operations \
	$(BUNDLE)/architecture/adr \
	$(BUNDLE)/ui/ux \
	$(BUNDLE)/ui/design-system \
	$(BUNDLE)/ui/uikit

.PHONY: help init validate rag-check indexes graph 7d-report 7d-dashboard 7d-validate guard-artifacts-dir clean-artifacts clean-project reset-empty

help:
	@echo "Targets:"
	@echo "  make init                 Install deps, create RAG env, validate and refresh RAG"
	@echo "  make validate             Compile MCP modules and validate the OKF bundle"
	@echo "  make indexes              Regenerate OKF index.md files"
	@echo "  make graph                Generate graph JSON/HTML under artifacts/okf"
	@echo "  make rag-check            Validate OKF, inspect RAG, refresh local RAG index"
	@echo "  make 7d-report           Generate a compact report by 7D stage"
	@echo "  make 7d-dashboard        Generate interactive 7D Kanban HTML dashboard"
	@echo "  make 7d-validate         Validate 7D registry usage"
	@echo "  make clean-artifacts      Remove generated artifacts/caches only"
	@echo "  make clean-project CONFIRM=YES"
	@echo "                            Remove all OKF concepts + artifacts; keep empty bundle skeleton"

init:
	@command -v $(UV) >/dev/null || { echo "ERROR: uv is required"; exit 2; }
	$(UV) sync
	@test -f $(RAG_ENV) || cp mcp/rag/.env.example $(RAG_ENV)
	@mkdir -p $(ARTIFACTS_DIR)/rag
	$(MAKE) rag-check

validate:
	$(PY) -m py_compile mcp/*.py simple_okf_mcp/*.py mcp/rag/*.py mcp/rag/ingestion/*.py mcp/rag/retrieval/*.py
	$(PY) -m mcp validate $(BUNDLE)

rag-check: validate
	@$(PY) -m mcp rag inspect | $(PY) -c 'import json,sys; d=json.load(sys.stdin); print("RAG corpus: {} concepts, {} bytes -> {}".format(d["concept_count"], d["total_bytes"], d["artifacts_dir"]))'
	@$(PY) -m mcp rag refresh | $(PY) -c 'import json,sys; d=json.load(sys.stdin); print("RAG index: {} chunks -> {}".format(d["chunk_count"], d["path"]))'
	@$(PY) -m mcp rag retrieve "$(RAG_QUERY)" --limit 3 | $(PY) -c 'import json,sys; d=json.load(sys.stdin); print("RAG retrieve: {} hit(s) for {!r}".format(len(d["hits"]), d["query"]))'

indexes:
	$(PY) -m mcp indexes $(BUNDLE)

graph:
	$(PY) -m mcp graph $(BUNDLE) --out $(ARTIFACTS_DIR)/okf/graph.json --html-out $(ARTIFACTS_DIR)/okf/graph.html

7d-report:
	$(PY) -m mcp 7d report --bundle $(BUNDLE)

7d-dashboard:
	$(PY) -m mcp 7d dashboard --bundle $(BUNDLE) --out $(ARTIFACTS_DIR)/7d-dashboard.html

7d-validate:
	$(PY) -m mcp 7d validate --bundle $(BUNDLE)

guard-artifacts-dir:
	@test "$(abspath $(ARTIFACTS_DIR))" = "$(abspath artifacts)" || { echo "ERROR: clean targets only support repository artifacts/; got ARTIFACTS_DIR=$(ARTIFACTS_DIR)"; exit 2; }

clean-artifacts: guard-artifacts-dir
	@rm -rf $(ARTIFACTS_DIR) .pytest_cache .mypy_cache .ruff_cache
	@find mcp -type d -name __pycache__ -prune -exec rm -rf {} +
	@find mcp -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	@echo "Generated artifacts removed."

clean-project reset-empty: guard-artifacts-dir
	@test "$(CONFIRM)" = "YES" || { echo "Destructive reset. Run: make clean-project CONFIRM=YES"; exit 2; }
	@mkdir -p $(OKF_DIRS)
	@find $(BUNDLE) -type f -name '*.md' ! -name index.md ! -name log.md -delete
	@rm -rf $(ARTIFACTS_DIR)
	@test -f $(BUNDLE)/log.md || printf '# Log\n\n' > $(BUNDLE)/log.md
	$(MAKE) indexes
	$(PY) -m mcp validate $(BUNDLE)
	@echo "Project reset to an empty OKF bundle skeleton."
