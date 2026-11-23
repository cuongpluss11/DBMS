# Tổng hợp thí nghiệm E1 – Đổi lược đồ gốc dưới tải & kẹt Metadata Lock

| Hệ DBMS | Kịch bản E1 | Lượt VALID | TPS nền (warmup) | TPS đo (median) | p99 toàn pha (ms) | Đỉnh p99 1s (ms) | Thời gian DDL (s) | Đóng băng lâu nhất (s) | DDL thành công / timeout |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| mongo | `create_index` | 3/3 | 1959.4 | **2125.52** | 171.8 | 422.87 | 8.8 | **0** | 3/3 (timeout: 0) |
| mongo | `create_index_long_txn` | 3/3 | 2036.37 | **706.11** | 140.69 | 358.98 | 66.77 | **0** | 3/3 (timeout: 0) |
| mysql | `add_column_copy` | 3/3 | 1147.83 | **903.35** | 562.23 | 22857.9 | 22.72 | **21** | 3/3 (timeout: 0) |
| mysql | `add_column_instant` | 3/3 | 1210.97 | **1415.1** | 527.29 | 714.62 | 0.28 | **0** | 3/3 (timeout: 0) |
| mysql | `add_index_inplace` | 3/3 | 1234.33 | **1084.6** | 537.63 | 3255.24 | 24.3 | **1** | 3/3 (timeout: 0) |
| mysql | `mdl_freeze` | 3/3 | 1412.73 | **502.07** | 350.78 | 58066.68 | 58.02 | **57** | 3/3 (timeout: 0) |
| mysql | `mdl_timeout_retry` | 3/3 | 1294.63 | **1276.75** | 473.69 | 3208.64 | 29.51 | **2** | 0/3 (timeout: 18) |
