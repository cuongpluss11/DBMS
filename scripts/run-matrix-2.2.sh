#!/usr/bin/env bash
# Chạy ma trận đo mục 2.2 (Tầng 1, docs/scope-2-weeks.md) cho MỘT hệ trên VM loadgen (chế độ remote).
# Dùng:  scripts/run-matrix-2.2.sh <mysql|mongo|tidb> [--tier t1|t2|t3|t4|c|all] [--dry-run]
#   t1: P1 ở θ ∈ {0; 0,5; 0,7; 0,9; "1 món"} × {8; 64; 256} client; P0 ở θ ∈ {0; 0,9; "1 món"} × {8; 64}.
#   t2: P1 so với P2 (N = 1, 3, 9, 27; có cấp mã theo lô B) ở θ=0,9 và "1 món", 64 client; đối chứng P2 không cấp
#       mã theo lô ở N=1 và N=9. (Điểm P1 không lô lấy từ t1 ở 64 client: chạy t1 trước hoặc cùng dataset.)
#   t3: P2 so với P3 ở 128 và 256 client, θ=0,9, TẢI VÒNG MỞ. Cần T3_RATES (yêu cầu/giây, cách nhau bằng dấu cách):
#       đặt SAU KHI xem t1/t2 (đề: T3 chỉ chạy khi hiệu năng thật sự sụp ở tải cao). Không đặt thì bỏ qua t3.
#   t4: đòn bẩy riêng từng hệ ở θ ∈ {0,9; "1 món"} × {32; 128} client: MySQL (legacy, NOWAIT, khóa theo thứ tự i_id,
#       P1 làm mốc), TiDB (legacy, khóa theo thứ tự, P1 lạc quan so với bi quan). MongoDB (thiết kế (a) so với (b), cùng P1).
#       MySQL stored procedure CHƯA có trong mã.
#   c : lượt kiểm luật có hết hàng thực (tồn 1.000, dataset riêng): P1, P2 N=9, P3 N=9 (+ P0, INVALID là kết quả).
# Mỗi điểm: reset dataset, rồi chạy 3 lần (30 giây warmup + 60 giây đo) với --reset-between. Không xóa dữ liệu,
# không dừng DBMS, không đụng tới hạ tầng AWS. Điểm P0 được phép INVALID (mất cập nhật là KẾT QUẢ cần quan sát).
# Biến môi trường: FLASHSALE_BIN, FLASHSALE_IOSTAT_SSH, MATRIX_START_POINT, MATRIX_END_POINT, MATRIX_LOG_DIR (như
#   run-matrix-2.1.sh); MATRIX_MAIN_DATASET (dùng lại dataset đã nạp); B (lô mã đơn, mặc định 50);
#   MATRIX_HOTSPOT_CONFIG, MATRIX_CORRECT_CONFIG (thay profile, dùng để chạy thử thu nhỏ);
#   HOT_ITEMS (số món nóng chia slot, mặc định 100); T3_RATES, T3_QUEUE (hàng đợi mỗi process, mặc định 64).
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

ENGINE="${1:?Thiếu engine: mysql|mongo|tidb}"
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
case "$ENGINE" in mysql | mongo | tidb) ;; *) echo "engine không hợp lệ: $ENGINE" >&2; exit 2 ;; esac
case "$TIER" in t1 | t2 | t3 | t4 | c | all) ;; *) echo "--tier phải là t1, t2, t3, t4, c hoặc all" >&2; exit 2 ;; esac

FS="${FLASHSALE_BIN:-flashsale}"
LOG="${MATRIX_LOG_DIR:-results/matrix22-$ENGINE-$(date -u +%Y%m%dT%H%M%SZ)}"
BATCH="${B:-50}"
HOT_ITEMS="${HOT_ITEMS:-100}"
mkdir -p "$LOG"
POINT_NO=0

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

# point <dataset> <label> <config> [tùy chọn run...]    (EXPECT_INVALID=1: INVALID là kết quả dự kiến, không dừng)
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
    run_cmd "$FS" run "$ENGINE" --config "$config" --dataset "$dataset" --reset-between "$@" \
        >"$out/run.json" 2>"$out/run.err" || status=$?
    [[ -n "$iostat_pid" ]] && { kill "$iostat_pid" 2>/dev/null || true; wait "$iostat_pid" 2>/dev/null || true; }
    if ((status)); then
        # run.json chỉ được in khi runner chạy xong: có nội dung nghĩa là lượt hoàn tất nhưng INVALID.
        if [[ "${EXPECT_INVALID:-0}" == 1 && -s "$out/run.json" ]]; then
            say "Điểm $POINT_NO ($label): INVALID như dự kiến (P0, mất cập nhật); tiếp tục"
        else
            say "LỖI hoặc INVALID ở điểm $POINT_NO ($label), mã $status. Xem $out/run.err và run.json"
            exit "$status"
        fi
    fi
}

say "Bắt đầu ma trận 2.2: engine=$ENGINE tier=$TIER dry=$DRY B=$BATCH hot_items=$HOT_ITEMS log=$LOG"
H="${MATRIX_HOTSPOT_CONFIG:-configs/hotspot.toml}"
MAIN="${MATRIX_MAIN_DATASET:-$(load_dataset "$H")}"

# θ hoặc "1 món": in tùy chọn tương ứng (mức cực đoan dùng θ=0 cho rõ nghĩa, như ma trận 2.1)
dist_args() { if [[ "$1" == hot ]]; then echo "--theta 0 --hot-item"; else echo "--theta $1 --no-hot-item"; fi; }

if [[ "$TIER" == t1 || "$TIER" == all ]]; then
    for clients in 8 64 256; do
        for d in 0 0.5 0.7 0.9 hot; do
            # shellcheck disable=SC2046
            point "$MAIN" "t1-p1-$d-c$clients" "$H" --variant p1 $(dist_args "$d") --concurrency "$clients"
        done
    done
    for clients in 8 64; do
        for d in 0 0.9 hot; do
            # shellcheck disable=SC2046
            EXPECT_INVALID=1 point "$MAIN" "t1-p0-$d-c$clients" "$H" --variant p0 $(dist_args "$d") --concurrency "$clients"
        done
    done
fi

if [[ "$TIER" == t2 || "$TIER" == all ]]; then
    for d in 0.9 hot; do
        for n in 1 3 9 27; do
            # shellcheck disable=SC2046
            point "$MAIN" "t2-p2-n$n-batch-$d" "$H" --variant p2 --slots "$n" --hot-items "$HOT_ITEMS" \
                --order-id-batch "$BATCH" $(dist_args "$d") --concurrency 64
        done
        for n in 1 9; do  # đối chứng: chỉ tách tác dụng của chia slot, không cấp mã theo lô
            # shellcheck disable=SC2046
            point "$MAIN" "t2-p2-n$n-nobatch-$d" "$H" --variant p2 --slots "$n" --hot-items "$HOT_ITEMS" \
                --order-id-batch 0 $(dist_args "$d") --concurrency 64
        done
    done
fi

if [[ "$TIER" == t3 || "$TIER" == all ]]; then
    if [[ -z "${T3_RATES:-}" ]]; then
        say "Bỏ qua t3: chưa đặt T3_RATES (đề: chỉ chạy T3 khi T1/T2 cho thấy hiệu năng sụp ở tải cao; xem t1/t2 rồi đặt)"
    else
        for clients in 128 256; do
            for rate in $T3_RATES; do
                for variant in p2 p3; do
                    point "$MAIN" "t3-$variant-c$clients-r$rate" "$H" --variant "$variant" --slots 9 \
                        --hot-items "$HOT_ITEMS" --order-id-batch "$BATCH" --theta 0.9 --no-hot-item \
                        --concurrency "$clients" --arrival-rate "$rate" --queue-size "${T3_QUEUE:-64}"
                done
            done
        done
    fi
fi

if [[ "$TIER" == t4 || "$TIER" == all ]]; then
    if [[ "$ENGINE" == mongo ]]; then
        for clients in 32 128; do
            for d in 0.9 hot; do
                # shellcheck disable=SC2046
                point "$MAIN" "t4-design-a-p1-$d-c$clients" "$H" --variant p1 $(dist_args "$d") --concurrency "$clients"
                point "$MAIN" "t4-design-b-p1-$d-c$clients" "$H" --variant p1 --mongo-design b $(dist_args "$d") --concurrency "$clients"
            done
        done
    else
        for clients in 32 128; do
            for d in 0.9 hot; do
                # shellcheck disable=SC2046
                if [[ "$ENGINE" == mysql ]]; then
                    point "$MAIN" "t4-legacy-$d-c$clients" "$H" --variant legacy $(dist_args "$d") --concurrency "$clients"
                    point "$MAIN" "t4-nowait-$d-c$clients" "$H" --variant legacy --nowait $(dist_args "$d") --concurrency "$clients"
                    point "$MAIN" "t4-lockorder-$d-c$clients" "$H" --variant legacy --lock-order $(dist_args "$d") --concurrency "$clients"
                    point "$MAIN" "t4-p1-$d-c$clients" "$H" --variant p1 $(dist_args "$d") --concurrency "$clients"
                else
                    point "$MAIN" "t4-legacy-$d-c$clients" "$H" --variant legacy $(dist_args "$d") --concurrency "$clients"
                    point "$MAIN" "t4-lockorder-$d-c$clients" "$H" --variant legacy --lock-order $(dist_args "$d") --concurrency "$clients"
                    point "$MAIN" "t4-p1-optimistic-$d-c$clients" "$H" --variant p1 --txn-mode optimistic $(dist_args "$d") --concurrency "$clients"
                    point "$MAIN" "t4-p1-pessimistic-$d-c$clients" "$H" --variant p1 --txn-mode pessimistic $(dist_args "$d") --concurrency "$clients"
                fi
            done
        done
    fi
fi

if [[ "$TIER" == c || "$TIER" == all ]]; then
    C="${MATRIX_CORRECT_CONFIG:-configs/correctness.toml}"
    CORRECT="${MATRIX_CORRECTNESS_DATASET:-$(load_dataset "$C")}"
    EXPECT_INVALID=1 point "$CORRECT" "c-p0" "$C" --variant p0
    point "$CORRECT" "c-p1" "$C" --variant p1
    point "$CORRECT" "c-p2-n9" "$C" --variant p2 --slots 9 --hot-items "$HOT_ITEMS" --order-id-batch "$BATCH"
    point "$CORRECT" "c-p3-n9" "$C" --variant p3 --slots 9 --hot-items "$HOT_ITEMS" --order-id-batch "$BATCH"
fi

say "Xong $POINT_NO điểm. Tổng hợp: $FS report --results-dir results --out $LOG/report"
((DRY)) || "$FS" report --results-dir results --out "$LOG/report" | tee -a "$LOG/matrix.log"
