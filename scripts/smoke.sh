#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
if (( $# )); then
    exec .venv/bin/flashsale smoke "$@" --start
fi
for engine in mysql mongo tidb; do
    .venv/bin/flashsale smoke "$engine" --start
done
