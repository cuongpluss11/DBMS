#!/usr/bin/env python3
"""Đối chiếu các bảng số trong docs với dữ liệu gốc (INDEX.csv/JSON trong results/official). Chỉ đọc.

Phân tích các bảng Markdown trong docs/experiment-2.2.md, docs/experiment-2.3.md và docs/fault-injection.md, tính lại
trung vị từ INDEX.csv và in từng ô lệch (sai số tương đối > 0,6% hoặc > 1 đơn vị sau làm tròn). Mã thoát 1 nếu có lệch.

  python scripts/verify_doc_numbers.py
"""
import csv
import json
from pathlib import Path
import re
import statistics
import sys

R22, R23, FI = Path("results/official/2.2-aws"), Path("results/official/2.3-aws"), Path("results/official/fault-injection")
DOC22 = Path("docs/experiment-2.2.md").read_text(encoding="utf-8")
DOC23 = Path("docs/experiment-2.3.md").read_text(encoding="utf-8")
DOCFI = Path("docs/fault-injection.md").read_text(encoding="utf-8")
bad = checked = 0


def rows(*dirs):
    out = []
    for d in dirs:
        with (d / "INDEX.csv").open(encoding="utf-8") as stream:
            out += [r for r in csv.DictReader(stream) if r["validation"] == "VALID" and r["tps"]]
    return out


def med(rs, key="tps", **kw):
    vals = [float(r[key]) for r in rs if all(str(r.get(k)) == str(v) for k, v in kw.items()) and r.get(key) not in ("", None)]
    return statistics.median(vals) if vals else None


def vn(text: str) -> float:
    text = text.strip().replace("−", "-")
    if "," in text:
        return float(text.replace(".", "").replace(",", "."))
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):
        return float(text.replace(".", ""))
    return float(text)


def section_table(doc: str, heading: str, nth: int = 0) -> list[list[str]]:
    start = doc.index(heading)
    lines = doc[start:].splitlines()
    tables, current = [], []
    for line in lines[1:]:
        if line.startswith("|"):
            current.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif current:
            tables.append(current)
            current = []
            if len(tables) > nth:
                break
    return tables[nth][2:]  # bỏ hàng tiêu đề và dòng ngăn cách


def check(label: str, doc_value: float | None, data_value: float | None, tol: float = 0.006) -> None:
    global bad, checked
    checked += 1
    if doc_value is None or data_value is None:
        bad += 1
        print(f"THIẾU  {label}: doc={doc_value} data={data_value}")
        return
    if abs(doc_value - data_value) > max(1.0, tol * abs(data_value)):
        bad += 1
        print(f"LỆCH   {label}: doc={doc_value} data={data_value:.1f}")


def cell(text: str) -> tuple[float, float | None]:
    m = re.match(r"^\s*([\-\d\.,]+)\s*(?:\(([\d\.,]+)\))?", text)
    return vn(m.group(1)), (vn(m.group(2)) if m.group(2) else None)


BASE = dict(label="hotspot", warehouse_mode="single-warehouse")
CATS = {"θ = 0": dict(theta="0.0", hot_item="False"), "θ = 0,5": dict(theta="0.5", hot_item="False"),
        "θ = 0,7": dict(theta="0.7", hot_item="False"), "θ = 0,9": dict(theta="0.9", hot_item="False"),
        "một": dict(theta="0.0", hot_item="True")}


def t1_table(doc, heading, engine_rows, extra, c256_rows=None):
    for row in section_table(doc, heading, 0):
        key = max((k for k in CATS if row[0].startswith(k)), key=len, default=None)
        if key is None:
            continue
        for col, clients in ((1, "8"), (2, "64"), (3, "256")):
            rs = (c256_rows if clients == "256" and c256_rows is not None else engine_rows)
            tps, p99 = cell(row[col])
            kw = dict(variant="p1", concurrency=clients, txn_mode="default", **BASE, **CATS[key], **extra)
            check(f"T1 {heading[-12:]} {row[0]} c{clients} TPS", tps, med(rs, **kw))
            if p99 is not None:
                check(f"T1 {heading[-12:]} {row[0]} c{clients} p99", p99, med(rs, "p99_ms", **kw))


my, mo = rows(R22 / "mysql"), rows(R22 / "mongo")
mo256 = rows(R22 / "mongo-t1-c256-postfix")
t1_table(DOC22, "## Kết quả đo chính thức trên MySQL", my, dict(lock_order="False", nowait="False", stored_procedure="False"))
t1_table(DOC22, "## Kết quả đo chính thức trên MongoDB", mo, dict(mongo_design="a"), c256_rows=mo256)


def t3_table(doc, heading, nth, series):
    for row in section_table(doc, heading, nth):
        if not re.match(r"^[\d\.]+$", row[0]):
            continue
        rate = vn(row[0])
        for col, (rs, variant, clients) in enumerate(series, 1):
            tps, p99 = cell(row[col])
            kw = dict(variant=variant, concurrency=clients, arrival_rate=f"{rate:.1f}")
            check(f"T3 {heading[-20:]} tải {rate:.0f} {variant} c{clients} TPS", tps, med(rs, **kw))
            check(f"T3 {heading[-20:]} tải {rate:.0f} {variant} c{clients} p99", p99, med(rs, "p99_ms", **kw))


my3 = rows(R22 / "mysql-t3")
mo3_128 = rows(R22 / "mongo-t3")
mo3_256_p2 = rows(R22 / "mongo-t3-p2-postfix")
t3_table(DOC22, "### T3 trên MySQL", 0, [(my3, "p2", "128"), (my3, "p3", "128"), (my3, "p2", "256"), (my3, "p3", "256")])
t3_table(DOC22, "### T3 trên MongoDB", 0, [(mo3_128, "p2", "128"), (mo3_128, "p3", "128"), (mo3_256_p2, "p2", "256"),
                                           (mo3_128, "p3", "256")])

# Nhóm R
rr = rows(R23 / "tidb3-R")
CFG = {"A": dict(variant="p1", theta="0.0"), "B": dict(variant="p1", theta="0.9"), "N=3": dict(variant="p2", slots="3"),
       "N=9": dict(variant="p2", slots="9"), "N=27": dict(variant="p2", slots="27")}
for row in section_table(DOC23, "## Nhóm R: chi phí replication", 0):
    key = "A" if row[0].startswith("A:") else "B" if row[0].startswith("B:") else next((k for k in CFG if k in row[0]), None)
    if key is None:
        continue
    a, b = vn(row[1]), vn(row[2])
    check(f"R {row[0]} rf=1 TPS", a, med(rr, run_note="tidb3-rf1", **CFG[key]))
    check(f"R {row[0]} rf=3 TPS", b, med(rr, run_note="tidb3-rf3", **CFG[key]))
    pct = float(row[3].replace("−", "-").replace("%", ""))
    base = med(rr, run_note="tidb3-rf1", **CFG[key])
    check(f"R {row[0]} thay đổi %", pct, 100 * (med(rr, run_note="tidb3-rf3", **CFG[key]) - base) / base, tol=0.02)
    p1, p3 = [vn(x) for x in row[4].split("→")]
    check(f"R {row[0]} p99 rf=1", p1, med(rr, "p99_ms", run_note="tidb3-rf1", **CFG[key]))
    check(f"R {row[0]} p99 rf=3", p3, med(rr, "p99_ms", run_note="tidb3-rf3", **CFG[key]))

# Nhóm R2 (ba pha)
r2 = rows(R23 / "tidb3-R2")
for row in section_table(DOC23, "## Nhóm R2: kiểm soát thứ tự", 0):
    key = "A" if row[0].startswith("A:") else "B" if row[0].startswith("B:") else next((k for k in CFG if k in row[0]), None)
    if key is None:
        continue
    for col, note in ((1, "tidb3-ph1-rf3"), (2, "tidb3-ph2-rf1"), (3, "tidb3-ph3-rf3")):
        tps, p99 = cell(row[col])
        check(f"R2 {row[0]} {note} TPS", tps, med(r2, run_note=note, **CFG[key]))
        check(f"R2 {row[0]} {note} p99", p99, med(r2, "p99_ms", run_note=note, **CFG[key]))

# Fault injection: bảng so với JSON
files = {("TiDB", "thường, tồn 30"): "tidb-kill-stockout", ("TiDB", "thường, tồn 2.000"): "tidb-kill-orders",
         ("TiDB", "đối chứng âm"): "tidb-kill-idempotency-off", ("MySQL", "thường"): "mysql-kill",
         ("MySQL", "đối chứng âm"): "mysql-kill-idempotency-off", ("MongoDB (a)", "thường"): "mongo-kill",
         ("MongoDB (a)", "đối chứng âm"): "mongo-kill-idempotency-off"}
for row in section_table(DOCFI, "Kết quả (`results/official/fault-injection", 0):
    name = next((v for (h, m), v in files.items() if row[0] == h and row[1].startswith(m)), None)
    if name is None:
        continue
    r = json.loads((FI / f"{name}.json").read_text(encoding="utf-8"))
    check(f"FI {name} yêu cầu", vn(row[2]), r["requests"])
    check(f"FI {name} lần giết", vn(row[3]), r["kills"])
    check(f"FI {name} trúng cửa sổ commit", vn(row[4]), r["rerun_found_committed"])
    if row[5] != "—":
        check(f"FI {name} chết trước commit", vn(row[5]), r["rerun_not_committed"])
    orders = [vn(x) for x in row[6].split("/")]
    check(f"FI {name} đơn DB", orders[0], r["orders_committed_in_db"])
    check(f"FI {name} đơn ack", orders[1], r["orders_acked_success"])
    if row[7] != "—":
        pay = [vn(x) for x in row[7].split("/")]
        check(f"FI {name} payment DB", pay[0], r["payments_in_db"])
        check(f"FI {name} payment ack", pay[1], r["payments_acked_success"])

print(f"Đã đối chiếu {checked} ô; lệch/thiếu: {bad}")
sys.exit(1 if bad else 0)
