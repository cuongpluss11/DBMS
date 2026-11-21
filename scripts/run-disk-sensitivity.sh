#!/usr/bin/env bash
# Thí nghiệm riêng "độ nhạy của đĩa" (MySQL một nút, MySQL-chỉnh): chạy cùng một bộ điểm đo ở một mức IOPS của ổ EBS.
# Chạy MỘT lần cho mỗi mức IOPS (3000, rồi 10000) trên cùng VM và cùng dataset để so cặp.
# Dùng: scripts/run-disk-sensitivity.sh <dataset> <iops>
# Cần: MySQL đã chạy với buffer pool lớn hơn mặc định (baseline-tuned), biến môi trường remote (xem infra/aws/README.md).
# FLASHSALE_IOSTAT_SSH=user@host (tùy chọn) để ghi iostat của VM MySQL cho từng điểm.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
DATASET="${1:?Thiếu tên dataset}"
IOPS="${2:?Thiếu mức IOPS của ổ (chỉ để ghi nhãn)}"
FS="${FLASHSALE_BIN:-flashsale}"
LOG="${DISK_LOG_DIR:-results/disk-sensitivity-iops$IOPS-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$LOG"
export FLASHSALE_RUN_NOTE="ebs_iops=$IOPS"

say() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG/disk.log"; }

point() {
    local label="$1"
    shift
    local out="$LOG/$label"
    mkdir -p "$out"
    say "Điểm $label ($*)"
    local pid=""
    if [[ -n "${FLASHSALE_IOSTAT_SSH:-}" ]]; then
        ssh -o BatchMode=yes "$FLASHSALE_IOSTAT_SSH" "iostat -x -d -t 1" >"$out/iostat.txt" 2>&1 &
        pid=$!
    fi
    local status=0
    "$FS" reset mysql --config configs/performance.toml --dataset "$DATASET" --confirm "$DATASET" >"$out/reset.json" 2>"$out/reset.err" || status=$?
    ((status == 0)) && "$FS" run mysql --config configs/performance.toml --dataset "$DATASET" --reset-between "$@" \
        >"$out/run.json" 2>"$out/run.err" || status=$?
    [[ -n "$pid" ]] && { kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; }
    ((status == 0)) || { say "LỖI hoặc INVALID ở $label (mã $status); xem $out/run.err"; exit "$status"; }
}

say "Độ nhạy đĩa: iops=$IOPS dataset=$DATASET log=$LOG"
point c8-theta0 --theta 0 --concurrency 8
point c64-theta0 --theta 0 --concurrency 64
point c64-theta0.9 --theta 0.9 --concurrency 64
say "Xong. Tổng hợp: $FS report --results-dir results --out $LOG/report"
