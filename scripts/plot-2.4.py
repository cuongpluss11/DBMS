"""Sinh bộ biểu đồ mục 2.4 (Biểu đồ 6 phần E1, Biểu đồ 6 phần E2 và Biểu đồ 6b phần E3)
từ dữ liệu thực đo trong `results/official/2.4-{baseline,eager,batch,lazy,e1}/`.

Cách chạy:
    python scripts/plot-2.4.py
Đầu ra:
    docs/figures/2.4/fig6_e1_mdl_freeze.png
    docs/figures/2.4/fig6_e2_strategies.png
    docs/figures/2.4/fig6b_e3_q_sweep.png
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL = ROOT / "results" / "official"
OUT_DIR = ROOT / "docs" / "figures" / "2.4"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 150,
})


def _to_float(v):
    if v in ("", "None", "null", None):
        return None
    return float(v)


def load_runs(folder: str) -> list[tuple[Path, dict]]:
    root = OFFICIAL / folder
    out = []
    if not root.is_dir():
        return out
    for rj in sorted(root.glob("*/result.json")):
        d = json.loads(rj.read_text(encoding="utf-8"))
        if (d.get("validation") or {}).get("status") == "VALID":
            out.append((rj.parent, d))
    return out


def pick_median_run(runs: list[tuple[Path, dict]]) -> tuple[Path, dict]:
    ordered = sorted(runs, key=lambda x: x[1]["measurement"]["tps"])
    return ordered[len(ordered) // 2]


def read_series(d: dict) -> tuple[list[int], list[float], list[float | None]]:
    tpss = [float(v) for v in (d.get("tps_series") or {}).get("measurement", [])]
    raw_p99 = (d.get("p99_series") or {}).get("measurement", [])
    p99s = [_to_float(v) for v in raw_p99] if raw_p99 else [None] * len(tpss)
    secs = list(range(len(tpss)))
    return secs, tpss, p99s


def plot_fig6_e1() -> None:
    """Biểu đồ 6 (phần E1): Tác động DDL gốc & kẹt Metadata Lock theo từng giây trên 3 hệ."""
    e1_runs = load_runs("2.4-e1")

    def get_med(engine: str, scenario: str):
        matched = [(p, d) for p, d in e1_runs if d["engine"] == engine and d["scenario"] == scenario]
        return pick_median_run(matched) if matched else None

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharey=False)
    fig.suptitle(
        "Biểu đồ 6 (E1): TPS theo từng giây khi chạy DDL dưới tải & có giao dịch đọc order_line giữ mở 60s\n"
        "(W=10, ~3 triệu dòng order_line, 64 client, θ=0,5, q=25%, lượt trung vị trên 3 lần chạy)",
        fontsize=12, fontweight="bold", y=1.02,
    )

    # Panel 1: MySQL 8.4.8
    ax = axes[0]
    mysql_specs = [
        ("add_column_instant", "ADD COLUMN INSTANT (0,05s, 0s đóng băng)", "#2ca02c", "-"),
        ("add_column_copy", "ADD COLUMN COPY (22,7s, đóng băng 21s)", "#ff7f0e", "--"),
        ("mdl_freeze", "MDL Freeze — không timeout (đóng băng 57s!)", "#d62728", "-"),
        ("mdl_timeout_retry", "MDL + lock_wait_timeout=3s (đóng băng 2s)", "#1f77b4", "-."),
    ]
    for scen, label, color, ls in mysql_specs:
        item = get_med("mysql", scen)
        if not item:
            continue
        secs, tpss, _ = read_series(item[1])
        ax.plot(secs, tpss, label=label, color=color, linestyle=ls, linewidth=2.0)
    ax.axvline(5, color="black", linestyle=":", linewidth=1.2, alpha=0.7, label="Bắt đầu DDL (t=5s)")
    ax.set_title("MySQL 8.4.8 (InnoDB — Metadata Lock)")
    ax.set_xlabel("Thời gian pha đo (giây)")
    ax.set_ylabel("Thông lượng (TPS)")
    ax.set_ylim(bottom=-80)
    ax.legend(loc="lower right", fontsize=8)

    # Panel 2: MongoDB 8.0.20
    ax = axes[1]
    mongo_specs = [
        ("create_index", "createIndex thường (8,8s, 0s đóng băng)", "#2ca02c", "-"),
        ("create_index_long_txn", "createIndex + đọc giữ 60s (66,8s, TPS -67%)", "#d62728", "-"),
    ]
    for scen, label, color, ls in mongo_specs:
        item = get_med("mongo", scen)
        if not item:
            continue
        secs, tpss, _ = read_series(item[1])
        ax.plot(secs, tpss, label=label, color=color, linestyle=ls, linewidth=2.0)
    ax.axvline(5, color="black", linestyle=":", linewidth=1.2, alpha=0.7, label="Bắt đầu createIndex (t=5s)")
    ax.set_title("MongoDB 8.0.20 (WiredTiger — createIndex)")
    ax.set_xlabel("Thời gian pha đo (giây)")
    ax.set_ylabel("Thông lượng (TPS)")
    ax.set_ylim(bottom=-80)
    ax.legend(loc="lower right", fontsize=8)

    # Panel 3: TiDB 8.5.7
    ax = axes[2]
    tidb_specs = [
        ("add_column_online", "ADD COLUMN Online DDL (1,2s, 0s đóng băng)", "#2ca02c", "-"),
        ("add_index_online", "ADD INDEX Online DDL (41,9s, 0s đóng băng)", "#ff7f0e", "--"),
        ("mdl_long_txn", "ADD COLUMN + đọc giữ 60s (59,3s, 0s đóng băng!)", "#1f77b4", "-"),
    ]
    for scen, label, color, ls in tidb_specs:
        item = get_med("tidb", scen)
        if not item:
            continue
        secs, tpss, _ = read_series(item[1])
        ax.plot(secs, tpss, label=label, color=color, linestyle=ls, linewidth=2.0)
    ax.axvline(5, color="black", linestyle=":", linewidth=1.2, alpha=0.7, label="Bắt đầu DDL (t=5s)")
    ax.set_title("TiDB 8.5.7 (Online DDL — không chặn tải mới)")
    ax.set_xlabel("Thời gian pha đo (giây)")
    ax.set_ylabel("Thông lượng (TPS)")
    ax.set_ylim(bottom=-80)
    ax.legend(loc="lower right", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6_e1_mdl_freeze.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_fig6_e2() -> None:
    """Biểu đồ 6 (phần E2): Chuỗi TPS và p99 theo từng giây của P1 Eager, P2 Batch 1000, P3 Lazy trên 3 hệ."""
    eager_runs = load_runs("2.4-eager")
    batch_runs = load_runs("2.4-batch")
    lazy_runs = load_runs("2.4-lazy")

    engines = [
        ("mysql", "MySQL 8.4.8 (InnoDB)"),
        ("mongo", "MongoDB 8.0.20 (WiredTiger)"),
        ("tidb", "TiDB 8.5.7 (3 TiKV)"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.2), sharex=True)
    fig.suptitle(
        "Biểu đồ 6 (E2): TPS (hàng trên) và p99 (hàng dưới, thang log) theo từng giây trong lúc chuyển dữ liệu\n"
        "(W=10, ~3 triệu dòng order_line, 64 client, θ=0,5, q=25%, lượt trung vị trên 3 lần chạy)",
        fontsize=12, fontweight="bold", y=0.99,
    )

    for col, (eng, title) in enumerate(engines):
        ax_tps = axes[0, col]
        ax_p99 = axes[1, col]
        specs = [
            ("P1 – Eager", [x for x in eager_runs if x[1]["engine"] == eng and x[1].get("old_order_read_pct") == 25.0], "#d62728", "-"),
            ("P2 – Batch 1.000", [x for x in batch_runs if x[1]["engine"] == eng and x[1].get("migration_batch_size") == 1000 and x[1].get("old_order_read_pct") == 25.0], "#1f77b4", "-"),
            ("P3 – Lazy (q=25%)", [x for x in lazy_runs if x[1]["engine"] == eng and x[1].get("old_order_read_pct") == 25.0], "#2ca02c", "--"),
        ]
        for label, matched, color, ls in specs:
            if not matched:
                continue
            run_dir, d = pick_median_run(matched)
            secs, tpss, p99s = read_series(d)
            ax_tps.plot(secs, tpss, label=label, color=color, linestyle=ls, linewidth=1.9)
            valid_p99 = [(s, p) for s, p in zip(secs, p99s) if p is not None and p > 0]
            if valid_p99:
                ax_p99.plot([x[0] for x in valid_p99], [x[1] for x in valid_p99],
                            label=label, color=color, linestyle=ls, linewidth=1.9)

        ax_tps.axvline(2, color="black", linestyle=":", linewidth=1.1, alpha=0.7, label="Bắt đầu migration (t=2s)")
        ax_p99.axvline(2, color="black", linestyle=":", linewidth=1.1, alpha=0.7)
        ax_tps.set_title(title)
        ax_p99.set_yscale("log")
        ax_p99.set_xlabel("Thời gian pha đo (giây)")
        if col == 0:
            ax_tps.set_ylabel("Thông lượng (TPS)")
            ax_p99.set_ylabel("Độ trễ p99 (ms, thang log)")
        ax_tps.legend(loc="lower right", fontsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "fig6_e2_strategies.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_fig6b_e3() -> None:
    """Biểu đồ 6b (phần E3): Ảnh hưởng tỉ lệ q ∈ {5%, 25%, 50%} — P2 Batch 1000 vs P3 Lazy (MySQL & MongoDB)."""
    base_runs = load_runs("2.4-baseline")
    batch_runs = load_runs("2.4-batch")
    lazy_runs = load_runs("2.4-lazy")

    qs = [5.0, 25.0, 50.0]

    def series_stats(runs, engine, q, metric, batch_size=None):
        vals = [
            d["measurement"][metric]
            for _, d in runs
            if d["engine"] == engine and d.get("old_order_read_pct") == q
            and (batch_size is None or d.get("migration_batch_size") == batch_size)
        ]
        med = statistics.median(vals)
        return med, med - min(vals), max(vals) - med

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.2), sharex=True)
    fig.suptitle(
        "Biểu đồ 6b (E3): Ảnh hưởng của tỉ lệ truy cập dữ liệu cũ q đến TPS và p99 — P2 Batch 1.000 vs P3 Lazy\n"
        "(W=10, 64 client, θ=0,5; điểm trung vị kèm khoảng min–max của 3 lần chạy độc lập)",
        fontsize=12, fontweight="bold", y=0.99,
    )

    for col, (eng, title) in enumerate([("mysql", "MySQL 8.4.8 (InnoDB)"), ("mongo", "MongoDB 8.0.20 (WiredTiger)")]):
        for row, (metric, ylabel) in enumerate([("tps", "Thông lượng (TPS)"), ("p99_ms", "Độ trễ p99 toàn pha (ms)")]):
            ax = axes[row, col]
            for label, runs, bs, color, marker, ls in [
                ("Nền không migration (none)", base_runs, None, "#7f7f7f", "s", ":"),
                ("P2 – Batch 1.000", batch_runs, 1000, "#1f77b4", "o", "-"),
                ("P3 – Lazy", lazy_runs, 1000, "#2ca02c", "^", "--"),
            ]:
                stats = [series_stats(runs, eng, q, metric, bs) for q in qs]
                meds = [s[0] for s in stats]
                yerr = [[s[1] for s in stats], [s[2] for s in stats]]
                ax.errorbar(qs, meds, yerr=yerr, label=label, color=color, marker=marker,
                            linestyle=ls, linewidth=2.2, markersize=7, capsize=4)
            if row == 0:
                ax.set_title(title)
            else:
                ax.set_xlabel("Tỉ lệ giao dịch 'Xem đơn cũ' q (%)")
            if col == 0:
                ax.set_ylabel(ylabel)
            ax.set_xticks(qs)
            ax.set_xticklabels(["5%", "25%", "50%"])
            ax.legend(loc="best", fontsize=8.5)

        # Chú thích điểm đảo chiều trên MySQL
        if eng == "mysql":
            axes[0, 0].annotate(
                "Điểm đảo chiều:\nq=5% Lazy thắng P2\n(1.027 vs 988 TPS)",
                xy=(5, 1027), xytext=(12, 1380),
                arrowprops={"arrowstyle": "->", "color": "#2ca02c", "lw": 1.4},
                fontsize=8.5, fontweight="bold", color="#1b6e1b",
                bbox={"boxstyle": "round,pad=0.3", "fc": "#eef9ee", "ec": "#2ca02c"},
            )

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "fig6b_e3_q_sweep.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_fig6_e1()
    plot_fig6_e2()
    plot_fig6b_e3()
    for p in sorted(OUT_DIR.glob("*.png")):
        print(f"Đã tạo: {p.relative_to(ROOT)} ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
