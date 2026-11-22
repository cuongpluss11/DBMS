#!/usr/bin/env bash
# Chạy thí nghiệm E1 (mục 2.4): Đổi lược đồ gốc dưới tải + kẹt Metadata Lock.
# Lưu kết quả vào results/official/2.4-e1/ (tự động tái sử dụng dataset W=10 đã nạp).
#
# Cách dùng trên VM:
#   bash scripts/run-2.4-e1.sh mysql
#   bash scripts/run-2.4-e1.sh mongo
#   PROFILE=configs/smoke.toml REPS=1 LONG_TXN_S=8 OUT_DIR=results/smoke-2.4-e1 bash scripts/run-2.4-e1.sh mysql
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

if [[ ! -x .venv/bin/flashsale ]]; then
    bash scripts/setup.sh
fi
source .venv/bin/activate

ENGINES=("${@:-mysql}")
if [[ $# -eq 0 ]]; then
    ENGINES=(mysql)
fi

PROFILE="${PROFILE:-configs/migration.toml}"
REPS="${REPS:-3}"
LONG_TXN_S="${LONG_TXN_S:-60}"
DDL_DELAY_S="${DDL_DELAY_S:-5}"
SHORT_TIMEOUT_S="${SHORT_TIMEOUT_S:-3}"
OUT_DIR="${OUT_DIR:-results/official/2.4-e1}"
EVIDENCE_DIR="$OUT_DIR/evidence"
mkdir -p "$OUT_DIR" "$EVIDENCE_DIR"

export FLASHSALE_MYSQL_MAX_CONNECTIONS="${FLASHSALE_MYSQL_MAX_CONNECTIONS:-400}"
export FLASHSALE_MYSQL_BUFFER_POOL_BYTES="${FLASHSALE_MYSQL_BUFFER_POOL_BYTES:-3221225472}"

flashsale doctor | tee "$EVIDENCE_DIR/doctor.json"

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

for ENGINE in "${ENGINES[@]}"; do
    ENG_EVIDENCE="$EVIDENCE_DIR/$ENGINE"
    mkdir -p "$ENG_EVIDENCE"

    if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
        flashsale start "$ENGINE"
    fi
    flashsale status "$ENGINE" | tee "$ENG_EVIDENCE/status.json"

    DATASET="${FLASHSALE_DATASET:-$(find_existing_dataset "$ENGINE" "$PROFILE")}"
    if [[ -n "$DATASET" ]]; then
        printf 'Tái sử dụng dataset đã nạp trên VM: %s\n' "$DATASET"
        flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" \
            | tee "$ENG_EVIDENCE/load.json"
    else
        printf 'Chưa có dataset sẵn trên VM, đang nạp mới...\n'
        flashsale load "$ENGINE" --config "$PROFILE" | tee "$ENG_EVIDENCE/load.json"
        DATASET="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["database"])' "$ENG_EVIDENCE/load.json")"
    fi

    printf '\n=== [2.4 E1 – DDL gốc & MDL] Hệ: %s | reps=%s | long_txn=%ss ===\n' "$ENGINE" "$REPS" "$LONG_TXN_S"
    python -m flashsale.e1_ddl "$ENGINE" \
        --config "$PROFILE" \
        --dataset "$DATASET" \
        --repetitions "$REPS" \
        --long-txn-seconds "$LONG_TXN_S" \
        --ddl-delay-seconds "$DDL_DELAY_S" \
        --short-lock-timeout "$SHORT_TIMEOUT_S" \
        --out-dir "$OUT_DIR" \
        | tee "$ENG_EVIDENCE/e1-runs.json"

    if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
        flashsale stop "$ENGINE"
    fi
done

printf '\nHoàn tất E1! Kết quả và E1_SUMMARY.md đã lưu tại: %s\n' "$OUT_DIR"
