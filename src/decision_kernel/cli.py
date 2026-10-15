"""命令行入口：dk <子命令>。机械步骤都在这里，需要判断的步骤交给 Claude（见 claude/commands/）。"""
import argparse
import collections
import datetime
import json
import os
import re
import shutil
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from . import evidence as EV
from . import records as RC
from . import scan as SC
from . import verify as VF
from .workbench import Workbench

TEMPLATES = ("EXTRACT_GUIDE.md", "MOTIVE_GUIDE.md", "watchlist.md")
FINISHED = ".finished"          # incr/ 里的完成标记，内容是 finish 的日期


def _out(msg=""):
    print(msg)


def cmd_init(args):
    wb = Workbench(args.dir or args.workbench)
    wb.root.mkdir(parents=True, exist_ok=True)
    created = []
    for name in TEMPLATES:
        dst = wb.path(name)
        if not dst.exists():
            dst.write_text(resources.files("decision_kernel.templates").joinpath(name)
                           .read_text(encoding="utf-8"), encoding="utf-8")
            created.append(name)
    for name in ("all_records.jsonl", "motives.jsonl", "kernel_map.jsonl"):
        dst = wb.path(name)
        if not dst.exists():
            dst.touch()
            created.append(name)
    _out(f"工作目录：{wb.root}")
    _out(f"新建：{', '.join(created) if created else '（都已存在，未改动）'}")
    if wb.root != Workbench().root:
        _out(f"提示：后续命令加 --workbench {wb.root}，或 export DK_WORKBENCH={wb.root}")


def _archive_run(wb, redo=False):
    """开新一轮前处理上一轮的 incr/：已 finish 的归档为 incr-<日期>/；
    没 finish 的默认拒绝（里面可能有抽取到一半的成果），--redo 时挪到 incr-abandoned-<时刻>/，不删除。"""
    if not wb.run.exists():
        return None
    if (wb.run / FINISHED).exists():
        dst = wb.path(f"incr-{(wb.run / FINISHED).read_text(encoding='utf-8').strip()}")
    elif redo:
        dst = wb.path(f"incr-abandoned-{datetime.datetime.now():%Y%m%d-%H%M%S}")
    else:
        raise SystemExit("incr/ 是还没 finish 的本轮工作目录，可能有抽取到一半的成果。\n"
                         "要放弃它重扫，加 --redo（会挪到 incr-abandoned-<时刻>/，不删除）。")
    if dst.exists():
        raise SystemExit(f"{dst} 已存在，请先人工处理")
    wb.run.rename(dst)
    return dst


def cmd_scan(args):
    wb = Workbench(args.workbench).require()
    since = None if args.all else (args.since or wb.last_run())
    claude_dir = os.path.expanduser(args.claude_dir)
    archived = _archive_run(wb, args.redo)
    if archived:
        _out(f"上一轮工作目录已移到 {archived.name}/")
    wb.run.mkdir()

    s_frags, s_stats = SC.scan_sessions(claude_dir, since)
    h_frags, h_stats = ([], collections.Counter()) if args.no_history \
        else SC.scan_history(claude_dir, s_frags, since)
    SC.write_jsonl(wb.run / "corpus.jsonl", s_frags)
    SC.write_jsonl(wb.run / "corpus_history.jsonl", h_frags)
    allf = s_frags + h_frags
    SC.write_jsonl(wb.run / "corpus_all.jsonl", allf)

    chars = sum(len(json.dumps(f, ensure_ascii=False)) for f in allf)
    _out(f"范围：{since + ' 起' if since else '全部记录'}（{claude_dir}）")
    _out(f"会话日志 {s_stats['files']} 个 → A {s_stats['A']} / B {s_stats['B']} / "
         f"C {s_stats['C']} / D {s_stats['D']}")
    _out(f"输入历史 {h_stats['inputs']} 条 → E-meta {h_stats['E-meta']} / E-fix {h_stats['E-fix']}"
         f"（与会话源重复丢弃 {h_stats['dup']}）")
    _out(f"合计 {len(allf)} 片段，{chars:,} 字符 → {wb.run / 'corpus_all.jsonl'}")
    by_proj = collections.Counter(f["proj"] for f in allf)
    if by_proj:
        _out("--- 按项目 ---")
        for p, n in by_proj.most_common(15):
            _out(f"{n:5d}  {p}")
    if len(allf) < args.min_fragments:
        _out(f"\n片段少于 {args.min_fragments} 条，增量太少，不值得复盘。")


def _next_prefix(all_path):
    """挑一个累积记录里还没用过的单字母作批次前缀，免得新一轮的 id 与历史撞号。"""
    used = set()
    if all_path.exists():
        for line in all_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = re.match(r"([A-Za-z]+)\d*-", json.loads(line).get("id", ""))
                if m:
                    used.add(m.group(1))
    singles = sorted(u for u in used if len(u) == 1 and u.isupper())
    start = ord(singles[-1]) + 1 if singles else ord("J")
    for c in list(range(start, ord("Z") + 1)) + list(range(ord("A"), start)):
        if chr(c) not in used:
            return chr(c)
    raise SystemExit("A–Z 都已用作前缀，请用 --prefix 指定")


def cmd_batch(args):
    wb = Workbench(args.workbench).require()
    corpus = SC.read_jsonl(wb.run / "corpus_all.jsonl")
    if not args.prefix:
        args.prefix = _next_prefix(wb.path("all_records.jsonl"))
    bdir = wb.run / "batches"
    if bdir.exists():
        shutil.rmtree(bdir)
    bdir.mkdir()
    n = 0
    for i in range(0, len(corpus), args.size):
        n += 1
        SC.write_jsonl(bdir / f"{args.prefix}{n}.jsonl", corpus[i:i + args.size])
    (wb.run / "extracted").mkdir(exist_ok=True)
    _out(f"{len(corpus)} 片段 → {n} 批（每批 ≤{args.size}）→ {bdir}/")
    _out(f"每批交给一个 subagent，按 {wb.path('EXTRACT_GUIDE.md')} 抽取，"
         f"产物写 {wb.run / 'extracted'}/records_<批次名>.jsonl，id 以批次名为前缀。")


def _record_files(wb, given):
    if given:
        files = []
        for g in given:
            p = Path(g)
            files += sorted(p.glob("*.jsonl")) if p.is_dir() else [p]
        return files
    return sorted((wb.run / "extracted").glob("*.jsonl"))


def cmd_verify(args):
    wb = Workbench(args.workbench).require()
    corpus = Path(args.corpus) if args.corpus else wb.run / "corpus_all.jsonl"
    files = _record_files(wb, args.records)
    if not files:
        raise SystemExit("没找到裁决记录文件（默认读 incr/extracted/*.jsonl）")
    results, issues = VF.verify(corpus, files)
    total = sum(results.values()) or 1
    _out(f"校验 {sum(results.values())} 条原话")
    for k, n in results.most_common():
        flag = "" if k.startswith("OK") or k == "EMPTY" else "  ← 需处理"
        _out(f"  {k:14} {n:5d}  ({n / total * 100:5.1f}%){flag}")
    if issues:
        _out(f"\n--- 问题条目（前 25 / 共 {len(issues)}）---")
        for p, i, v, t in issues[:25]:
            _out(f"  {v:12} {p}:{i}  {t}")
        tsv = corpus.parent / "verbatim_issues.tsv"
        with open(tsv, "w", encoding="utf-8") as fh:
            for p, i, v, t in issues:
                fh.write(f"{p}\t{i}\t{v}\t{t}\n")
        _out(f"\n全量问题清单 → {tsv}")
        sys.exit(1)


def cmd_axes(args):
    wb = Workbench(args.workbench).require()
    recs = RC.load_records(_record_files(wb, args.records))
    out = wb.run / "axes.md"
    out.write_text(RC.axes_report(recs), encoding="utf-8")
    s = RC.summary(recs)
    _out(f"{len(recs)} 条记录 → {out}")
    _out(f"domain {s['domain']} · 可迁移 {s['reusable']} · 置信度 {s['confidence']} · 无轴 {s['no_axis']}")


def _append_unique(path, rows):
    """逐行追加到 jsonl，完全相同的行不重复写。返回新增条数。"""
    have = set()
    if path.exists():
        have = {l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
    added = 0
    with open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            line = json.dumps(r, ensure_ascii=False)
            if line not in have:
                fh.write(line + "\n")
                have.add(line)
                added += 1
    return added


def cmd_merge(args):
    wb = Workbench(args.workbench).require()
    recs = RC.load_records(_record_files(wb, args.records))
    added, skipped = RC.merge_into(wb.path("all_records.jsonl"), recs)
    _out(f"裁决记录：新增 {added}，已存在跳过 {skipped} → all_records.jsonl")
    for name in ("motives.jsonl", "kernel_map.jsonl"):
        src = wb.run / name
        if src.exists():
            n = _append_unique(wb.path(name), SC.read_jsonl(src))
            _out(f"{name}：新增 {n}")


def cmd_evidence(args):
    wb = Workbench(args.workbench).require()
    kernel = Path(args.kernel).expanduser()
    if not kernel.exists():
        raise SystemExit(f"内核文件不存在：{kernel}")
    text, st = EV.build(kernel.read_text(encoding="utf-8"), wb.path("kernel_map.jsonl"),
                        wb.path("all_records.jsonl"), wb.path("motives.jsonl"),
                        kernel_ref=f"`{args.kernel}`")
    wb.path("evidence-map.md").write_text(text, encoding="utf-8")
    _out(f"evidence-map.md：{st['kernels']} 条内核 · 引用裁决 {st['cited']} 条（全库 {st['records']}）"
         f" · 动机 {st['motives']} 条")
    if st["missing"]:
        _out(f"⚠ kernel_map 引用了不存在的记录：{' '.join(st['missing'][:20])}")
    if st["unknown_kernels"]:
        _out(f"⚠ kernel_map 里有内核文件中没有的编号：{' '.join(st['unknown_kernels'])}")
    if st["missing"] or st["unknown_kernels"]:
        sys.exit(1)


def cmd_finish(args):
    wb = Workbench(args.workbench).require()
    day = args.date or datetime.date.today().isoformat()
    wb.last_run_file.write_text(day + "\n", encoding="utf-8")
    if wb.run.exists():
        (wb.run / FINISHED).write_text(day + "\n", encoding="utf-8")
    _out(f"last-run = {day}（下次 scan 从这天开始，本轮 incr/ 届时归档为 incr-{day}/）")


def cmd_status(args):
    wb = Workbench(args.workbench)
    _out(f"工作目录：{wb.root}{'' if wb.root.is_dir() else '（不存在，先 dk init）'}")
    if not wb.root.is_dir():
        return

    def count(p):
        return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip()) if p.exists() else 0
    _out(f"上次复盘：{wb.last_run() or '从未'}")
    _out(f"裁决记录 {count(wb.path('all_records.jsonl'))} · 动机 {count(wb.path('motives.jsonl'))}"
         f" · 内核映射 {count(wb.path('kernel_map.jsonl'))}")
    if wb.run.exists():
        ext = sorted((wb.run / "extracted").glob("*.jsonl")) if (wb.run / "extracted").exists() else []
        _out(f"本轮 incr/：片段 {count(wb.run / 'corpus_all.jsonl')} · 已抽取文件 {len(ext)}")
    arch = sorted(p.name for p in wb.root.glob("incr-*"))
    if arch:
        _out(f"历次归档：{' '.join(arch)}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dk", description="从 Claude Code 会话记录蒸馏个人决策内核")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--workbench", "-w", help="工作目录（默认 $DK_WORKBENCH 或 ~/.decision-kernel）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="建工作目录并放入抽取规范等模板")
    p.add_argument("dir", nargs="?")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("scan", help="从会话日志和输入历史硬筛决策片段 → incr/corpus_all.jsonl")
    p.add_argument("--since", help="只取该日（YYYY-MM-DD）及之后；默认取 last-run")
    p.add_argument("--all", action="store_true", help="忽略 last-run，扫全部记录（首次蒸馏用）")
    p.add_argument("--claude-dir", default="~/.claude", help="Claude Code 数据目录（默认 ~/.claude）")
    p.add_argument("--no-history", action="store_true", help="不扫 history.jsonl")
    p.add_argument("--redo", action="store_true", help="放弃没 finish 的本轮 incr/ 重扫（挪走，不删除）")
    p.add_argument("--min-fragments", type=int, default=30, help="少于此数提示不值得复盘")
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("batch", help="把本轮片段切成批次，供多个 subagent 并行抽取")
    p.add_argument("--size", type=int, default=150)
    p.add_argument("--prefix", help="批次名前缀，也是记录 id 前缀（默认自动取历史记录没用过的字母）")
    p.set_defaults(fn=cmd_batch)

    p = sub.add_parser("verify", help="原话校验：裁决记录的 verbatim 必须能在用户侧原文里找到")
    p.add_argument("--corpus", help="语料文件（默认 incr/corpus_all.jsonl）")
    p.add_argument("--records", nargs="*", help="记录文件或目录（默认 incr/extracted/）")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("axes", help="生成权衡轴清单 incr/axes.md，供归纳时通览")
    p.add_argument("--records", nargs="*")
    p.set_defaults(fn=cmd_axes)

    p = sub.add_parser("merge", help="把本轮记录、动机、内核映射并入累积文件")
    p.add_argument("--records", nargs="*")
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("evidence", help="生成 evidence-map.md 证据溯源表")
    p.add_argument("--kernel", required=True, help="内核文件路径（读取 ## K<n> · 名称 标题）")
    p.set_defaults(fn=cmd_evidence)

    p = sub.add_parser("finish", help="记录本次复盘日期，作为下次 scan 的起点")
    p.add_argument("--date", help="默认今天")
    p.set_defaults(fn=cmd_finish)

    p = sub.add_parser("status", help="查看工作目录状态")
    p.set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    args.fn(args)
