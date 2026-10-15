"""裁决记录的合并与整理。"""
import collections
import json
from pathlib import Path

DOMAINS = ("collab", "tech", "product", "aesthetics")


def load_records(files):
    recs = []
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def merge_into(all_path, new_recs):
    """把新记录追加进累积文件。id 已存在且内容相同则跳过；内容不同则报错，不静默覆盖。

    返回 (新增条数, 跳过条数)。
    """
    all_path = Path(all_path)
    existing = {}
    if all_path.exists():
        for line in all_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                existing[r["id"]] = r
    clash = [r["id"] for r in new_recs if r["id"] in existing and existing[r["id"]] != r]
    if clash:
        raise SystemExit(f"这些 id 已存在且内容不同，先改名再合并：{', '.join(clash[:10])}")
    added = [r for r in new_recs if r["id"] not in existing]
    with open(all_path, "a", encoding="utf-8") as fh:
        for r in added:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(added), len(new_recs) - len(added)


def axes_report(recs):
    """把记录压成「权衡轴清单」：只列 轴 / 领域 / 可迁移性 / 置信度 / 出处，供归纳时通览。

    不含原话和情境——归纳阶段看的是「在哪条轴上做了取舍」，全文需要时再按 id 回查。
    """
    out = [f"# 权衡轴清单（{len(recs)} 条）\n"]
    for dom in DOMAINS:
        sub = [r for r in recs if r.get("domain") == dom]
        out.append(f"\n## {dom}  ({len(sub)} 条)\n")
        for r in sorted(sub, key=lambda x: (x.get("reusable") is not True, x.get("date", ""))):
            ax = (r.get("axis") or "").strip() or "（无轴）"
            flag = "" if r.get("reusable") is True else " [不可迁移]"
            cf = {"high": "", "medium": "~", "low": "?"}.get(r.get("confidence"), "")
            note = " [归属偏差]" if r.get("src_note") else ""
            out.append(f"- `{r.get('id')}` {cf}{ax}{flag}{note}  · {r.get('date')} {r.get('proj')}")
    return "\n".join(out)


def summary(recs):
    c = collections.Counter
    return {
        "domain": dict(c(r.get("domain") for r in recs)),
        "reusable": sum(1 for r in recs if r.get("reusable") is True),
        "confidence": dict(c(r.get("confidence") for r in recs)),
        "no_axis": sum(1 for r in recs if not (r.get("axis") or "").strip()),
    }
