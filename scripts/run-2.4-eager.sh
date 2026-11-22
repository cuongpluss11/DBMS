#!/usr/bin/env bash
# Chạy thực nghiệm mục 2.4 – Chiến lược P1 (Chuyển tập trung / Eager Migration) trên MySQL, MongoDB, TiDB
# và đóng gói toàn bộ kết quả + bằng chứng nhỏ gọn vào results/official/2.4-eager/ để commit và push lên GitHub.
#
# Cách dùng trên VM:
#   bash scripts/run-2.4-eager.sh                  # Chạy lần lượt cả 3 hệ: mysql, mongo, tidb (W=10, q=25%)
#   bash scripts/run-2.4-eager.sh mysql mongo      # Chỉ chạy các hệ chỉ định
#   PROFILE=configs/smoke.toml REPS=1 bash scripts/run-2.4-eager.sh mysql   # Chạy thử nhanh quy mô smoke
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

if [[ ! -x .venv/bin/flashsale ]]; then
    if ! bash scripts/setup.sh; then
        printf 'Thiết lập .venv trực tiếp (cho phép VM 8 vCPU như m6i.2xlarge khi chờ duyệt quota)...\n' >&2
        python3.12 -m venv .venv
        .venv/bin/python -m pip install -r requirements-dev.txt
        .venv/bin/python -m pip install --no-deps -e .
        .venv/bin/python -m pytest -m 'not integration' -q
    fi
fi
source .venv/bin/activate

ENGINES=("${@:-mysql mongo tidb}")
if [[ $# -eq 0 ]]; then
    ENGINES=(mysql mongo tidb)
fi

PROFILE="${PROFILE:-configs/migration.toml}"
Q_PCT="${Q_PCT:-25}"
REPS="${REPS:-3}"
OUT_DIR="${OUT_DIR:-results/official/2.4-eager}"
EVIDENCE_DIR="$OUT_DIR/evidence"
mkdir -p "$OUT_DIR" "$EVIDENCE_DIR"

# Mục 2.2–2.5 dùng MySQL-chỉnh (buffer pool 3 GiB) và max_connections=400 cho 64–256 client.
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
    # Chỉ chép các file kết quả chính thức nhỏ gọn (không commit successful_new_orders.json vào Git theo AGENTS.md).
    for name in ("manifest.json", "result.json", "result.csv", "tps_per_second.csv"):
        if (src / name).is_file():
            shutil.copy2(src / name, dst / name)
PY
}

for ENGINE in "${ENGINES[@]}"; do
    printf '\n=== [2.4 Eager P1] Hệ: %s | Profile: %s | q=%s%% ===\n' "$ENGINE" "$PROFILE" "$Q_PCT"
    ENG_EVIDENCE="$EVIDENCE_DIR/$ENGINE"
    mkdir -p "$ENG_EVIDENCE"

    if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
        flashsale start "$ENGINE"
    fi

    flashsale status "$ENGINE" | tee "$ENG_EVIDENCE/status.json"
    FLASHSALE_TEST_ENGINE="$ENGINE" python -m pytest -m integration -k "migration" -q \
        2>&1 | tee "$ENG_EVIDENCE/integration-migration.log"

    if [[ "$PROFILE" == "configs/smoke.toml" ]]; then
        flashsale smoke "$ENGINE" --migration-strategy eager --old-order-read-pct "$Q_PCT" \
            | tee "$ENG_EVIDENCE/eager-runs.json"
        copy_runs "$ENG_EVIDENCE/eager-runs.json"
    else
        flashsale load "$ENGINE" --config "$PROFILE" | tee "$ENG_EVIDENCE/load.json"
        DATASET="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["database"])' "$ENG_EVIDENCE/load.json")"
        flashsale run "$ENGINE" --config "$PROFILE" --dataset "$DATASET" \
            --migration-strategy eager --old-order-read-pct "$Q_PCT" \
            --repetitions "$REPS" --reset-between \
            | tee "$ENG_EVIDENCE/eager-runs.json"
        copy_runs "$ENG_EVIDENCE/eager-runs.json"
    fi

    if [[ -z "${FLASHSALE_REMOTE_NODES:-}" ]]; then
        flashsale stop "$ENGINE"
    fi
done

flashsale report --results-dir "$OUT_DIR" --out "$OUT_DIR" | tee "$EVIDENCE_DIR/report.json"
printf '\nHoàn tất! Kết quả và bằng chứng đã được lưu tại: %s\n' "$OUT_DIR"
