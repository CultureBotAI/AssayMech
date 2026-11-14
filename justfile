set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

check: lint validate audit-seed test

lint:
    uv run --locked ruff check src tests/test_native.py scripts/check_review_event_base.py tests/test_review_event_base.py tests/test_seed_evidence.py tests/test_site.py scripts/adhoc/verify_site_browser.py

validate:
    uv run --locked assaymech validate

validate-schema:
    uv run --locked assaymech validate-schema

validate-data: validate

validate-all: validate

test:
    uv run --locked pytest -q

check-vendored:
    bash scripts/check_vendored_sync.sh

new-history *args:
    uv run --locked assaymech new-history {{args}}

validate-history:
    uv run --locked assaymech validate

check-review-event-base:
    uv run --locked python scripts/check_review_event_base.py

audit-seed:
    uv run --locked python -m assaymech.seed_audit

# Deterministic generated output stays under ignored build/site.
build-site:
    uv run --locked python -m assaymech.site

check-site:
    uv run --locked python -m assaymech.site --check

# Template tooling is independently pinned; the governed project dependency is unchanged.
check-template:
    uv run --isolated --no-project --with "kg-microbe-orchestration @ git+https://github.com/CultureBotAI/culturebotai-claw.git@6e7887bf69328e72e950b9adc656b256b1c0e1c1" python -m kg_microbe_skills.template_cli check --target-root . --config workflow/mech-template.json
    uv run --isolated --no-project --with "kg-microbe-orchestration @ git+https://github.com/CultureBotAI/culturebotai-claw.git@6e7887bf69328e72e950b9adc656b256b1c0e1c1" python -m kg_microbe_workflows validate --profile workflow/mech-workflow.yaml --parent workflow/parent/mech-cycle.yaml --schema workflow/parent/workflow.yaml --repository-key assaymech
