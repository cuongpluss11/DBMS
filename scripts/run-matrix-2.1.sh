#!/usr/bin/env bash
# Chạy ma trận đo mục 2.1 cho MỘT hệ trên VM loadgen (chế độ remote, xem infra/aws/README.md).
# Dùng:  scripts/run-matrix-2.1.sh <mysql|mongo|tidb> [--grid evidence|full] [--dry-run]
#   --grid evidence (mặc định): θ ∈ {0; 0,3; 0,5; 0,7; 0,9; "1 món"} ở 8 client, và 8/32/64/128/256 client ở θ=0.
#   --grid full: toàn bộ lưới θ × client (đây là việc của 2.2/T1; rất lâu).
# Mỗi điểm chạy 3 lần (30 giây warmup + 60 giây đo) với --reset-between. Không xóa dữ liệu, không dừng DBMS.
# Biến môi trường:
#   FLASHSALE_BIN          lệnh flashsale (mặc định: flashsale)
#   FLASHSALE_IOSTAT_SSH   user@host của VM DBMS; nếu đặt, ghi iostat/vmstat của VM đó trong lúc đo
#   MATRIX_LOG_DIR         thư mục log (mặc định: results/matrix-<engine>-<giờ>)
# MySQL-chỉnh (baseline-tuned) cần khởi động lại MySQL với buffer pool lớn hơn: chạy riêng, xem README.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

ENGINE="${1:?Thiếu engine: mysql|mongo|tidb}"
shift || true
GRID=evidence
DRY=0
while (($#)); do
    case "$1" in
        --grid) GRID="${2:?}"; shift 2 ;;
        --dry-run) DRY=1; shift ;;
        *) echo "Tùy chọn lạ: $1" >&2; exit 2 ;;
    esac
done
case "$ENGINE" in mysql | mongo | tidb) ;; *) echo "engine không hợp lệ: $ENGINE" >&2; exit 2 ;; esac
case "$GRID" in evidence | full) ;; *) echo "--grid phải là evidence hoặc full" >&2; exit 2 ;; esac

FS="${FLASHSALE_BIN:-flashsale}"
LOG="${MATRIX_LOG_DIR:-results/matrix-$ENGINE-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$LOG"
POINT_NO=0

say() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG/matrix.log"; }

run_cmd() {
    if ((DRY)); then
        say "DRY-RUN: $*"
    else
        "$@"
    fi
}

dataset_of() { python3 -c 'import json,sys; print(json.load(sys.stdin)["database"])'; }

# load_dataset <config> -> in tên dataset
load_dataset() {
    local config="$1" name
    if ((DRY)); then
        echo "flashsale_00000000000000000000000000000000"
        return
    fi
    name="$("$FS" load "$ENGINE" --config "$config" | tee -a "$LOG/load.json" | dataset_of)"
    say "Đã nạp dataset $name từ $config"
    echo "$name"
}

# point <dataset> <label> <config> [tùy chọn run...]
point() {
    local dataset="$1" label="$2" config="$3"
    shift 3
    POINT_NO=$((POINT_NO + 1))
    local out="$LOG/point-$(printf '%02d' "$POINT_NO")-$label"
    mkdir -p "$out"
    say "Điểm $POINT_NO: $label ($config $*)"
    local iostat_pid=""
    if [[ -n "${FLASHSALE_IOSTAT_SSH:-}" ]] && ((!DRY)); then
        # Stream iostat/vmstat từ VM DBMS về file cục bộ; dừng khi điểm đo kết thúc.
        ssh -o BatchMode=yes "$FLASHSALE_IOSTAT_SSH" "iostat -x -d -t 1" >"$out/iostat.txt" 2>&1 &
        iostat_pid=$!
    fi
    local status=0
    run_cmd "$FS" run "$ENGINE" --config "$config" --dataset "$dataset" --reset-between "$@" \
        >"$out/run.json" 2>"$out/run.err" || status=$?
    [[ -n "$iostat_pid" ]] && { kill "$iostat_pid" 2>/dev/null || true; wait "$iostat_pid" 2>/dev/null || true; }
    if ((status)); then
        # Mã thoát 1 cũng gồm lượt INVALID; giữ log và dừng để người vận hành xem trước khi tiếp tục.
        say "LỖI hoặc INVALID ở điểm $POINT_NO ($label), mã $status. Xem $out/run.err và run.json"
        exit "$status"
    fi
}

say "Bắt đầu ma trận 2.1: engine=$ENGINE grid=$GRID dry=$DRY log=$LOG"

# --- Dataset chính (tồn 10^9), dùng chung cho baseline, cross-engine, payment-ytd, lưới θ/client ---
MAIN="$(load_dataset configs/baseline.toml)"

if [[ "$ENGINE" == mysql ]]; then
    point "$MAIN" baseline-mysql-default configs/baseline.toml
    point "$MAIN" baseline-single-warehouse configs/baseline-single-warehouse.toml
    point "$MAIN" baseline-1client configs/baseline-1client.toml
fi
point "$MAIN" baseline-cross configs/baseline-cross.toml
point "$MAIN" baseline-cross-1client configs/baseline-cross-1client.toml
point "$MAIN" payment-ytd configs/payment-ytd.toml

# Các mức θ ở 8 client (kho uniform), cộng mức cực đoan "mọi người mua đúng 1 món".
for theta in 0 0.3 0.5 0.7 0.9; do
    point "$MAIN" "theta-$theta" configs/performance.toml --theta "$theta"
done
point "$MAIN" theta-hot-item configs/performance.toml --hot-item

if [[ "$GRID" == full ]]; then
    for clients in 8 32 64 128 256; do
        for theta in 0 0.3 0.5 0.7 0.9; do
            point "$MAIN" "grid-theta-$theta-c$clients" configs/performance.toml --theta "$theta" --concurrency "$clients"
        done
        point "$MAIN" "grid-hot-c$clients" configs/performance.toml --hot-item --concurrency "$clients"
    done
else
    # Số client 32/64/128/256 ở θ=0 (8 client đã có ở trên). MySQL cần max_connections >= client + 2.
    for clients in 32 64 128 256; do
        point "$MAIN" "clients-$clients" configs/performance.toml --theta 0 --concurrency "$clients"
    done
fi

# --- Lượt kiểm luật: tồn đầu 1.000, dataset riêng ---
CORRECT="$(load_dataset configs/correctness.toml)"
point "$CORRECT" correctness configs/correctness.toml

# --- Lượt phụ tắt mã chống trùng: lược đồ không UNIQUE, dataset riêng; INVALID luật 3 là KẾT QUẢ DỰ KIẾN ---
IDEM="$(load_dataset configs/idempotency-off.toml)"
POINT_NO=$((POINT_NO + 1))
say "Điểm $POINT_NO: idempotency-off (INVALID luật 3 là kết quả dự kiến, không xếp hạng)"
mkdir -p "$LOG/point-$(printf '%02d' "$POINT_NO")-idempotency-off"
run_cmd "$FS" run "$ENGINE" --config configs/idempotency-off.toml --dataset "$IDEM" --reset-between \
    >"$LOG/point-$(printf '%02d' "$POINT_NO")-idempotency-off/run.json" 2>"$LOG/point-$(printf '%02d' "$POINT_NO")-idempotency-off/run.err" || true

say "Xong $POINT_NO điểm. Tổng hợp: $FS report --results-dir results --out $LOG/report"
((DRY)) || "$FS" report --results-dir results --out "$LOG/report" | tee -a "$LOG/matrix.log"
