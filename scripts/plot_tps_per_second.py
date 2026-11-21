"""Vẽ TPS theo từng giây (warmup + đo) từ `tps_per_second.csv` của các lượt đã lưu, không cần thư viện ngoài.

Mục đích: kiểm tra 30 giây warmup có đủ không (bản chốt mục 2.1). Mỗi ô là một (hệ, θ, số client), mỗi đường là
một lần lặp; vùng xám là warmup.

Dùng:
    python scripts/plot_tps_per_second.py --results-dir results/official/2.1-aws --out results/official/2.1-aws/plots
Kết quả là các file SVG (mở bằng trình duyệt; muốn PNG thì chụp hoặc xuất từ trình duyệt/Inkscape).
"""
import argparse
import csv
from html import escape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from flashsale.benchmark.report import collect  # noqa: E402

ENGINES = ("mysql", "mongo", "tidb")
COLORS = ("#1f77b4", "#d62728", "#2ca02c")  # ba lần lặp
PANEL_W, PANEL_H = 380, 190
LEFT, RIGHT, TOP, BOTTOM = 54, 14, 30, 34


def read_series(run_dir: Path) -> tuple[list[int], list[int]]:
    warmup: dict[int, int] = {}
    measurement: dict[int, int] = {}
    with (run_dir / "tps_per_second.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            target = warmup if row["phase"] == "warmup" else measurement
            target[int(row["second"])] = int(row["successes"])
    return ([warmup[i] for i in sorted(warmup)], [measurement[i] for i in sorted(measurement)])


def select(rows: list[dict], engine: str, concurrency: int, theta: float, note=None) -> list[dict]:
    chosen = [r for r in rows if r["engine"] == engine and r["profile"] == "performance"
              and r["concurrency"] == concurrency and r["theta"] == theta and not r["hot_item"]
              and r["validation"] == "VALID" and r["run_note"] == note]
    return sorted(chosen, key=lambda r: r["repetition"])


def panel(x0: float, y0: float, title: str, runs: list[tuple[int, list[int], list[int]]]) -> str:
    plot_w, plot_h = PANEL_W - LEFT - RIGHT, PANEL_H - TOP - BOTTOM
    peak = max((max(w + m) for _, w, m in runs if w + m), default=1)
    top = peak * 1.1
    seconds = max((len(w) + len(m) for _, w, m in runs), default=90)
    warm = max((len(w) for _, w, _ in runs), default=30)

    def sx(t: float) -> float:
        return x0 + LEFT + plot_w * t / seconds

    def sy(v: float) -> float:
        return y0 + TOP + plot_h * (1 - v / top)

    parts = [f'<text x="{x0 + LEFT}" y="{y0 + 17}" font-size="13" font-weight="600" fill="#222">{escape(title)}</text>',
             f'<rect x="{sx(0)}" y="{sy(top)}" width="{sx(warm) - sx(0)}" height="{plot_h}" fill="#eeeeee"/>',
             f'<text x="{sx(warm / 2)}" y="{sy(top) + 12}" font-size="10" fill="#888" text-anchor="middle">warmup</text>']
    for tick in (0, 0.5, 1.0):
        value = top / 1.1 * tick
        parts.append(f'<line x1="{x0 + LEFT}" x2="{x0 + LEFT + plot_w}" y1="{sy(value)}" y2="{sy(value)}" stroke="#ddd"/>')
        parts.append(f'<text x="{x0 + LEFT - 6}" y="{sy(value) + 4}" font-size="10" fill="#555" text-anchor="end">{value:.0f}</text>')
    for t in range(0, seconds + 1, 30):
        parts.append(f'<text x="{sx(t)}" y="{y0 + TOP + plot_h + 14}" font-size="10" fill="#555" text-anchor="middle">{t}</text>')
    parts.append(f'<text x="{x0 + LEFT + plot_w / 2}" y="{y0 + PANEL_H - 6}" font-size="10" fill="#555" text-anchor="middle">giây</text>')
    for index, (repetition, w, m) in enumerate(runs):
        values = w + m
        points = " ".join(f"{sx(i + 0.5):.1f},{sy(v):.1f}" for i, v in enumerate(values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{COLORS[index % 3]}" stroke-width="1.3" opacity="0.9"/>')
        parts.append(f'<text x="{x0 + LEFT + plot_w - 4}" y="{y0 + TOP + 12 + 12 * index}" font-size="10" fill="{COLORS[index % 3]}" text-anchor="end">lần {repetition}</text>')
    parts.append(f'<line x1="{sx(warm)}" x2="{sx(warm)}" y1="{sy(top)}" y2="{sy(0)}" stroke="#999" stroke-dasharray="3 3"/>')
    return "\n".join(parts)


def figure(rows: list[dict], root: Path, cells: list[tuple[str, int, float, str | None]], title: str, columns: int) -> str:
    panels = []
    for position, (engine, concurrency, theta, note) in enumerate(cells):
        runs = [(r["repetition"], *read_series(root / r["run_id"])) for r in select(rows, engine, concurrency, theta, note)]
        if not runs:
            continue
        col, row = position % columns, position // columns
        label = f"{engine} · θ={theta:g} · {concurrency} client"
        panels.append(panel(col * PANEL_W, 36 + row * PANEL_H, label, runs))
    lines = -(-len(cells) // columns)
    width, height = columns * PANEL_W, 36 + lines * PANEL_H + 8
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'font-family="Segoe UI, Arial, sans-serif" role="img" aria-label="{escape(title)}">'
            f'<rect width="100%" height="100%" fill="#fff"/>'
            f'<text x="12" y="22" font-size="15" font-weight="600" fill="#111">{escape(title)}</text>\n'
            + "\n".join(panels) + "</svg>\n")


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--results-dir", type=Path, default=Path("results/official/2.1-aws"))
    cli.add_argument("--out", type=Path, default=None)
    args = cli.parse_args()
    out = args.out or args.results_dir / "plots"
    out.mkdir(parents=True, exist_ok=True)
    rows = collect(args.results_dir)
    low = [(e, 8, theta, None) for theta in (0.0, 0.9) for e in ENGINES]
    # θ ở cột trái/phải: sắp lại để mỗi hàng là một hệ, hai cột là θ=0 và θ=0,9
    low = [(e, 8, theta, None) for e in ENGINES for theta in (0.0, 0.9)]
    (out / "tps-per-second-8-client.svg").write_text(
        figure(rows, args.results_dir, low, "TPS mỗi giây, 8 client (vùng xám = 30 giây warmup)", 2), encoding="utf-8")
    high = [("mysql", 64, 0.0, None), ("mongo", 64, 0.0, "loadgen_c6i.4xlarge"), ("tidb", 64, 0.0, None),
            ("mysql", 256, 0.0, None), ("mongo", 256, 0.0, "loadgen_c6i.4xlarge"), ("tidb", 256, 0.0, None)]
    (out / "tps-per-second-64-256-client.svg").write_text(
        figure(rows, args.results_dir, high, "TPS mỗi giây, 64 và 256 client, θ=0 (vùng xám = warmup)", 3), encoding="utf-8")
    print("đã ghi", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
