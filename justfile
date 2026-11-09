set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

check: lint validate audit-seed test

lint:
    uv run --locked ruff check src tests/test_native.py tests/test_seed_evidence.py

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

audit-seed:
    uv run --locked python -m assaymech.seed_audit
