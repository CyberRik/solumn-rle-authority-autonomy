#!/bin/sh
# CI entry point: tests, then the coverage gate (configured in pyproject.toml).
set -e
cd "$(dirname "$0")/.."
python -m coverage erase
python -m coverage run -m pytest -q
python -m coverage report
