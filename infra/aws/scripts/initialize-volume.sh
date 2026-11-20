#!/bin/bash
# Doc het o du lieu khoi phuc tu snapshot EBS truoc khi do (lan truy cap dau cua block chua tai ve rat cham,
# neu khong lam buoc nay thi lan do dau bi lech). Chay tren VM co o du lieu, mat khoang vai phut den vai chuc phut.
set -euo pipefail
DEV="$(cat /etc/flashsale-data-device)"
echo "Doc toan bo $DEV de khoi tao volume tu snapshot..."
sudo fio --filename="$DEV" --rw=read --bs=1M --iodepth=32 --ioengine=libaio --direct=1 \
  --name=volume-initialize --output-format=terse > /dev/null
echo "Xong."
