# Tổng hợp thí nghiệm E1 – Đổi lược đồ gốc dưới tải & kẹt Metadata Lock

| Hệ DBMS | Kịch bản E1 | Lượt VALID | TPS nền (warmup) | TPS đo (median) | p99 toàn pha (ms) | Đỉnh p99 1s (ms) | Thời gian DDL (s) | Đóng băng lâu nhất (s) | DDL thành công / timeout |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| mongo | `create_index` | 3/3 | 1959.4 | **2125.52** | 171.8 | 422.87 | 8.8 | **0** | 3/3 (timeout: 0) |
| mongo | `create_index_long_txn` | 3/3 | 2036.37 | **706.11** | 140.69 | 358.98 | 66.77 | **0** | 3/3 (timeout: 0) |
