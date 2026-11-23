#!/usr/bin/env python3
"""Sinh hình và CSV nguồn cho báo cáo từ INDEX.csv của results/official (chỉ đọc, không chạm DBMS).

Mỗi hình đi kèm một CSV cùng tên (trung vị, min, max, số lượt) để đối chiếu số trong báo cáo.
  python scripts/make_figures.py --out results/official/figures
"""
import argparse
import csv
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R22, R23 = Path("results/official/2.2-aws"), Path("results/official/2.3-aws")
COLORS = {"MySQL": "#1f77b4", "MongoDB": "#2ca02c", "TiDB": "#d62728"}


def rows(*dirs: Path) -> list[dict]:
    out = []
    for folder in dirs:
        path = folder / "INDEX.csv"
        if path.is_file():
            with path.open(encoding="utf-8") as stream:
                for row in csv.DictReader(stream):
                    row["_src"] = folder.name
                    out.append(row)
    return [r for r in out if r["validation"] == "VALID" and r["tps"] not in ("", None)]


def stat(rs: list[dict], key: str = "tps"):
    vals = [float(r[key]) for r in rs if r.get(key) not in ("", None)]
    return (statistics.median(vals), min(vals), max(vals), len(vals)) if vals else (None, None, None, 0)


def pick(rs, **kw):
    return [r for r in rs if all(str(r.get(k)) == str(v) for k, v in kw.items())]


def write_csv(path: Path, header: list[str], table: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(table)


def bars(ax, groups: list[str], series: dict[str, list], ylabel: str, colors=None) -> None:
    width = 0.8 / max(len(series), 1)
    for i, (name, values) in enumerate(series.items()):
        xs = [g + i * width - 0.4 + width / 2 for g in range(len(groups))]
        med = [v[0] or 0 for v in values]
        lo = [(v[0] - v[1]) if v[0] is not None else 0 for v in values]
        hi = [(v[2] - v[0]) if v[0] is not None else 0 for v in values]
        ax.bar(xs, med, width * 0.92, label=name, yerr=[lo, hi], capsize=2, color=(colors or {}).get(name))
    ax.set_xticks(range(len(groups)), groups)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="results/official/figures")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    base = dict(label="hotspot", warehouse_mode="single-warehouse", lock_order="False", nowait="False",
                stored_procedure="False")
    eng = {"MySQL": rows(R22 / "mysql"), "MongoDB": rows(R22 / "mongo"), "TiDB": rows(R22 / "tidb3")}
    # Mongo ở 256 client: dùng số đo lại sau khi nâng nofile (docs/assumptions.md)
    postfix = rows(R22 / "mongo-t1-c256-postfix")
    eng["MongoDB"] = [r for r in eng["MongoDB"] if r["concurrency"] != "256"] + postfix

    # Hình 1: T1, P1, 64 client, theo mức tập trung
    cats = [("θ=0", dict(theta="0.0", hot_item="False")), ("θ=0,5", dict(theta="0.5", hot_item="False")),
            ("θ=0,7", dict(theta="0.7", hot_item="False")), ("θ=0,9", dict(theta="0.9", hot_item="False")),
            ("một món", dict(theta="0.0", hot_item="True"))]
    series, table = {}, []
    for name, rs in eng.items():
        vals = []
        for label, kw in cats:
            sel = pick(rs, variant="p1", concurrency="64", txn_mode="default", mongo_design="a", **base, **kw)
            vals.append(stat(sel))
            table.append([name, label, *stat(sel)])
        series[name] = vals
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars(ax, [c[0] for c in cats], series, "TPS (trung vị, thanh = min–max)", COLORS)
    ax.set_title("T1: P1, một kho, 64 client")
    fig.tight_layout()
    fig.savefig(out / "fig1_t1_theta.png", dpi=160)
    plt.close(fig)
    write_csv(out / "fig1_t1_theta.csv", ["dbms", "muc_tap_trung", "tps_median", "tps_min", "tps_max", "n"], table)

    # Hình 2: P1 -> P2, một món, 64 client, lô mã 50
    steps = ["P1", "P2 N=1", "P2 N=3", "P2 N=9", "P2 N=27"]
    series, table = {}, []
    for name, rs in eng.items():
        vals = [stat(pick(rs, variant="p1", concurrency="64", hot_item="True", txn_mode="default", mongo_design="a",
                          order_id_batch="0", **base))]
        for n in (1, 3, 9, 27):
            vals.append(stat(pick(rs, variant="p2", concurrency="64", hot_item="True", slots=str(n),
                                  order_id_batch="50", **base)))
        series[name] = vals
        table += [[name, s, *v] for s, v in zip(steps, vals)]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars(ax, list(series), {s: [series[d][i] for d in series] for i, s in enumerate(steps)}, "TPS (trung vị)")
    ax.set_title("T2: chia tồn kho thành N slot, một món, 64 client, lô mã 50")
    fig.tight_layout()
    fig.savefig(out / "fig2_p1_to_p2.png", dpi=160)
    plt.close(fig)
    write_csv(out / "fig2_p1_to_p2.csv", ["dbms", "bien_the", "tps_median", "tps_min", "tps_max", "n"], table)

    # Hình 3: tác động riêng của cấp mã đơn theo lô (P2 N=9, 64 client)
    series, table = {}, []
    groups = [("một món", dict(hot_item="True")), ("θ=0,9", dict(hot_item="False", theta="0.9"))]
    for name, rs in eng.items():
        for batch, label in (("0", "không lô"), ("50", "lô 50")):
            vals = [stat(pick(rs, variant="p2", concurrency="64", slots="9", order_id_batch=batch, **base, **kw))
                    for _, kw in groups]
            series[f"{name} {label}"] = vals
            table += [[name, label, g[0], *v] for g, v in zip(groups, vals)]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars(ax, [g[0] for g in groups], series, "TPS (trung vị)")
    ax.set_title("Tách cấp mã theo lô khỏi chia slot (P2 N=9, 64 client)")
    fig.tight_layout()
    fig.savefig(out / "fig3_batch_effect.png", dpi=160)
    plt.close(fig)
    write_csv(out / "fig3_batch_effect.csv",
              ["dbms", "lo_ma", "muc_tap_trung", "tps_median", "tps_min", "tps_max", "n"], table)

    # Hình 4: bảng 2x2 trên TiDB (số TiKV x chia slot), θ=0,9, 64 client, lô mã 50
    tikv = {1: rows(R23 / "tidb1"), 3: rows(R23 / "tidb3")}
    table, lines = [], {}
    for label, kw in (("P1 (N=1)", dict(variant="p1")), ("P2 (N=27)", dict(variant="p2", slots="27"))):
        vals = []
        for k in (1, 3):
            sel = pick(tikv[k], order_warehouses="1-1", theta="0.9", concurrency="64", order_id_batch="50",
                       hot_item="False", tikv_count=str(k), **kw)
            vals.append(stat(sel))
            table.append([label, k, *stat(sel)])
        lines[label] = vals
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for label, vals in lines.items():
        ax.errorbar([1, 3], [v[0] for v in vals], yerr=[[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]],
                    marker="o", capsize=3, label=label)
    ax.set_xticks([1, 3], ["1 TiKV", "3 TiKV"])
    ax.set_ylabel("TPS (trung vị)")
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title("TiDB: thêm TiKV × chia tồn kho (θ=0,9, 64 client)")
    fig.tight_layout()
    fig.savefig(out / "fig4_tidb_2x2.png", dpi=160)
    plt.close(fig)
    write_csv(out / "fig4_tidb_2x2.csv", ["thiet_ke", "tikv", "tps_median", "tps_min", "tps_max", "n"], table)

    # Hình 5: T3, p99 theo tải đặt, P2 so với P3 (MongoDB; MySQL nếu đã có)
    t3 = {"MongoDB": rows(R22 / "mongo-t3", R22 / "mongo-t3-p2-postfix"), "MySQL": rows(R22 / "mysql-t3")}
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    table = []
    for ax, clients in zip(axes, ("128", "256")):
        for name, rs in t3.items():
            for variant, style in (("p2", "--"), ("p3", "-")):
                sel = [r for r in rs if r["variant"] == variant and r["concurrency"] == clients and r["arrival_rate"]
                       and not (name == "MongoDB" and clients == "256" and variant == "p2" and r["_src"] == "mongo-t3")]
                rates = sorted({float(r["arrival_rate"]) for r in sel})
                pts = [(rate, [r for r in sel if float(r["arrival_rate"]) == rate]) for rate in rates]
                if pts:
                    ax.plot([p[0] for p in pts], [stat(p[1], "p99_ms")[0] for p in pts], style, marker="o",
                            label=f"{name} {variant.upper()}")
                    table += [[name, variant, clients, p[0], *stat(p[1], "p99_ms"), stat(p[1])[0]] for p in pts]
        ax.set_title(f"{clients} client")
        ax.set_xlabel("tải đặt (yêu cầu/s)")
        ax.set_ylabel("p99 (ms)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("T3: tải vòng mở, θ=0,9 (P2 nét đứt, P3 nét liền)")
    fig.tight_layout()
    fig.savefig(out / "fig5_t3_p99.png", dpi=160)
    plt.close(fig)
    write_csv(out / "fig5_t3_p99.csv",
              ["dbms", "bien_the", "client", "tai_dat", "p99_median", "p99_min", "p99_max", "n", "tps_median"], table)

    # Hình 6: T4, một món, 128 client
    my, mo, ti = eng["MySQL"], eng["MongoDB"], eng["TiDB"]
    cfg = dict(label="hotspot", warehouse_mode="single-warehouse", concurrency="128", hot_item="True")
    items = [("MySQL legacy", pick(my, variant="legacy", lock_order="False", nowait="False", stored_procedure="False",
                                   **cfg)),
             ("MySQL SP", pick(my, variant="legacy", stored_procedure="True", **cfg)),
             ("MySQL NOWAIT", pick(my, variant="legacy", nowait="True", **cfg)),
             ("MySQL khóa thứ tự", pick(my, variant="legacy", lock_order="True", **cfg)),
             ("Mongo (a)", pick(mo, variant="p1", mongo_design="a", **cfg)),
             ("Mongo (b)", pick(mo, variant="p1", mongo_design="b", **cfg)),
             ("TiDB bi quan", pick(ti, variant="p1", txn_mode="pessimistic", **cfg)),
             ("TiDB lạc quan", pick(ti, variant="p1", txn_mode="optimistic", **cfg))]
    table = [[name, *stat(sel)] for name, sel in items]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar([t[0] for t in table], [t[1] or 0 for t in table], color=["#1f77b4"] * 4 + ["#2ca02c"] * 2 + ["#d62728"] * 2)
    ax.set_ylabel("TPS (trung vị)")
    ax.set_title("T4: cơ chế riêng từng hệ, một món, 128 client")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "fig6_t4.png", dpi=160)
    plt.close(fig)
    write_csv(out / "fig6_t4.csv", ["cau_hinh", "tps_median", "tps_min", "tps_max", "n"], table)
    print(f"Đã ghi 6 hình và CSV vào {out}")


if __name__ == "__main__":
    main()
