.PHONY: setup fetch-data data data-check test lint typecheck web-build scan-forbidden scan-secrets \
	facts baseline run-replay run-live run-live-smoke serve export screenshots all e2e release-check \
	results-manifest results-manifest-check

PYTHON := uv run python
FQA := uv run fqa

setup:
	uv sync --all-groups
	cd web && npm install

fetch-data:
	$(FQA) data --refresh

data:
	$(FQA) data

data-check:
	$(PYTHON) scripts/check_data.py

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

web-build:
	cd web && npm run build

scan-forbidden:
	$(PYTHON) scripts/scan_forbidden.py

scan-secrets:
	$(PYTHON) scripts/scan_secrets.py

facts:
	$(PYTHON) scripts/check_facts.py

baseline:
	$(FQA) baseline

run-replay:
	# --legacy-recorded-input replays the frozen Q9 requests, which still carry
	# the PLAN §7 evaluation labels. The run manifest records that policy and the
	# label-dependent metrics are withheld. New runs must not use the flag.
	$(FQA) run --mode replay --set replay_2025 --run-id replay --legacy-recorded-input

run-live:
	@if [ "$${FQA_LIVE_APPROVED:-}" != "1" ]; then \
		echo "run-live is reserved for Q9/Q14; set FQA_LIVE_APPROVED=1 to approve real calls."; \
		exit 2; \
	fi
	$(FQA) run --mode record --set replay_2025 --run-id live-2025

run-live-smoke:
	@if [ "$${FQA_LIVE_APPROVED:-}" != "1" ]; then \
		echo "run-live-smoke makes real calls; set FQA_LIVE_APPROVED=1 to approve them."; \
		exit 2; \
	fi
	$(FQA) run --mode record --set replay_2025 --run-id live-2025-smoke --limit 20

serve:
	$(FQA) serve

export:
	$(FQA) export --run-id replay

screenshots:
	@test -f dist/field-quality-agents/index.html || { \
		echo "screenshots: no static export yet; run make all first"; \
		exit 2; \
	}
	cd web && FQA_SCREENSHOT_DIR="$(CURDIR)/results/screenshots" \
		NODE_PATH="$$PWD/node_modules" \
		npx playwright test --config ../tests/web/playwright.export.config.ts

results-manifest:
	$(PYTHON) scripts/results_manifest.py write

results-manifest-check: web-build export
	$(PYTHON) scripts/results_manifest.py check

all: data-check baseline run-replay web-build export results-manifest
	@echo "all: data checked, baseline, replay run, dashboard data and web build are up to date"

e2e: web-build
	$(FQA) run --mode replay --set replay_2025 --run-id e2e-fixture \
		--fixture-sql tests/fixtures/e2e/replay_2025.sql \
		--recordings-dir tests/fixtures/recordings
	$(FQA) export --out dist/field-quality-agents --run-id e2e-fixture
	cd web && NODE_PATH="$$PWD/node_modules" npx playwright test --config ../tests/e2e/playwright.config.ts

release-check: lint typecheck test web-build scan-forbidden scan-secrets facts results-manifest-check
	@echo "release-check: green"
