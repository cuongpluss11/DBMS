---
name: dbms-benchmark
description: Triển khai, kiểm thử và tái hiện benchmark Flash-sale trên MySQL, MongoDB và TiDB trong repo này. Dùng khi thay đổi lược đồ, workload, giao dịch, đo hiệu năng hoặc validator của bài tập DBMS.
---

# Benchmark Flash-sale

- Đọc AGENTS.md, docs/requirements-2.1.md và docs/assumptions.md để xác định phạm vi bài được yêu cầu. Dùng mục tương ứng của PDF chính làm đặc tả.
- Dùng một luồng yêu cầu logic cho ba adapter. Khi sửa New-Order hoặc Payment, thử lại cùng request ID trên DB thật và kiểm tra rollback đầy đủ sau khi món thứ hai hết hàng.
- Dùng database UUID do CLI tạo. Chạy từng dự án Compose lần lượt. Dừng bằng lệnh stop và giữ volume. Các lệnh reset và drop cần đúng dataset mà người dùng đã đồng ý thao tác.
- Kiểm tra EXPLAIN trước đo và lưu bằng chứng TiDB Region. Đối soát order_line của cả warmup và measurement từ đơn đã commit. Giữ TPS, percentile và thống kê lỗi riêng theo cửa sổ thời gian.
- Tái hiện bằng README.md và đối chiếu trường kết quả theo docs/experiment-2.1.md. Ghi phiên bản và phạm vi chạy thực tế, bao gồm trường null và các mục NOT TESTED.
