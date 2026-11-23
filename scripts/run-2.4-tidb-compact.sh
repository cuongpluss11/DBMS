#!/usr/bin/env bash
# Chạy trọn gói TiDB 8.5.x bản gọn cho mục 2.4 (Phương án 2):
#   - baseline : Đường nền không migration (none, q=25%) -> results/official/2.4-baseline/
#   - eager    : P1 Eager (q=25%)                        -> results/official/2.4-eager/
#   - batch    : P2 Batch 1.000 và 5.000 (q=25%)         -> results/official/2.4-batch/
#   - lazy     : P3 Lazy (q=25%)                         -> results/official/2.4-lazy/
#   - e1       : E1 Online DDL (ADD COLUMN, ADD INDEX, MDL 60s) -> results/official/2.4-e1/
#
# Cách dùng trên VM:
#   # 1. Smoke test nhanh (~2 phút):
#   PROFILE=configs/smoke.toml REPS=1 LONG_TXN_S=8 PARTS="eager e1" bash scripts/run-2.4-tidb-compact.sh
#   # 2. Chạy chính thức W=10 bản gọn (~1,5-2 giờ, bọc trong tmux):
#   bash scripts/run-2.4-tidb-compact.sh
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

if [[ ! -x .venv/bin/flashsale ]]; then
    bash scripts/setup.sh
fi
source .venv/bin/activate

ENGINE="tidb"
PROFILE="${PROFILE:-configs/migration.toml}"
REPS="${REPS:-3}"
Q_PCT="${Q_PCT:-25}"
LONG_TXN_S="${LONG_TXN_S:-60}"
PARTS="${PARTS:-baseline eager batch lazy e1}"

OUT_BASE="${OUT_BASE:-results/official/2.4-baseline}"
OUT_EAGER="${OUT_EAGER:-results/official/2.4-eager}"
OUT_BATCH="${OUT_BATCH:-results/official/2.4-batch}"
OUT_LAZY="${OUT_LAZY:-results/official/2.4-lazy}"
OUT_E1="${OUT_E1:-results/official/2.4-e1}"

if [[ "$PROFILE" == "configs/smoke.toml" ]]; then
    OUT_BASE="results/smoke-2.4-tidb/baseline"
    OUT_EAGER="results/smoke-2.4-tidb/eager"
    OUT_BATCH="results/smoke-2.4-tidb/batch"
    OUT_LAZY="results/smoke-2.4-tidb/lazy"
    OUT_E1="results/smoke-2.4-tidb/e1"
fi

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

mkdir -p "$OUT_BASE/evidence/$ENGINE"
flashsale status "$ENGINE" | tee "$OUT_BASE/evidence/$ENGINE/status.json"

DATASET="${FLASHSALE_DATASET:-$(find_existing_dataset "$ENGINE" "$PROFILE")}"
if [[ -n "$DATASET" ]]; then
    printf 'Tái sử dụng dataset TiDB đã nạp trên VM: %s\n' "$DATASET"
else
    printf 'Chưa có dataset TiDB trên VM, đang nạp mới (%s)...\n' "$PROFILE"
    flashsale load "$ENGINE" --config "$PROFILE" | tee "$OUT_BASE/evidence/$ENGINE/load.json"
    DATASET="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["database"])' "$OUT_BASE/evidence/$ENGINE/load.json")"
fi

if has_part "baseline"; then
    printf '\n=== [2.4 TiDB Baseline none] q=%s%% | θ=0.5 | 64 client ===\n' "$Q_PCT"
    flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
    flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
        --migration-strategy none --old-order-read-pct "$Q_PCT" \
        --repetitions "$REPS" --reset-between \
        | tee "$OUT_BASE/evidence/$ENGINE/none-q${Q_PCT}-runs.json"
    copy_runs "$OUT_BASE/evidence/$ENGINE/none-q${Q_PCT}-runs.json" "$OUT_BASE"
    flashsale report --results-dir "$OUT_BASE" --out "$OUT_BASE" >/dev/null
fi

if has_part "eager"; then
    mkdir -p "$OUT_EAGER/evidence/$ENGINE"
    printf '\n=== [2.4 TiDB P1 Eager] q=%s%% ===\n' "$Q_PCT"
    flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
    flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
        --migration-strategy eager --old-order-read-pct "$Q_PCT" \
        --repetitions "$REPS" --reset-between \
        | tee "$OUT_EAGER/evidence/$ENGINE/eager-runs.json"
    copy_runs "$OUT_EAGER/evidence/$ENGINE/eager-runs.json" "$OUT_EAGER"
    flashsale report --results-dir "$OUT_EAGER" --out "$OUT_EAGER" >/dev/null
fi

if has_part "batch"; then
    mkdir -p "$OUT_BATCH/evidence/$ENGINE"
    for BSIZE in 1000 5000; do
        printf '\n=== [2.4 TiDB P2 Batch %s] q=%s%% ===\n' "$BSIZE" "$Q_PCT"
        flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
        flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
            --migration-strategy batch --migration-batch-size "$BSIZE" --migration-sleep-ms 20 \
            --old-order-read-pct "$Q_PCT" --repetitions "$REPS" --reset-between \
            | tee "$OUT_BATCH/evidence/$ENGINE/batch-${BSIZE}-runs.json"
        copy_runs "$OUT_BATCH/evidence/$ENGINE/batch-${BSIZE}-runs.json" "$OUT_BATCH"
    done
    flashsale report --results-dir "$OUT_BATCH" --out "$OUT_BATCH" >/dev/null
fi

if has_part "lazy"; then
    mkdir -p "$OUT_LAZY/evidence/$ENGINE"
    printf '\n=== [2.4 TiDB P3 Lazy] q=%s%% ===\n' "$Q_PCT"
    flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
    flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
        --migration-strategy lazy --migration-batch-size 1000 --migration-sleep-ms 20 \
        --old-order-read-pct "$Q_PCT" --repetitions "$REPS" --reset-between \
        | tee "$OUT_LAZY/evidence/$ENGINE/lazy-q${Q_PCT}-runs.json"
    copy_runs "$OUT_LAZY/evidence/$ENGINE/lazy-q${Q_PCT}-runs.json" "$OUT_LAZY"
    flashsale report --results-dir "$OUT_LAZY" --out "$OUT_LAZY" >/dev/null
fi

if has_part "e1"; then
    mkdir -p "$OUT_E1/evidence/$ENGINE"
    printf '\n=== [2.4 TiDB E1 Online DDL] reps=%s | long_txn=%ss ===\n' "$REPS" "$LONG_TXN_S"
    python -m flashsale.e1_ddl "$ENGINE" \
        --config "$PROFILE" --dataset "$DATASET" \
        --repetitions "$REPS" --long-txn-seconds "$LONG_TXN_S" \
        --out-dir "$OUT_E1" \
        | tee "$OUT_E1/evidence/$ENGINE/e1-runs.json"
fi

if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
    flashsale stop "$ENGINE"
fi

printf '\nHoàn tất TiDB bản gọn (parts=[%s])!\n' "$PARTS"
