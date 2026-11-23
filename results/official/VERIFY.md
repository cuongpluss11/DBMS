# Kiểm tra toàn vẹn results/official

| Thư mục | Lượt | VALID | INVALID (không phải P0) | INVALID P0 | Phiên bản DBMS | Môi trường | Ghi chú chạy | CPU máy tải tối đa % | Vấn đề |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.2-aws\mongo | 135 | 135 | 0 | 0 | mongo 8.0.20 | remote | m22-mongo | 1246 | không |
| 2.2-aws\mongo-t1-c256-postfix | 15 | 15 | 0 | 0 | mongo 8.0.20 | remote | m22-mongo-t1c256-postfix | 1068 | không |
| 2.2-aws\mongo-t3 | 48 | 48 | 0 | 0 | mongo 8.0.20 | remote | m22-mongo-t3 | 625 | không |
| 2.2-aws\mongo-t3-p2-postfix | 12 | 12 | 0 | 0 | mongo 8.0.20 | remote | m22-mongo-t3-postfix | 626 | không |
| 2.2-aws\mysql | 157 | 150 | 0 | 7 | mysql 8.4.8 | remote | m22-mysql | 386 | không |
| 2.2-aws\mysql-t3 | 48 | 48 | 0 | 0 | mysql 8.4.8 | remote | m22-mysql-t3 | 363 | không |
| 2.2-aws\tidb3 | 145 | 138 | 0 | 7 | tidb 8.0.11-TiDB-v8.5.7 | remote | m22-tidb3 | 246 | không |
| 2.3-aws\mysql | 30 | 30 | 0 | 0 | mysql 8.4.8 | remote | mysql-20vcpu, mysql-24vcpu | 439 | không |
| 2.3-aws\tidb1 | 21 | 21 | 0 | 0 | tidb 8.0.11-TiDB-v8.5.7 | remote | m23-tidb1 | 113 | không |
| 2.3-aws\tidb3 | 48 | 48 | 0 | 0 | tidb 8.0.11-TiDB-v8.5.7 | remote | m23-tidb3 | 257 | không |
| 2.3-aws\tidb3-R | 30 | 30 | 0 | 0 | tidb 8.0.11-TiDB-v8.5.7 | remote | tidb3-rf1, tidb3-rf3 | 247 | không |
| 2.3-aws\tidb3-R2 | 45 | 45 | 0 | 0 | tidb 8.0.11-TiDB-v8.5.7 | remote | tidb3-ph1-rf3, tidb3-ph2-rf1, tidb3-ph3-rf3 | 233 | không |
