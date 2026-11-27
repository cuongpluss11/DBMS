"""Sinh bộ biểu đồ mục 2.6 & Phụ lục D (không gắn tiêu đề trên đỉnh ảnh để đặt tên hình chuẩn dưới ảnh trong báo cáo)
từ dữ liệu thực đo trong `results/official/2.4-{baseline,eager,batch,lazy,highload,e1}/`.

Cách chạy:
    python scripts/plot-2.4.py
Đầu ra:
    docs/figures/2.4/fig6_bar_e1_mdl.png        (Hình 2.6.1 — Bar chart DDL & MDL)
    docs/figures/2.4/fig6_bar_e2_strategies.png (Hình 2.6.2 — Bar chart tải chuẩn)
    docs/figures/2.4/fig6_e1_mdl_freeze.png     (Hình D.1 — Time-series DDL & MDL)
    docs/figures/2.4/fig6_e2_strategies.png     (Hình D.2 — Time-series tải chuẩn)
    docs/figures/2.4/fig6c_e2_highload.png      (Hình D.3 — Bar chart tải cao)
    docs/figures/2.4/fig6_bar_e3_q_sweep.png    (Hình D.4 — Bar chart quét q)
    docs/figures/2.4/fig6b_e3_q_sweep.png       (Hình D.5 — Đường cong quét q)
"""

from __future__ import annotations

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
    "axes.titlesize": 10.5,
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
    """Hình D.1: Tác động DDL gốc & kẹt Metadata Lock theo từng giây trên 3 hệ."""
    e1_runs = load_runs("2.4-e1")

    def get_med(engine: str, scenario: str):
        matched = [(p, d) for p, d in e1_runs if d["engine"] == engine and d["scenario"] == scenario]
        return pick_median_run(matched) if matched else None

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), sharey=False)

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
    ax.set_title("MySQL 8.4.8 (InnoDB)", fontweight="bold")
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
    ax.set_title("MongoDB 8.0.20 (WiredTiger)", fontweight="bold")
    ax.set_xlabel("Thời gian pha đo (giây)")
    ax.set_ylabel("Thông lượng (TPS)")
    ax.set_ylim(bottom=-80)
    ax.legend(loc="lower right", fontsize=8)

    # Panel 3: TiDB v8.5.7
    ax = axes[2]
    tidb_specs = [
        ("add_column_online", "ADD COLUMN Online DDL (1,2s, 0s đóng băng)", "#2ca02c", "-"),
        ("add_index_online", "ADD INDEX Online DDL (41,9s, 0s đóng băng)", "#ff7f0e", "--"),
        ("mdl_long_txn", "ADD COLUMN + đọc giữ 60s (59,3s, 0s đóng băng)", "#1f77b4", "-"),
    ]
    for scen, label, color, ls in tidb_specs:
        item = get_med("tidb", scen)
        if not item:
            continue
        secs, tpss, _ = read_series(item[1])
        ax.plot(secs, tpss, label=label, color=color, linestyle=ls, linewidth=2.0)
    ax.axvline(5, color="black", linestyle=":", linewidth=1.2, alpha=0.7, label="Bắt đầu DDL (t=5s)")
    ax.set_title("TiDB v8.5.7 (Online DDL)", fontweight="bold")
    ax.set_xlabel("Thời gian pha đo (giây)")
    ax.set_ylabel("Thông lượng (TPS)")
    ax.set_ylim(bottom=-80)
    ax.legend(loc="lower right", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6_e1_mdl_freeze.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_fig6_e2() -> None:
    """Hình D.2: Chuỗi TPS và p99 theo từng giây của Eager, Batch 1.000, Lazy trên 3 hệ."""
    eager_runs = load_runs("2.4-eager")
    batch_runs = load_runs("2.4-batch")
    lazy_runs = load_runs("2.4-lazy")

    engines = [
        ("mysql", "MySQL 8.4.8 (InnoDB)"),
        ("mongo", "MongoDB 8.0.20 (WiredTiger)"),
        ("tidb", "TiDB v8.5.7 (3 TiKV)"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(16, 7.6), sharex=True)

    for col, (eng, title) in enumerate(engines):
        ax_tps = axes[0, col]
        ax_p99 = axes[1, col]
        specs = [
            ("Eager", [x for x in eager_runs if x[1]["engine"] == eng and x[1].get("old_order_read_pct") == 25.0], "#d62728", "-"),
            ("Batch 1.000", [x for x in batch_runs if x[1]["engine"] == eng and x[1].get("migration_batch_size") == 1000 and x[1].get("old_order_read_pct") == 25.0], "#1f77b4", "-"),
            ("Lazy (q=25%)", [x for x in lazy_runs if x[1]["engine"] == eng and x[1].get("old_order_read_pct") == 25.0], "#2ca02c", "--"),
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
        ax_tps.set_title(title, fontweight="bold")
        ax_p99.set_yscale("log")
        ax_p99.set_xlabel("Thời gian pha đo (giây)")
        if col == 0:
            ax_tps.set_ylabel("Thông lượng (TPS)")
            ax_p99.set_ylabel("Độ trễ p99 (ms, thang log)")
        ax_tps.legend(loc="lower right", fontsize=8.5)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6_e2_strategies.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_fig6b_e3() -> None:
    """Hình D.5: Đường cong TPS và p99 khi quét q ∈ {5%, 25%, 50%} (MySQL & MongoDB)."""
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

    fig, axes = plt.subplots(2, 2, figsize=(13, 7.6), sharex=True)

    for col, (eng, title) in enumerate([("mysql", "MySQL 8.4.8 (InnoDB)"), ("mongo", "MongoDB 8.0.20 (WiredTiger)")]):
        for row, (metric, ylabel) in enumerate([("tps", "Thông lượng (TPS)"), ("p99_ms", "Độ trễ p99 toàn pha (ms)")]):
            ax = axes[row, col]
            for label, runs, bs, color, marker, ls in [
                ("Nền (none)", base_runs, None, "#7f7f7f", "s", ":"),
                ("Batch 1.000", batch_runs, 1000, "#1f77b4", "o", "-"),
                ("Lazy", lazy_runs, 1000, "#2ca02c", "^", "--"),
            ]:
                stats = [series_stats(runs, eng, q, metric, bs) for q in qs]
                meds = [s[0] for s in stats]
                yerr = [[s[1] for s in stats], [s[2] for s in stats]]
                ax.errorbar(qs, meds, yerr=yerr, label=label, color=color, marker=marker,
                            linestyle=ls, linewidth=2.2, markersize=7, capsize=4)
            if row == 0:
                ax.set_title(title, fontweight="bold")
            else:
                ax.set_xlabel("Tỉ lệ giao dịch 'Xem đơn cũ' q (%)")
            if col == 0:
                ax.set_ylabel(ylabel)
            ax.set_xticks(qs)
            ax.set_xticklabels(["5%", "25%", "50%"])
            ax.legend(loc="best", fontsize=8.5)

        if eng == "mysql":
            axes[0, 0].annotate(
                "Điểm đảo chiều:\nq=5% Lazy thắng Batch\n(1.027 vs 988 TPS)",
                xy=(5, 1027), xytext=(12, 1380),
                arrowprops={"arrowstyle": "->", "color": "#2ca02c", "lw": 1.4},
                fontsize=8.5, fontweight="bold", color="#1b6e1b",
                bbox={"boxstyle": "round,pad=0.3", "fc": "#eef9ee", "ec": "#2ca02c"},
            )

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6b_e3_q_sweep.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_fig6c_highload() -> None:
    """Hình D.3: So sánh TPS và p99 tại tải cao θ=0,9, 128 client trên 3 hệ."""
    hl_runs = load_runs("2.4-highload")
    if not hl_runs:
        return

    engines = [
        ("mysql", "MySQL 8.4.8"),
        ("mongo", "MongoDB 8.0.20"),
        ("tidb", "TiDB v8.5.7"),
    ]
    strategies = [
        ("none", None, "Nền (none)", "#7f7f7f"),
        ("eager", None, "Eager", "#d62728"),
        ("batch", 5000, "Batch 5.000", "#ff7f0e"),
        ("batch", 1000, "Batch 1.000", "#1f77b4"),
        ("lazy", 1000, "Lazy", "#2ca02c"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 4.9))

    x_base = list(range(len(engines)))
    width = 0.15
    for idx, (strat, bs, label, color) in enumerate(strategies):
        offsets = [x + (idx - 2) * width for x in x_base]
        tps_vals, p99_vals = [], []
        for eng, _ in engines:
            matched = [
                d for _, d in hl_runs
                if d["engine"] == eng and d.get("migration_strategy") == strat
                and (bs is None or d.get("migration_batch_size") == bs)
            ]
            tps_vals.append(statistics.median([d["measurement"]["tps"] for d in matched]) if matched else 0.0)
            p99_vals.append(statistics.median([d["measurement"]["p99_ms"] for d in matched]) if matched else 0.0)

        bars1 = axes[0].bar(offsets, tps_vals, width=width, label=label, color=color, alpha=0.92)
        bars2 = axes[1].bar(offsets, p99_vals, width=width, label=label, color=color, alpha=0.92)
        for bar, val in zip(bars1, tps_vals):
            axes[0].text(bar.get_x() + bar.get_width() / 2, val + 35, f"{val:.0f}",
                         ha="center", va="bottom", fontsize=7.5, rotation=90)
        for bar, val in zip(bars2, p99_vals):
            axes[1].text(bar.get_x() + bar.get_width() / 2, val + 20, f"{val:.0f}",
                         ha="center", va="bottom", fontsize=7.5, rotation=90)

    for ax, title, ylabel, ylim, leg_loc in [
        (axes[0], "Thông lượng thành công (TPS — cao hơn là tốt hơn)", "TPS (giao dịch/giây)", 3150, "upper right"),
        (axes[1], "Độ trễ đuôi p99 toàn pha (ms — thấp hơn là tốt hơn)", "Độ trễ p99 (ms)", 1620, "upper left"),
    ]:
        ax.set_title(title, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.set_xticks(x_base)
        ax.set_xticklabels([e[1] for e in engines], fontweight="bold")
        ax.set_ylim(0, ylim)
        ax.legend(loc=leg_loc, fontsize=8.5)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6c_e2_highload.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_bar_e1() -> None:
    """Hình 2.6.1: So sánh TPS và thời gian đóng băng 0 TPS giữa các cơ chế DDL."""
    e1_runs = load_runs("2.4-e1")
    if not e1_runs:
        return

    specs = [
        ("mysql", "add_column_instant", "MySQL: ADD COLUMN INSTANT", "#2ca02c"),
        ("mysql", "add_column_copy", "MySQL: ADD COLUMN COPY", "#ff7f0e"),
        ("mysql", "add_index_inplace", "MySQL: ADD INDEX INPLACE", "#9467bd"),
        ("mysql", "mdl_freeze", "MySQL: Đọc dài 60s + DDL (MDL Freeze)", "#d62728"),
        ("mysql", "mdl_timeout_retry", "MySQL: MDL + lock_wait_timeout=3s", "#1f77b4"),
        ("mongo", "create_index", "MongoDB: createIndex (thường)", "#2ca02c"),
        ("mongo", "create_index_long_txn", "MongoDB: createIndex + đọc dài 60s", "#e377c2"),
        ("tidb", "add_column_online", "TiDB: ADD COLUMN Online DDL", "#2ca02c"),
        ("tidb", "add_index_online", "TiDB: ADD INDEX Online DDL", "#17becf"),
        ("tidb", "mdl_long_txn", "TiDB: ADD COLUMN + đọc dài 60s", "#1f77b4"),
    ]

    labels, tps_meds, freeze_meds, colors = [], [], [], []
    for eng, scen, lbl, col in reversed(specs):
        matched = [d for _, d in e1_runs if d["engine"] == eng and d["scenario"] == scen]
        if not matched:
            continue
        labels.append(lbl)
        tps_meds.append(statistics.median([d["measurement"]["tps"] for d in matched]))
        freeze_meds.append(statistics.median([float(d["ddl"]["max_freeze_seconds"]) for d in matched]))
        colors.append(col)

    y_pos = list(range(len(labels)))
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 5.6), sharey=True)

    # Trái: TPS
    bars_tps = axes[0].barh(y_pos, tps_meds, color=colors, height=0.66, alpha=0.92, edgecolor="#333333", linewidth=0.5)
    axes[0].set_title("Thông lượng pha đo (TPS — cao hơn là tốt hơn)", fontweight="bold")
    axes[0].set_xlabel("TPS trung vị (giao dịch/giây)")
    axes[0].set_yticks(y_pos)
    axes[0].set_yticklabels(labels, fontsize=9.5, fontweight="bold")
    axes[0].set_xlim(0, 2480)
    for bar, val in zip(bars_tps, tps_meds):
        axes[0].text(val + 30, bar.get_y() + bar.get_height() / 2, f"{val:,.1f}".replace(",", "_").replace(".", ",").replace("_", "."),
                     va="center", ha="left", fontsize=8.8, fontweight="bold")

    # Phải: Thời gian đóng băng lâu nhất (giây)
    bars_frz = axes[1].barh(y_pos, freeze_meds, color=colors, height=0.66, alpha=0.92, edgecolor="#333333", linewidth=0.5)
    axes[1].set_title("Thời gian đóng băng 0 TPS lâu nhất (giây — thấp hơn là tốt hơn)", fontweight="bold")
    axes[1].set_xlabel("Số giây liên tiếp hệ thống rơi về 0 TPS")
    axes[1].set_xlim(0, 75)
    for bar, val in zip(bars_frz, freeze_meds):
        txt = f"{int(round(val))} s (treo cứng!)" if val >= 50 else (f"{int(round(val))} s" if val > 0 else "0 s (không treo)")
        col_txt = "#b30000" if val >= 20 else ("#1b6e1b" if val == 0 else "#1f4e79")
        axes[1].text(val + 1.0, bar.get_y() + bar.get_height() / 2, txt,
                     va="center", ha="left", fontsize=8.8, fontweight="bold", color=col_txt)

    for ax in axes:
        ax.axhline(2.5, color="#888888", linestyle="--", linewidth=0.9, alpha=0.7)
        ax.axhline(4.5, color="#888888", linestyle="--", linewidth=0.9, alpha=0.7)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6_bar_e1_mdl.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_bar_e2() -> None:
    """Hình 2.6.2: So sánh 3 chiến lược chuyển dữ liệu tại q = 25%, 64 client, θ = 0,5."""
    all_e2 = (
        load_runs("2.4-baseline")
        + load_runs("2.4-eager")
        + load_runs("2.4-batch")
        + load_runs("2.4-lazy")
    )
    if not all_e2:
        return

    engines = [
        ("mysql", "MySQL 8.4.8 (InnoDB)"),
        ("mongo", "MongoDB 8.0.20 (WiredTiger)"),
        ("tidb", "TiDB v8.5.7 (3 TiKV)"),
    ]
    strategies = [
        ("none", None, "Nền (none)", "#7f7f7f"),
        ("eager", None, "Eager", "#d62728"),
        ("batch", 5000, "Batch 5.000", "#ff7f0e"),
        ("batch", 1000, "Batch 1.000", "#1f77b4"),
        ("lazy", 1000, "Lazy", "#2ca02c"),
    ]

    base_tps = {}
    for eng, _ in engines:
        b_vals = [
            d["measurement"]["tps"]
            for _, d in all_e2
            if d["engine"] == eng and d.get("migration_strategy") == "none" and d.get("old_order_read_pct") == 25.0
        ]
        base_tps[eng] = statistics.median(b_vals) if b_vals else 1.0

    fig, axes = plt.subplots(1, 2, figsize=(15.2, 5.1))

    x_base = list(range(len(engines)))
    width = 0.155
    for idx, (strat, bs, label, color) in enumerate(strategies):
        offsets = [x + (idx - 2) * width for x in x_base]
        tps_meds, tps_lo, tps_hi = [], [], []
        p99_meds, p99_lo, p99_hi = [], [], []
        pct_deltas = []
        for eng, _ in engines:
            matched = [
                d for _, d in all_e2
                if d["engine"] == eng
                and d.get("migration_strategy") == strat
                and d.get("old_order_read_pct") == 25.0
                and (bs is None or d.get("migration_batch_size") == bs)
            ]
            t_list = [d["measurement"]["tps"] for d in matched]
            p_list = [d["measurement"]["p99_ms"] for d in matched]
            t_med = statistics.median(t_list)
            p_med = statistics.median(p_list)
            tps_meds.append(t_med)
            tps_lo.append(t_med - min(t_list))
            tps_hi.append(max(t_list) - t_med)
            p99_meds.append(p_med)
            p99_lo.append(p_med - min(p_list))
            p99_hi.append(max(p_list) - p_med)
            pct_deltas.append(0.0 if strat == "none" else 100.0 * (t_med - base_tps[eng]) / base_tps[eng])

        bars1 = axes[0].bar(
            offsets, tps_meds, width=width, label=label, color=color, alpha=0.92,
            yerr=[tps_lo, tps_hi], capsize=2.5, error_kw={"lw": 0.9, "ecolor": "#222222"},
        )
        bars2 = axes[1].bar(
            offsets, p99_meds, width=width, label=label, color=color, alpha=0.92,
            yerr=[p99_lo, p99_hi], capsize=2.5, error_kw={"lw": 0.9, "ecolor": "#222222"},
        )
        for bar, val, hi, pct in zip(bars1, tps_meds, tps_hi, pct_deltas):
            lbl_txt = f"{val:.0f}" if strat == "none" else f"{val:.0f} ({pct:+.1f}%)".replace(".", ",")
            axes[0].text(
                bar.get_x() + bar.get_width() / 2, val + hi + 40, lbl_txt,
                ha="center", va="bottom", fontsize=7.6, rotation=90,
                fontweight="bold" if (strat == "batch" and bs == 1000) else "normal",
            )
        for bar, val, hi in zip(bars2, p99_meds, p99_hi):
            axes[1].text(
                bar.get_x() + bar.get_width() / 2, val + hi + 15, f"{val:.0f}",
                ha="center", va="bottom", fontsize=7.8, rotation=90,
            )

    for ax, title, ylabel, ylim in [
        (axes[0], "Thông lượng thành công (TPS — cao hơn là tốt hơn)", "TPS (giao dịch/giây)", 2950),
        (axes[1], "Độ trễ đuôi p99 toàn pha (ms — thấp hơn là tốt hơn)", "Độ trễ p99 (ms)", 1120),
    ]:
        ax.set_title(title, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.set_xticks(x_base)
        ax.set_xticklabels([e[1] for e in engines], fontweight="bold")
        ax.set_ylim(0, ylim)
        ax.legend(loc="upper right", fontsize=8.5)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6_bar_e2_strategies.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_bar_e3() -> None:
    """Hình D.4: Quét tỉ lệ đọc đơn cũ q ∈ {5%, 25%, 50%} giữa Nền, Batch 1.000 và Lazy."""
    base_runs = load_runs("2.4-baseline")
    batch_runs = load_runs("2.4-batch")
    lazy_runs = load_runs("2.4-lazy")
    if not base_runs:
        return

    qs = [5.0, 25.0, 50.0]
    x_base = list(range(len(qs)))
    width = 0.24

    fig, axes = plt.subplots(1, 2, figsize=(14.8, 5.0))

    series_defs = [
        ("Nền (none)", base_runs, None, "#7f7f7f"),
        ("Batch 1.000", batch_runs, 1000, "#1f77b4"),
        ("Lazy (on-demand)", lazy_runs, 1000, "#2ca02c"),
    ]

    for col, (eng, title, ylim) in enumerate([
        ("mysql", "MySQL 8.4.8 (InnoDB)", 2820),
        ("mongo", "MongoDB 8.0.20 (WiredTiger)", 3650),
    ]):
        ax = axes[col]
        b_map = {}
        for q in qs:
            vals = [d["measurement"]["tps"] for _, d in base_runs if d["engine"] == eng and d.get("old_order_read_pct") == q]
            b_map[q] = statistics.median(vals)

        for idx, (label, runs, bs, color) in enumerate(series_defs):
            offsets = [x + (idx - 1) * width for x in x_base]
            meds, lo, hi, pcts = [], [], [], []
            for q in qs:
                vals = [
                    d["measurement"]["tps"]
                    for _, d in runs
                    if d["engine"] == eng
                    and d.get("old_order_read_pct") == q
                    and (bs is None or d.get("migration_batch_size") == bs)
                ]
                m = statistics.median(vals)
                meds.append(m)
                lo.append(m - min(vals))
                hi.append(max(vals) - m)
                pcts.append(0.0 if idx == 0 else 100.0 * (m - b_map[q]) / b_map[q])

            bars = ax.bar(
                offsets, meds, width=width, label=label, color=color, alpha=0.92,
                yerr=[lo, hi], capsize=3, error_kw={"lw": 1.0, "ecolor": "#222222"},
            )
            for bar, val, h_err, pct in zip(bars, meds, hi, pcts):
                txt = f"{val:.0f}" if idx == 0 else f"{val:.0f}\n({pct:+.1f}%)".replace(".", ",")
                ax.text(
                    bar.get_x() + bar.get_width() / 2, val + h_err + (35 if col == 0 else 45), txt,
                    ha="center", va="bottom", fontsize=8.0,
                    fontweight="bold" if idx > 0 else "normal",
                )

        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Tỉ lệ giao dịch đọc 'Xem đơn cũ' q")
        ax.set_ylabel("Thông lượng thành công (TPS)")
        ax.set_xticks(x_base)
        ax.set_xticklabels(["q = 5%\n(ít đọc đơn cũ)", "q = 25%\n(tải chuẩn)", "q = 50%\n(đọc đơn cũ cao)"], fontweight="bold")
        ax.set_ylim(0, ylim)
        ax.legend(loc="upper left", fontsize=8.8)

    axes[0].annotate(
        "q = 5%: Lazy thắng Batch\n(1.027 vs 988 TPS; p99 1,20× vs 1,29×)",
        xy=(0 + width, 1340), xytext=(0.46, 2360),
        arrowprops={"arrowstyle": "->", "color": "#1b6e1b", "lw": 1.4},
        fontsize=8.5, fontweight="bold", color="#1b6e1b",
        bbox={"boxstyle": "round,pad=0.35", "fc": "#eef9ee", "ec": "#2ca02c"},
    )

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig6_bar_e3_q_sweep.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_fig6_e1()
    plot_fig6_e2()
    plot_fig6b_e3()
    plot_fig6c_highload()
    plot_bar_e1()
    plot_bar_e2()
    plot_bar_e3()
    for p in sorted(OUT_DIR.glob("*.png")):
        print(f"Đã tạo: {p.relative_to(ROOT)} ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
