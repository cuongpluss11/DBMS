# Ánh xạ yêu cầu mục 2.1

| Yêu cầu | Mã và cấu hình | Bằng chứng |
| --- | --- | --- |
| 9 bảng, W=10, stock và đơn nạp sẵn | data/schema.py, data/loader.py, configs/baseline.toml | `test_nine_tables_and_initial_order_lines`, `test_transaction_contract_and_validator`, manifest baseline |
| TiDB 1 PD, 3 TiKV, replica=1, history split, cache và Region | docker/, adapters/sql.py | Kiểm store và PD, manifest lưu Region và DDL |
| MongoDB mode A với replica set một nút | docker/compose.mongo.yml, adapters/mongo.py | Healthcheck primary, `test_transaction_contract_and_validator` |
| New-Order, Payment 1:1, kho và Zipf | transactions/core.py, workload/generator.py | `test_mix_reproducibility_and_warehouse`, `test_zipf_uniformity_and_seed`, `test_transaction_contract_and_validator` |
| Retry và chống trùng | workload/retry.py, adapters/ | `test_hot_item_and_retry_limit`, `test_commit_ambiguity_reconciles_before_replay`, `test_unreachable_reconciliation_prevents_resubmission`, integration replay |
| Một DBMS, ngân sách bằng nhau, EXPLAIN, warmup và đo | infra.py, benchmark/runner.py, configs/ | Healthcheck, `test_smoke_exports`, manifest baseline |
| Hai mức tồn, reset và ba luật | data/loader.py, validation/checks.py | `test_validator_distinguishes_two_directions_and_duplicates`, `test_transaction_contract_and_validator`, `test_replay_without_persisted_idempotency_is_rejected` |
| CSV/JSON, phiên bản, tài nguyên và CPU | benchmark/metrics.py, infra.py | `test_metrics_and_export`, `test_smoke_exports`, manifest baseline |
| Hướng dẫn và thao tác có phạm vi | README.md, scripts/, docs/experiment-2.1.md | Kiểm Bash, Compose và smoke tuần tự |
| Lượt phụ tắt idempotency, baseline một kho và 1 client, Payment bật YTD | configs/idempotency-off.toml, baseline-single-warehouse.toml, baseline-1client.toml, payment-ytd.toml, workload/retry.py, data/schema.py | `test_idempotency_off_profile_resubmits_without_reconciliation`, `test_idempotency_off_schema_and_fingerprint`, `test_every_profile_loads_and_matches_the_document`, integration `test_idempotency_off_replay_creates_duplicate_order` (NOT TESTED trên DBMS thật) |
| Nghiệm thu thực tế trên VM | docs/acceptance-2.1.md, results/official/2.1/ | 30 lượt trên MySQL, MongoDB và TiDB; 29 VALID, 1 INVALID dự kiến (idempotency-off) |
