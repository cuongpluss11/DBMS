# Nghiệm thu mục 2.1

Ngày chạy: 2026-11-19. Môi trường: AWS EC2 `c6i.4xlarge` (16 vCPU, 32 GiB), Ubuntu 24.04 LTS x86_64, Docker 29.10.0, Compose 5.8.0, Python 3.12.3, Git commit `38dda58` (`main`, không có thay đổi chưa commit). Mỗi hệ chạy riêng một thời điểm với ngân sách container chung **8 CPU / 16 GiB** ([assumptions.md](assumptions.md)). Dữ liệu thô nằm ở [results/official/2.1/](../results/official/2.1/) (xem `INDEX.csv`).

## Kết luận: DONE theo tiêu chí AGENTS.md mục 14

| Tiêu chí | Trạng thái | Bằng chứng |
| --- | --- | --- |
| Xác nhận phiên bản thực tế cả ba hệ | PASS | MySQL 8.4.8, MongoDB 8.0.20, TiDB v8.5.7 (3 TiKV cùng 8.5.7, `max_replicas=1`) trong manifest |
| Nạp và kiểm đếm 9 bảng/collection W=10 | PASS | Cả ba hệ: warehouse 10, item 100.000, district 100, stock 1.000.000, customer 300.000, history 300.000, orders 300.000, new_order 90.000, order_line 2.998.678 (khớp nhau) |
| New-Order và Payment đúng trên các adapter | PASS | Integration test 4/4 trên mỗi hệ; các lượt đo VALID |
| Zipf/seed tái lập, uniform và single-warehouse | PASS | Unit test; trên DB thật θ=0,5: rank 1 quan sát 0,14–0,19% so với 0,1585% lý thuyết, top 100 quan sát 2,8–2,9% so với 2,95% |
| Baseline MySQL theo thông số 2.1 | PASS | 3 điểm x 3 lần, tất cả VALID (bảng dưới) |
| Xuất CSV/JSON và manifest phiên bản/tài nguyên | PASS | `result.csv`, `result.json`, `manifest.json` mỗi lượt |
| Tự kiểm ba luật sau mỗi lượt | PASS | 30 lượt: 29 VALID; 1 INVALID là lượt idempotency-off ở timeout 0,02 s, vi phạm luật 3 theo đúng dự kiến |
| Test trên DBMS thật PASS | PASS | `pytest -m integration`: 4 passed trên mỗi hệ (MySQL, MongoDB, TiDB); smoke VALID cả ba |

## Kết quả

Tất cả dùng 8 client trừ khi ghi khác, 3 lần lặp, 30 giây warmup cộng 60 giây đo; số là trung vị (khoảng min–max của TPS). p50/p95/p99 tính trên request thành công, gồm retry và backoff. Hủy không gồm hết hàng.

### Baseline MySQL (dữ liệu tồn 10^9, θ=0)
| Điểm đo | TPS | p50 | p95 | p99 | Hủy |
| --- | --- | --- | --- | --- | --- |
| Kho uniform (**baseline**) | 261,3 (260,6–267,4) | 18,2 ms | 102 ms | 157 ms | 0% |
| Một kho | 399,4 (399,0–434,3) | 12,7 ms | 48 ms | 96 ms | 0% |
| 1 client, uniform | 163,4 (161,5–170,8) | 5,6 ms | 11 ms | 14 ms | 0% |
| Payment bật `w_ytd`/`d_ytd` (lượt riêng) | 256,4 (254,7–265,8) | 18,7 ms | 105 ms | 160 ms | 0% |

### Lượt kiểm luật (tồn đầu 1.000, kho 1, một món hot)
| Hệ | TPS | p50 | p99 | Hết hàng | Retry |
| --- | --- | --- | --- | --- | --- |
| MySQL 8.4.8 | 420,4 | 9,5 ms | 15,1 ms | 50% request | 0% |
| MongoDB 8.0.20 | 390,4 | 8,0 ms | 12,6 ms | 50% | 5,4% (write conflict) |
| TiDB v8.5.7 | 261,8 (247,4–293,4) | 7,4 ms | 17,3 ms (lượt 1: 49 ms) | 50% | 0% |

Cả ba hệ giữ ba luật qua mỗi lần lặp có 15.000–25.000 request hết hàng. Các số này chỉ so được trong cùng một workload (mọi request dồn vào một dòng tồn kho), không dùng để xếp hạng hệ.

### Lượt đo tốc độ (tồn 10^9, θ=0,5, uniform)
| Hệ | TPS | p50 | p95 | p99 | Retry |
| --- | --- | --- | --- | --- | --- |
| MongoDB | 392,7 (385,2–403,1) | 14,7 ms | 41 ms | 79 ms | 2,1% (write conflict) |
| TiDB | 307,1 (289,0–310,0) | 20,2 ms | 59 ms | 93 ms | 0% |

MySQL chưa chạy θ=0,5; baseline của đề dùng θ=0.

### Lượt phụ tắt idempotency (MySQL, 1 lần lặp mỗi mức, 64 client, một món hot)
| `client_timeout_seconds` | Kết quả | Ghi chú |
| --- | --- | --- |
| 0,2 s | VALID | Chưa thấy đơn trùng |
| 0,05 s | VALID | Chưa thấy đơn trùng |
| **0,02 s** | **INVALID luật 3** | 1 đơn ghi hai lần; 2 đơn đã commit nhưng client không ghi nhận; ~34% request hủy |

## Quan sát cần lưu ý (chưa đủ chứng cứ để kết luận)
- **Kiểu một kho nhanh hơn uniform** (399 so với 261 TPS) dù thời gian chờ khóa lớn hơn khoảng 10 lần (65 giây so với 6 giây). Giả thuyết: dữ liệu W=10 lớn hơn buffer pool mặc định 128 MiB nên uniform bị trượt bộ nhớ đệm. Chưa đo I/O đĩa để xác nhận.
- CPU MySQL chỉ dùng 42–64% của một lõi trên hạn mức 8: tốc độ bị chặn bởi thứ khác (nghi là fsync đĩa EBS gp3 ở mỗi commit hoặc số client thấp), nên số TPS phụ thuộc vào loại đĩa.
- Payment bật `w_ytd`/`d_ytd` làm thời gian chờ khóa tăng khoảng 6 lần (6 giây lên 36 giây) nhưng TPS giảm chỉ khoảng 2% ở 8 client uniform.
- TiDB: `stock` nằm trong 2 Region, `history` có 16 Region (đúng `SHARD_ROW_ID_BITS=4`, `PRE_SPLIT_REGIONS=4`). Leader của Region `stock` đổi giữa các lượt (PD đang cân bằng); cần ghim bộ cân bằng ở 2.3.
- CPU TiDB server khoảng 140–170% của hạn mức 3 CPU, không vượt ngưỡng cảnh báo 80%.

## Khác biệt so với tài liệu
Chi tiết ở [assumptions.md](assumptions.md). Tóm tắt: loader Python thay go-tpc; đối soát bằng `run_id` thay `o_id > 3000`; không có FOREIGN KEY; ngân sách chung 8 CPU / 16 GiB (không phải 4 / 6); block cache TiKV 1 GiB; tách `out_of_stock` khỏi tỉ lệ hủy; lượt idempotency-off dùng timeout 0,02 s để gây commit mơ hồ.

## NOT TESTED
- MySQL ở θ=0,5, các θ khác (0,3; 0,7; 0,9) và mức "mọi người mua một món" trên DB thật (Zipf chỉ kiểm bằng unit test và θ=0,5 trên MongoDB/TiDB).
- 8, 32, 64, 128, 256 client: chỉ chạy 1, 8 và 64 client (lượt idempotency-off); 256 client cần tăng `FLASHSALE_MYSQL_MAX_CONNECTIONS` lớn hơn 151.
- Baseline uniform trên MongoDB và TiDB (đề chỉ yêu cầu baseline MySQL).
- Lượt idempotency-off trên MongoDB và TiDB; chỉ một lần lặp mỗi mức timeout trên MySQL.
- Lệnh `flashsale validate` chạy lại đối soát trên run đã lưu.
- Pin leader/Region, `SPLIT TABLE`, replica 3 của TiDB (thuộc 2.3).

## Tái hiện
Xem [README](../README.md) và [trien-khai-2.1.md](trien-khai-2.1.md). Ví dụ baseline MySQL:

```bash
flashsale start mysql
DATASET=$(flashsale load mysql --config configs/baseline.toml | python -c 'import json,sys; print(json.load(sys.stdin)["database"])')
flashsale run mysql --config configs/baseline.toml --dataset "$DATASET" --reset-between
```
