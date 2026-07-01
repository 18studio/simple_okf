PY ?= python3
UV ?= uv
BUNDLE ?= okf
ARTIFACTS_DIR ?= artifacts
RAG_ENV ?= okf_mcp/rag/.env
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

.PHONY: help init validate test smoke e2e quality live-agent docker-compose-check rag-check indexes graph 7d-report 7d-dashboard 7d-validate guard-artifacts-dir clean-artifacts clean-project reset-empty

help:
	@echo "Targets:"
	@echo "  make init                 Install deps, create RAG env, validate and refresh RAG"
	@echo "  make validate             Compile MCP modules and validate the OKF bundle"
	@echo "  make test                 Run Python regression tests"
	@echo "  make smoke                Run fast local validation + tests"
	@echo "  make e2e                  Run deterministic local E2E checks"
	@echo "  make quality              Run infrastructure-backed quality checks"
	@echo "  make live-agent           Print gated live-agent acceptance instructions"
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
	@test -f $(RAG_ENV) || cp okf_mcp/rag/.env.example $(RAG_ENV)
	@mkdir -p $(ARTIFACTS_DIR)/rag
	$(MAKE) rag-check

validate:
	$(PY) -m py_compile okf_mcp/*.py okf_mcp/rag/*.py okf_mcp/rag/ingestion/*.py okf_mcp/rag/retrieval/*.py okf_mcp/rag/storage/*.py
	$(PY) -m okf_mcp validate $(BUNDLE)


test:
	$(PY) -m unittest discover -s tests -p 'test_*.py'

smoke: validate 7d-validate test indexes graph
	$(PY) -m okf_mcp rag inspect --env okf_mcp/rag/.env.example --pretty >/dev/null
	$(PY) -m okf_mcp rag refresh --env okf_mcp/rag/.env.example --pretty >/dev/null
	$(PY) -m okf_mcp rag retrieve "$(RAG_QUERY)" --env okf_mcp/rag/.env.example --limit 3 --pretty >/dev/null
	RAG_EVALUATION_MODE=always $(PY) -m okf_mcp rag retrieve "$(RAG_QUERY)" --env okf_mcp/rag/.env.example --answer --limit 3 --pretty >/dev/null

docker-compose-check:
	docker compose config >/dev/null

e2e: smoke docker-compose-check
	$(PY) -m okf_mcp rag retrieve "$(RAG_QUERY)" --env okf_mcp/rag/.env.example --answer --limit 3 --pretty >/dev/null
	@echo "Deterministic local E2E checks passed. See E2E_TEST_SPEC.md for full profile scope."

quality: docker-compose-check
	@if [ "$(QUALITY_INFRA)" = "1" ]; then \
		$(PY) -m okf_mcp rag refresh --mode hybrid --env $(RAG_ENV) --pretty >/dev/null; \
		RAG_EVALUATION_MODE=always RAG_EVENT_STORAGE_MODE=best-effort $(PY) -m okf_mcp rag retrieve "$(RAG_QUERY)" --mode hybrid --env $(RAG_ENV) --answer --pretty >/dev/null; \
	else \
		RAG_EVALUATION_MODE=always $(PY) -m okf_mcp rag retrieve "$(RAG_QUERY)" --env okf_mcp/rag/.env.example --answer --limit 3 --pretty >/dev/null; \
		echo "Quality profile ran deterministic local evaluator. Set QUALITY_INFRA=1 with running services for hybrid infra checks."; \
	fi

live-agent:
	@test -n "$(LIVE_AGENT_TRANSCRIPT)" || { echo "ERROR: set LIVE_AGENT_TRANSCRIPT to a captured sandbox transcript path"; exit 2; }
	@test -f "$(LIVE_AGENT_TRANSCRIPT)" || { echo "ERROR: transcript not found: $(LIVE_AGENT_TRANSCRIPT)"; exit 2; }
	@grep -Eq "sandbox|live-agent|validate" "$(LIVE_AGENT_TRANSCRIPT)" || { echo "ERROR: transcript does not look like a live-agent sandbox acceptance run"; exit 1; }
	@echo "Live-agent transcript gate passed: $(LIVE_AGENT_TRANSCRIPT)"

rag-check: validate
	@$(PY) -m okf_mcp rag inspect | $(PY) -c 'import json,sys; d=json.load(sys.stdin); print("RAG corpus: {} concepts, {} bytes -> {}".format(d["concept_count"], d["total_bytes"], d["artifacts_dir"]))'
	@$(PY) -m okf_mcp rag refresh | $(PY) -c 'import json,sys; d=json.load(sys.stdin); print("RAG index: {} chunks -> {}".format(d["chunk_count"], d["path"]))'
	@$(PY) -m okf_mcp rag retrieve "$(RAG_QUERY)" --limit 3 | $(PY) -c 'import json,sys; d=json.load(sys.stdin); print("RAG retrieve: {} hit(s) for {!r}".format(len(d["hits"]), d["query"]))'

indexes:
	$(PY) -m okf_mcp indexes $(BUNDLE)

graph:
	$(PY) -m okf_mcp graph $(BUNDLE) --out $(ARTIFACTS_DIR)/okf/graph.json --html-out $(ARTIFACTS_DIR)/okf/graph.html

7d-report:
	$(PY) -m okf_mcp 7d report --bundle $(BUNDLE)

7d-dashboard:
	$(PY) -m okf_mcp 7d dashboard --bundle $(BUNDLE) --out $(ARTIFACTS_DIR)/7d-dashboard.html

7d-validate:
	$(PY) -m okf_mcp 7d validate --bundle $(BUNDLE)

guard-artifacts-dir:
	@test "$(abspath $(ARTIFACTS_DIR))" = "$(abspath artifacts)" || { echo "ERROR: clean targets only support repository artifacts/; got ARTIFACTS_DIR=$(ARTIFACTS_DIR)"; exit 2; }

clean-artifacts: guard-artifacts-dir
	@rm -rf $(ARTIFACTS_DIR) .pytest_cache .mypy_cache .ruff_cache
	@find okf_mcp -type d -name __pycache__ -prune -exec rm -rf {} +
	@find okf_mcp -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	@echo "Generated artifacts removed."

clean-project reset-empty: guard-artifacts-dir
	@test "$(CONFIRM)" = "YES" || { echo "Destructive reset. Run: make clean-project CONFIRM=YES"; exit 2; }
	@mkdir -p $(OKF_DIRS)
	@find $(BUNDLE) -type f -name '*.md' ! -name index.md ! -name log.md -delete
	@rm -rf $(ARTIFACTS_DIR)
	@test -f $(BUNDLE)/log.md || printf '# Log\n\n' > $(BUNDLE)/log.md
	$(MAKE) indexes
	$(PY) -m okf_mcp validate $(BUNDLE)
	@echo "Project reset to an empty OKF bundle skeleton."
