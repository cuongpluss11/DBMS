# Số liệu tranh chấp và kết quả P0 (mục 2.2, AWS)

Sinh bởi `scripts/contention_summary.py` từ `result.json`; trung vị 3 lần lặp. `n/a` = hệ không cung cấp metric đó (không đưa về 0). Lỗi theo mỗi 100 yêu cầu = `request_error_pct`; `lock_wait_ms` chỉ có ở MySQL.

## P0 (đọc rồi ghi, không khóa) so với bất biến

| Hệ | Lượt P0 | INVALID | Lỗi `write_conflict` mỗi lượt (min–max) | Deadlock (tổng) | Dòng lệch đối soát INV2 (tổng) |
| --- | --- | --- | --- | --- | --- |
| MySQL | 7 | 7 | 0–0 | 30 | 1335 |
| MongoDB | 21 | 0 | 3,075–78,699 | 0 | 0 |
| TiDB | 7 | 7 | 0–0 | 19 | 1038 |

INV1 (tồn không âm) đúng ở mọi lượt P0 vì tồn đầu rất lớn; lỗi nằm ở INV2 (mất cập nhật).

## P1 một kho: tranh chấp theo mức tập trung (64 client)

| Hệ | Cấu hình | TPS | p99 (ms) | Abort % | Retry % | Deadlock | `write_conflict` | Lock wait (ms) | Lock wait ÷ thời gian client |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MySQL | θ=0.0 | 1,416 | 500 | 0.0 | 0.0 | 0 | 0 | 2,800,429 | 73% |
| MySQL | θ=0.5 | 1,387 | 518 | 0.0 | 0.0 | 0 | 0 | 2,802,398 | 73% |
| MySQL | θ=0.7 | 1,392 | 512 | 0.0 | 0.0 | 0 | 0 | 2,811,136 | 73% |
| MySQL | θ=0.9 | 1,252 | 476 | 0.0 | 0.0 | 23 | 0 | 2,982,608 | 78% |
| MySQL | một món | 426 | 474 | 0.0 | 0.0 | 0 | 0 | 3,720,299 | 97% |
| MongoDB | θ=0.0 | 1,884 | 346 | 2.4 | 28.5 | 0 | 79,599 | n/a | n/a |
| MongoDB | θ=0.5 | 1,880 | 346 | 2.4 | 28.5 | 0 | 79,563 | n/a | n/a |
| MongoDB | θ=0.7 | 1,867 | 346 | 2.4 | 28.5 | 0 | 79,522 | n/a | n/a |
| MongoDB | θ=0.9 | 1,698 | 346 | 3.5 | 29.0 | 0 | 78,559 | n/a | n/a |
| MongoDB | một món | 673 | 338 | 15.8 | 40.4 | 0 | 75,207 | n/a | n/a |
| TiDB | θ=0.0 | 956 | 408 | 0.0 | 0.0 | 0 | 0 | n/a | n/a |
| TiDB | θ=0.5 | 929 | 435 | 0.0 | 0.0 | 0 | 0 | n/a | n/a |
| TiDB | θ=0.7 | 983 | 404 | 0.0 | 0.0 | 0 | 0 | n/a | n/a |
| TiDB | θ=0.9 | 807 | 398 | 0.0 | 0.0 | 22 | 0 | n/a | n/a |
| TiDB | một món | 255 | 605 | 0.0 | 0.0 | 0 | 0 | n/a | n/a |
