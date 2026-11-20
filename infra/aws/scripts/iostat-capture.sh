#!/bin/bash
# Ghi iostat va vmstat moi giay trong luc do, de xac nhan nut that dia EBS (chay tren VM DBMS).
# Dung: iostat-capture.sh <thu-muc-ket-qua> <so-giay>   (vi du 100 giay cho 30 warmup + 60 do + du phong)
set -euo pipefail
OUT="${1:?thu muc ket qua}"
SECONDS_TOTAL="${2:?so giay}"
mkdir -p "$OUT"
HOST="$(hostname)"
iostat -x -d -t 1 "$SECONDS_TOTAL" > "$OUT/iostat-$HOST.txt" &
vmstat -t 1 "$SECONDS_TOTAL" > "$OUT/vmstat-$HOST.txt" &
wait
echo "Da ghi $OUT/iostat-$HOST.txt va vmstat-$HOST.txt"
