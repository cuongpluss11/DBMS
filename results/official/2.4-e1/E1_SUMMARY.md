# Tổng hợp thí nghiệm E1 – Đổi lược đồ gốc dưới tải & kẹt Metadata Lock

| Hệ DBMS | Kịch bản E1 | Lượt VALID | TPS nền (warmup) | TPS đo (median) | p99 toàn pha (ms) | Đỉnh p99 1s (ms) | Thời gian DDL (s) | Đóng băng lâu nhất (s) | DDL thành công / timeout |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| mongo | `create_index` | 3/3 | 1959.4 | **2125.52** | 171.8 | 422.87 | 8.8 | **0** | 3/3 (timeout: 0) |
| mongo | `create_index_long_txn` | 3/3 | 2036.37 | **706.11** | 140.69 | 358.98 | 66.77 | **0** | 3/3 (timeout: 0) |
| mysql | `add_column_copy` | 3/3 | 1147.83 | **903.35** | 562.23 | 22857.9 | 22.72 | **21** | 3/3 (timeout: 0) |
| mysql | `add_column_instant` | 6/6 | 1231.35 | **1420.21** | 523.87 | 713.65 | 0.05 | **0.0** | 6/6 (timeout: 0) |
| mysql | `add_index_inplace` | 3/3 | 1234.33 | **1084.6** | 537.63 | 3255.24 | 24.3 | **1** | 3/3 (timeout: 0) |
| mysql | `mdl_freeze` | 3/3 | 1412.73 | **502.07** | 350.78 | 58066.68 | 58.02 | **57** | 3/3 (timeout: 0) |
| mysql | `mdl_timeout_retry` | 3/3 | 1294.63 | **1276.75** | 473.69 | 3208.64 | 29.51 | **2** | 0/3 (timeout: 18) |
| tidb | `add_column_online` | 3/3 | 724.5 | **920.1** | 284.79 | 380.26 | 1.2 | **0** | 3/3 (timeout: 0) |
| tidb | `add_index_online` | 3/3 | 1046.6 | **848.12** | 339.45 | 732.63 | 41.89 | **0** | 3/3 (timeout: 0) |
| tidb | `mdl_long_txn` | 3/3 | 950.9 | **1042.22** | 250.88 | 422.65 | 59.27 | **0** | 3/3 (timeout: 0) |
