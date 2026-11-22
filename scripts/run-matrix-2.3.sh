#!/usr/bin/env bash
# Chạy ma trận đo mục 2.3 (Tầng 1, docs/scope-2-weeks.md) trên VM loadgen (chế độ remote, xem infra/aws/README.md).
# Dùng:  scripts/run-matrix-2.3.sh <tidb|mysql> [--tier a|b|c|d|e|all] [--dry-run]
# Chạy MỘT lần cho mỗi cụm: stack `tidb1` (1 TiKV) rồi `tidb3` (3 TiKV) với cùng cấu hình; hệ số tăng tốc tính ở
# `flashsale report` (cặp theo từng nhóm). MySQL-chỉnh là mốc mở rộng dọc: chạy hai cỡ máy (xem bên dưới).
#   a: tải đều θ=0, kho đều.                                        (TiDB, MySQL)
#   b: dồn θ=0,9, một kho, cấp mã đơn theo lô.                      (TiDB, MySQL)
#   c: b + chia món nóng thành N = 3, 9, 27 slot (P2).              (TiDB, MySQL)
#   d: khóa orders tự tăng so với AUTO_RANDOM (dataset riêng).      (chỉ TiDB)
#   e: nhóm E.a: đơn 1 / 2 / 3–4 kho × vị trí leader {PD, tách, chung theo nhóm}.  (chỉ TiDB, cụm 3 TiKV)
# Mỗi điểm 64 client, reset dataset rồi 3 lần × (30 giây warmup + 60 giây đo). Không xóa dữ liệu, không dừng DBMS,
# không đụng tới hạ tầng AWS. Ở TiDB mỗi lượt tự tách Region/đặt leader, tạm dừng bộ cân bằng của PD trong lúc đo và
# khôi phục sau đó; nếu PD không làm đúng thì điểm bị INVALID (placement_failed) và script dừng.
#
# MySQL-chỉnh hai cỡ máy (mốc mở rộng dọc, đề 2.3): cùng tổng vCPU/RAM với cụm 1 TiKV và cụm 3 TiKV (PD + TiDB + TiKV,
# không tính máy tải). TiDB server dùng c6i.4xlarge (16 vCPU/32 GiB, quyết định 2026-11-21 vì 4 vCPU bị nghẽn ở tầng SQL),
# PD c6i.large (2/4 GiB), TiKV m6i.large (2/8 GiB): cụm 1 TiKV = 20 vCPU/44 GiB, cụm 3 TiKV = 24 vCPU/60 GiB. Không có c6i
# đủ RAM nên MySQL dùng single_node_instance_type = "m6i.8xlarge" (32 vCPU/128 GiB), giới hạn bằng cpuset và mem_limit:
# single_node_cpus/mem_gb = 20/44 rồi 24/60 trong terraform.tfvars, và trên VM loadgen:
#   FLASHSALE_REMOTE_BUDGET_CPUS=20 FLASHSALE_REMOTE_BUDGET_MEMORY_BYTES=47244640256    (cỡ nhỏ)
#   FLASHSALE_REMOTE_BUDGET_CPUS=24 FLASHSALE_REMOTE_BUDGET_MEMORY_BYTES=64424509440    (cỡ lớn)
# kèm FLASHSALE_MYSQL_BUFFER_POOL_BYTES tương ứng RAM và FLASHSALE_RUN_NOTE=mysql-20vcpu / mysql-24vcpu.
# Biến môi trường: FLASHSALE_BIN, FLASHSALE_IOSTAT_SSH, MATRIX_START_POINT, MATRIX_END_POINT, MATRIX_LOG_DIR,
#   MATRIX_MAIN_DATASET, B (lô mã, mặc định 50), HOT_ITEMS (mặc định 100), SCALING_CONFIG (mặc định
#   configs/scaling.toml), SCALING_CONFIG_AUTOINC / SCALING_CONFIG_AUTORANDOM (nhóm D).
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

ENGINE="${1:?Thiếu engine: tidb|mysql}"
shift || true
TIER=all
DRY=0
while (($#)); do
    case "$1" in
        --tier) TIER="${2:?}"; shift 2 ;;
        --dry-run) DRY=1; shift ;;
        *) echo "Tùy chọn lạ: $1" >&2; exit 2 ;;
    esac
done
case "$ENGINE" in tidb | mysql) ;; *) echo "mục 2.3 chỉ chạy TiDB và MySQL (mốc): $ENGINE" >&2; exit 2 ;; esac
case "$TIER" in a | b | c | d | e | all) ;; *) echo "--tier phải là a, b, c, d, e hoặc all" >&2; exit 2 ;; esac

FS="${FLASHSALE_BIN:-flashsale}"
LOG="${MATRIX_LOG_DIR:-results/matrix23-$ENGINE-$(date -u +%Y%m%dT%H%M%SZ)}"
BATCH="${B:-50}"
HOT_ITEMS="${HOT_ITEMS:-100}"
CFG="${SCALING_CONFIG:-configs/scaling.toml}"
mkdir -p "$LOG"
POINT_NO=0
# MySQL không có Region/leader: mọi điểm chạy với --placement none.
if [[ "$ENGINE" == mysql ]]; then PLACE=(--placement none); else PLACE=(); fi

say() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG/matrix.log" >&2; }
run_cmd() { if ((DRY)); then say "DRY-RUN: $*"; else "$@"; fi; }
dataset_of() { python3 -c 'import json,sys; print(json.load(sys.stdin)["database"])'; }

load_dataset() {
    local config="$1" name
    if ((DRY)); then echo "flashsale_00000000000000000000000000000000"; return; fi
    name="$("$FS" load "$ENGINE" --config "$config" | tee -a "$LOG/load.json" | dataset_of)"
    say "Đã nạp dataset $name từ $config"
    echo "$name"
}

# point <dataset> <label> <config> [tùy chọn run...]
point() {
    local dataset="$1" label="$2" config="$3"
    shift 3
    POINT_NO=$((POINT_NO + 1))
    if ((POINT_NO < ${MATRIX_START_POINT:-1})); then say "Bỏ qua điểm $POINT_NO ($label): MATRIX_START_POINT"; return; fi
    if ((POINT_NO > ${MATRIX_END_POINT:-1000})); then say "Bỏ qua điểm $POINT_NO ($label): MATRIX_END_POINT"; return; fi
    local out="$LOG/point-$(printf '%02d' "$POINT_NO")-$label"
    mkdir -p "$out"
    say "Điểm $POINT_NO: $label ($config $*)"
    local reset_status=0
    run_cmd "$FS" reset "$ENGINE" --config "$config" --dataset "$dataset" --confirm "$dataset" \
        >"$out/reset.json" 2>"$out/reset.err" || reset_status=$?
    if ((reset_status)); then say "LỖI reset ở điểm $POINT_NO ($label), mã $reset_status. Xem $out/reset.err"; exit "$reset_status"; fi
    local iostat_pid=""
    if [[ -n "${FLASHSALE_IOSTAT_SSH:-}" ]] && ((!DRY)); then
        ssh -o BatchMode=yes "$FLASHSALE_IOSTAT_SSH" "iostat -x -d -t 1" >"$out/iostat.txt" 2>&1 &
        iostat_pid=$!
    fi
    local status=0
    run_cmd "$FS" run "$ENGINE" --config "$config" --dataset "$dataset" --reset-between "${PLACE[@]}" "$@" \
        >"$out/run.json" 2>"$out/run.err" || status=$?
    [[ -n "$iostat_pid" ]] && { kill "$iostat_pid" 2>/dev/null || true; wait "$iostat_pid" 2>/dev/null || true; }
    if ((status)); then
        say "LỖI hoặc INVALID ở điểm $POINT_NO ($label), mã $status. Xem $out/run.err và run.json"
        exit "$status"
    fi
}

say "Bắt đầu ma trận 2.3: engine=$ENGINE tier=$TIER dry=$DRY B=$BATCH hot_items=$HOT_ITEMS log=$LOG"
MAIN="${MATRIX_MAIN_DATASET:-$(load_dataset "$CFG")}"
UNIFORM=(--theta 0 --no-hot-item --warehouse-mode uniform)
HOT=(--theta 0.9 --no-hot-item --warehouse-mode single-warehouse --order-id-batch "$BATCH")

if [[ "$TIER" == a || "$TIER" == all ]]; then
    point "$MAIN" "a-uniform" "$CFG" --variant p1 "${UNIFORM[@]}"
fi
if [[ "$TIER" == b || "$TIER" == all ]]; then
    point "$MAIN" "b-hot" "$CFG" --variant p1 "${HOT[@]}"
fi
if [[ "$TIER" == c || "$TIER" == all ]]; then
    for n in 3 9 27; do
        point "$MAIN" "c-slots-n$n" "$CFG" --variant p2 --slots "$n" --hot-items "$HOT_ITEMS" "${HOT[@]}"
    done
fi
if [[ "$TIER" == d || "$TIER" == all ]]; then
    if [[ "$ENGINE" != tidb ]]; then
        say "Bỏ qua d: AUTO_RANDOM chỉ có trên TiDB (MySQL không áp dụng)"
    else
        INC="${SCALING_CONFIG_AUTOINC:-configs/scaling-autoinc.toml}"
        RND="${SCALING_CONFIG_AUTORANDOM:-configs/scaling-autorandom.toml}"
        D1="$(load_dataset "$INC")"
        point "$D1" "d-autoinc" "$INC" --variant p1 "${UNIFORM[@]}"
        D2="$(load_dataset "$RND")"
        point "$D2" "d-auto-random" "$RND" --variant p1 "${UNIFORM[@]}"
    fi
fi
if [[ "$TIER" == e || "$TIER" == all ]]; then
    if [[ "$ENGINE" != tidb ]]; then
        say "Bỏ qua e: chỉ TiDB (cụm 3 TiKV)"
    else
        for layout in none spread group; do   # none = PD tự quyết; spread = "tách"; group = "chung theo nhóm"
            for span in "1 1" "2 2" "3 4"; do
                read -r lo hi <<<"$span"
                point "$MAIN" "e-$layout-k$lo-$hi" "$CFG" --variant p1 "${UNIFORM[@]}" --placement "$layout" \
                    --placement-scope all --warehouse-groups 3 --order-warehouses-min "$lo" --order-warehouses-max "$hi"
            done
        done
    fi
fi

say "Xong $POINT_NO điểm. Tổng hợp: $FS report --results-dir results --out $LOG/report"
((DRY)) || "$FS" report --results-dir results --out "$LOG/report" | tee -a "$LOG/matrix.log"
