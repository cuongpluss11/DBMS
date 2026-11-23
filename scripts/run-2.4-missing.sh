#!/usr/bin/env bash
# Chạy toàn bộ các đo đạc còn thiếu của mục 2.4 trên MySQL hoặc MongoDB theo bản chốt:
#   1. baseline : Đường nền không migration (strategy=none) tại q ∈ {5%, 25%, 50%} (64 client, θ=0.5)
#                 -> lưu tại results/official/2.4-baseline/ (để tính chính xác % giảm TPS và lần tăng p99)
#   2. e3_batch : P2 Batch lô 1.000 ở q=5% và q=50% (bổ sung đủ đường P2 cho Biểu đồ 6b so với Lazy P3)
#                 -> lưu tại results/official/2.4-batch/
#   3. highload : E2 tải cao θ=0.9, 128 client, q=25% (none, eager, batch 1000, batch 5000, lazy)
#                 -> lưu tại results/official/2.4-highload/
#   4. e1       : E1 đổi lược đồ gốc dưới tải + kẹt Metadata Lock
#                 -> lưu tại results/official/2.4-e1/
#
# Cách dùng trên VM:
#   bash scripts/run-2.4-missing.sh mongo                         # Chạy đủ 4 phần cho MongoDB
#   bash scripts/run-2.4-missing.sh mysql                         # Chạy đủ 4 phần cho MySQL
#   PARTS="baseline e3_batch" bash scripts/run-2.4-missing.sh mongo   # Chỉ chạy phần chọn
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

if [[ ! -x .venv/bin/flashsale ]]; then
    bash scripts/setup.sh
fi
source .venv/bin/activate

ENGINE="${1:-mysql}"
PROFILE="${PROFILE:-configs/migration.toml}"
REPS="${REPS:-3}"
PARTS="${PARTS:-baseline e3_batch highload e1}"

export FLASHSALE_MYSQL_MAX_CONNECTIONS="${FLASHSALE_MYSQL_MAX_CONNECTIONS:-400}"
export FLASHSALE_MYSQL_BUFFER_POOL_BYTES="${FLASHSALE_MYSQL_BUFFER_POOL_BYTES:-3221225472}"

copy_runs() {
    local json_file="$1"
    local out_root="$2"
    python - "$json_file" "$out_root" <<'PY'
import json, shutil, sys
from pathlib import Path

runs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if isinstance(runs, dict):
    runs = [runs]
out_root = Path(sys.argv[2])
for item in runs:
    run_id = item["run_id"]
    src = Path("results") / run_id
    dst = out_root / run_id
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "result.json", "result.csv", "tps_per_second.csv"):
        if (src / name).is_file():
            shutil.copy2(src / name, dst / name)
PY
}

find_existing_dataset() {
    local engine="$1"
    local profile="$2"
    python - "$engine" "$profile" <<'PY'
import json, sys
from pathlib import Path
from flashsale.config import read_settings
from flashsale.data.loader import fingerprint

engine, profile = sys.argv[1], Path(sys.argv[2])
cfg = read_settings(profile)
fp = fingerprint(cfg.dataset, cfg.seed, cfg.idempotency)
ds_dir = Path("results/datasets")
if ds_dir.is_dir():
    for path in sorted(ds_dir.glob(f"{engine}-flashsale_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("fingerprint") == fp and "counts" in data:
                print(data["database"])
                sys.exit(0)
        except Exception:
            pass
PY
}

has_part() {
    [[ " $PARTS " == *" $1 "* ]]
}

if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
    flashsale start "$ENGINE"
fi

DATASET="${FLASHSALE_DATASET:-$(find_existing_dataset "$ENGINE" "$PROFILE")}"
if [[ -n "$DATASET" ]]; then
    printf 'Tái sử dụng dataset %s đã nạp trên VM: %s\n' "$ENGINE" "$DATASET"
else
    printf 'Chưa có dataset sẵn trên VM, đang nạp mới...\n'
    mkdir -p results/official/2.4-baseline/evidence/"$ENGINE"
    flashsale load "$ENGINE" --config "$PROFILE" | tee "results/official/2.4-baseline/evidence/$ENGINE/load.json"
    DATASET="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["database"])' "results/official/2.4-baseline/evidence/$ENGINE/load.json")"
fi

if has_part "baseline"; then
    OUT_BASE="results/official/2.4-baseline"
    mkdir -p "$OUT_BASE/evidence/$ENGINE"
    for Q in 5 25 50; do
        printf '\n=== [2.4 Baseline none] %s | q=%s%% | θ=0.5 | 64 client ===\n' "$ENGINE" "$Q"
        flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
        flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
            --migration-strategy none --old-order-read-pct "$Q" \
            --repetitions "$REPS" --reset-between \
            | tee "$OUT_BASE/evidence/$ENGINE/none-q${Q}-runs.json"
        copy_runs "$OUT_BASE/evidence/$ENGINE/none-q${Q}-runs.json" "$OUT_BASE"
    done
    flashsale report --results-dir "$OUT_BASE" --out "$OUT_BASE" >/dev/null
fi

if has_part "e3_batch"; then
    OUT_BATCH="results/official/2.4-batch"
    mkdir -p "$OUT_BATCH/evidence/$ENGINE"
    for Q in 5 50; do
        printf '\n=== [2.4 E3 Batch 1000] %s | q=%s%% | θ=0.5 | 64 client ===\n' "$ENGINE" "$Q"
        flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
        flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
            --migration-strategy batch --migration-batch-size 1000 --migration-sleep-ms 20 \
            --old-order-read-pct "$Q" --repetitions "$REPS" --reset-between \
            | tee "$OUT_BATCH/evidence/$ENGINE/batch-1000-q${Q}-runs.json"
        copy_runs "$OUT_BATCH/evidence/$ENGINE/batch-1000-q${Q}-runs.json" "$OUT_BATCH"
    done
    flashsale report --results-dir "$OUT_BATCH" --out "$OUT_BATCH" >/dev/null
fi

if has_part "highload"; then
    OUT_HL="results/official/2.4-highload"
    mkdir -p "$OUT_HL/evidence/$ENGINE"
    for SPEC in "none:0" "eager:0" "batch:1000" "batch:5000" "lazy:1000"; do
        STRAT="${SPEC%%:*}"
        BSIZE="${SPEC##*:}"
        printf '\n=== [2.4 E2 Tải cao] %s | strategy=%s | batch=%s | θ=0.9 | 128 client | q=25%% ===\n' \
            "$ENGINE" "$STRAT" "$BSIZE"
        flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
        EXTRA=()
        if [[ "$BSIZE" -gt 0 ]]; then
            EXTRA+=(--migration-batch-size "$BSIZE" --migration-sleep-ms 20)
        fi
        flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
            --theta 0.9 --concurrency 128 --old-order-read-pct 25 \
            --migration-strategy "$STRAT" "${EXTRA[@]}" \
            --repetitions "$REPS" --reset-between \
            | tee "$OUT_HL/evidence/$ENGINE/${STRAT}-${BSIZE}-runs.json"
        copy_runs "$OUT_HL/evidence/$ENGINE/${STRAT}-${BSIZE}-runs.json" "$OUT_HL"
    done
    flashsale report --results-dir "$OUT_HL" --out "$OUT_HL" >/dev/null
fi

if has_part "e1"; then
    FLASHSALE_DATASET="$DATASET" REPS="$REPS" bash scripts/run-2.4-e1.sh "$ENGINE"
else
    if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
        flashsale stop "$ENGINE"
    fi
fi

printf '\nHoàn tất các phần [%s] cho %s!\n' "$PARTS" "$ENGINE"
