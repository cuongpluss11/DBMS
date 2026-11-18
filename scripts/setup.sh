#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

if [[ $# -gt 1 || ( $# -eq 1 && $1 != --smoke-all ) ]]; then
    printf 'Cách dùng: bash scripts/setup.sh [--smoke-all]\n' >&2
    exit 2
fi
bash scripts/doctor.sh --vm
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -m 'not integration' -q

if [[ ${1:-} == --smoke-all ]]; then
    for engine in mysql mongo tidb; do
        docker compose -f "docker/compose.$engine.yml" pull
        .venv/bin/flashsale smoke "$engine" --start
    done
fi
