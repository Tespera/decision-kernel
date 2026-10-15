"""证据溯源表：每条内核由哪些裁决记录、哪些动机陈述支撑。

内核正文刻意不含原话和项目名（它要能被任何项目直接引用），所以「这条凭什么成立」
只能回到这张表查。输入：
- 内核文件：从「## K1 · 名称」这样的二级标题读出内核编号与名称
- kernel_map.jsonl：{"id": 裁决记录 id, "kernel": "K1"}，一行一条，顺序即展示顺序
- all_records.jsonl / motives.jsonl：motives 每条带 "kernel" 字段
"""
import json
import re

RE_KERNEL = re.compile(r"^##\s+(K\d+)\s*(?:[·:：\-—]\s*)?(.*?)\s*$")


def kernel_names(kernel_text):
    """返回 [(编号, 名称)]，按内核文件里出现的顺序。"""
    out = []
    for line in kernel_text.splitlines():
        m = RE_KERNEL.match(line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def build(kernel_text, kernel_map_path, records_path, motives_path, kernel_ref="内核文件"):
    """返回 (markdown 文本, 统计)。kernel_map 里引用了不存在的记录 id 会计入统计的 missing。"""
    kernels = kernel_names(kernel_text)
    recs = {r["id"]: r for r in _jsonl(records_path)}
    mots = _jsonl(motives_path) if motives_path and motives_path.exists() else []
    by_kernel = {}
    for x in _jsonl(kernel_map_path):
        by_kernel.setdefault(x["kernel"], []).append(x["id"])

    out = ["# 决策内核 · 证据溯源", "",
           f"> 内部文件，不进交付物。内核正文（{kernel_ref}）不含原话与项目名；",
           "> 将来质疑某条内核凭什么成立，从这里回查 `all_records.jsonl`（裁决记录）和 `motives.jsonl`（动机陈述）。",
           ""]
    cited, missing = set(), []
    for kid, name in kernels:
        ids = list(dict.fromkeys(by_kernel.get(kid, [])))
        missing += [i for i in ids if i not in recs]
        ev = [recs[i] for i in ids if i in recs]
        cited |= set(ids)
        projs = sorted({e["proj"] for e in ev})
        dates = sorted(e["date"] for e in ev)
        ms = [m for m in mots if m.get("kernel") == kid]
        out += [f"## {kid} {name}".rstrip(),
                f"- 裁决记录 **{len(ev)}** 条 · 项目 {len(projs)} 个 · "
                f"{dates[0] if dates else '?'} ~ {dates[-1] if dates else '?'}",
                f"- 动机陈述 **{len(ms)}** 条（explicit {sum(1 for m in ms if m.get('strength') == 'explicit')}）",
                f"- 项目：{'、'.join(projs)}",
                f"- 裁决 id：{' '.join(ids)}"]
        if ms:
            out.append("- 动机摘要：")
            out += [f"  - [{m.get('src', '')}] {m.get('motive', '')}" for m in ms[:6]]
            if len(ms) > 6:
                out.append(f"  - …另 {len(ms) - 6} 条见 motives.jsonl")
        out.append("")
    unknown = sorted(set(by_kernel) - {k for k, _ in kernels})
    out.append(f"---\n合计引用裁决记录 {len(cited)} 条（全库 {len(recs)}）、动机陈述 {len(mots)} 条。")
    stats = {"kernels": len(kernels), "cited": len(cited), "records": len(recs),
             "motives": len(mots), "missing": missing, "unknown_kernels": unknown}
    return "\n".join(out), stats
