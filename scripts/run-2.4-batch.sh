#!/usr/bin/env bash
# Chạy thực nghiệm mục 2.4 – Chiến lược P2 (Chuyển theo lô nền / Batch Background Migration)
# với hai cỡ lô theo tài liệu (1.000 và 5.000 dòng) và đóng gói kết quả + bằng chứng vào results/official/2.4-batch/.
# Tự động tái sử dụng dataset W=10 đã nạp trên VM (nếu có) bằng lệnh `flashsale reset` để tiết kiệm thời gian nạp.
#
# Cách dùng trên VM:
#   bash scripts/run-2.4-batch.sh mysql                # Chạy Batch P2 (lô 1000 và 5000) trên MySQL
#   BATCH_SIZES="1000" bash scripts/run-2.4-batch.sh mysql   # Chỉ chạy lô 1000
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

if [[ ! -x .venv/bin/flashsale ]]; then
    if ! bash scripts/setup.sh; then
        python3.12 -m venv .venv
        .venv/bin/python -m pip install -r requirements-dev.txt
        .venv/bin/python -m pip install --no-deps -e .
        .venv/bin/python -m pytest -m 'not integration' -q
    fi
fi
source .venv/bin/activate

ENGINES=("${@:-mysql}")
if [[ $# -eq 0 ]]; then
    ENGINES=(mysql)
fi

PROFILE="${PROFILE:-configs/migration.toml}"
Q_PCT="${Q_PCT:-25}"
REPS="${REPS:-3}"
BATCH_SIZES="${BATCH_SIZES:-1000 5000}"
SLEEP_MS="${SLEEP_MS:-20}"
OUT_DIR="${OUT_DIR:-results/official/2.4-batch}"
EVIDENCE_DIR="$OUT_DIR/evidence"
mkdir -p "$OUT_DIR" "$EVIDENCE_DIR"

export FLASHSALE_MYSQL_MAX_CONNECTIONS="${FLASHSALE_MYSQL_MAX_CONNECTIONS:-400}"
export FLASHSALE_MYSQL_BUFFER_POOL_BYTES="${FLASHSALE_MYSQL_BUFFER_POOL_BYTES:-3221225472}"

flashsale doctor | tee "$EVIDENCE_DIR/doctor.json"
lscpu > "$EVIDENCE_DIR/lscpu.txt" 2>/dev/null || true
lsblk -o NAME,SIZE,TYPE,ROTA > "$EVIDENCE_DIR/lsblk.txt" 2>/dev/null || true

copy_runs() {
    local json_file="$1"
    python - "$json_file" "$OUT_DIR" <<'PY'
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

for ENGINE in "${ENGINES[@]}"; do
    ENG_EVIDENCE="$EVIDENCE_DIR/$ENGINE"
    mkdir -p "$ENG_EVIDENCE"

    if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
        flashsale start "$ENGINE"
    fi

    flashsale status "$ENGINE" | tee "$ENG_EVIDENCE/status.json"

    if [[ "$PROFILE" == "configs/smoke.toml" ]]; then
        for BSIZE in $BATCH_SIZES; do
            printf '\n=== [2.4 Batch P2 Smoke] Hệ: %s | batch_size=%s | q=%s%% ===\n' "$ENGINE" "$BSIZE" "$Q_PCT"
            flashsale smoke "$ENGINE" --migration-strategy batch --migration-batch-size "$BSIZE" \
                --migration-sleep-ms "$SLEEP_MS" --old-order-read-pct "$Q_PCT" \
                | tee "$ENG_EVIDENCE/batch-${BSIZE}-runs.json"
            copy_runs "$ENG_EVIDENCE/batch-${BSIZE}-runs.json"
        done
    else
        DATASET="${FLASHSALE_DATASET:-$(find_existing_dataset "$ENGINE" "$PROFILE")}"
        if [[ -n "$DATASET" ]]; then
            printf 'Tái sử dụng dataset đã nạp trên VM: %s (đang reset về trạng thái chuẩn)...\n' "$DATASET"
            flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" \
                | tee "$ENG_EVIDENCE/load.json"
        else
            printf 'Chưa có dataset sẵn trên VM, đang nạp mới...\n'
            flashsale load "$ENGINE" --config "$PROFILE" | tee "$ENG_EVIDENCE/load.json"
            DATASET="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["database"])' "$ENG_EVIDENCE/load.json")"
        fi

        FIRST_BATCH=1
        for BSIZE in $BATCH_SIZES; do
            printf '\n=== [2.4 Batch P2] Hệ: %s | batch_size=%s | sleep=%sms | q=%s%% ===\n' "$ENGINE" "$BSIZE" "$SLEEP_MS" "$Q_PCT"
            if [[ $FIRST_BATCH -eq 0 ]]; then
                flashsale reset "$ENGINE" --config "$PROFILE" --dataset "$DATASET" --confirm "$DATASET" >/dev/null
            fi
            FIRST_BATCH=0
            flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
                --migration-strategy batch --migration-batch-size "$BSIZE" \
                --migration-sleep-ms "$SLEEP_MS" --old-order-read-pct "$Q_PCT" \
                --repetitions "$REPS" --reset-between \
                | tee "$ENG_EVIDENCE/batch-${BSIZE}-runs.json"
            copy_runs "$ENG_EVIDENCE/batch-${BSIZE}-runs.json"
        done
    fi

    if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
        flashsale stop "$ENGINE"
    fi
done

flashsale report --results-dir "$OUT_DIR" --out "$OUT_DIR" | tee "$EVIDENCE_DIR/report.json"
printf '\nHoàn tất! Kết quả và bằng chứng Batch P2 đã lưu tại: %s\n' "$OUT_DIR"
