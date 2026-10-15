"""语料硬筛：从 Claude Code 的本地记录里挑出「决策片段」。纯规则，零 LLM。

两个来源：
- 会话日志 <claude-dir>/projects/**/*.jsonl：对话完整，产出 A / B / C / D 四类
    A  AskUserQuestion 问答对（问题 + 选项 + 说明 + 用户答案 + 紧邻的补充）
    B  真·问答对（Claude 末尾确实在征询 → 用户的简短回答）
    C  反应型裁决（针对 Claude 刚提出的东西认可 / 否决 / 纠偏）
    D  协作元反馈（用户直接规定 Claude 该怎么工作，价值最高）
- 输入历史 <claude-dir>/history.jsonl：只有用户侧、没有 Claude 回复，但保留得更久，产出
    E-meta  协作元反馈（不依赖上下文，完全可用）
    E-fix   强纠正 / 否决（只有同会话上一条输入做弱上下文）

两源按「正文前 120 字」指纹去重。每条片段带 项目 / 会话 / 行号 / 日期，作为证据链地址。
"""
import collections
import datetime
import glob
import hashlib
import json
import os

from . import filters as F


def _proj_name(path, recs):
    """优先用会话记录里的 cwd 取末段作项目名（目录名会把中文吞成 -）。"""
    for _, o in recs[:80]:
        cwd = o.get("cwd")
        if cwd:
            return os.path.basename(cwd.rstrip("/")) or cwd
    return os.path.basename(os.path.dirname(path)).lstrip("-").replace("-", "/")


def scan_sessions(claude_dir, since=None):
    """扫会话日志，返回 (片段列表, 统计)。since 为 YYYY-MM-DD，只保留该日及之后的消息。"""
    root = os.path.join(claude_dir, "projects")
    frags, seen = [], set()
    stats = collections.Counter()

    paths = [p for p in glob.glob(root + "/**/*.jsonl", recursive=True) if "/subagents/" not in p]
    for path in sorted(paths):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        stats["files"] += 1
        recs = []
        for i, line in enumerate(lines):
            try:
                recs.append((i, json.loads(line)))
            except ValueError:
                continue
        proj, sess = _proj_name(path, recs), os.path.basename(path)[:8]
        askq, last_asst = {}, None

        for idx, (ln, o) in enumerate(recs):
            typ, msg = o.get("type"), (o.get("message") or {})
            ts = (o.get("timestamp") or "")[:10]
            if since and ts and ts < since:
                continue

            if typ == "assistant":
                for b in (msg.get("content") or []):
                    if isinstance(b, dict) and b.get("type") == "tool_use" \
                            and b.get("name") == "AskUserQuestion":
                        askq[b["id"]] = (ln, b.get("input"), ts)
                t = F.text_of(msg.get("content")).strip()
                if t:
                    last_asst = (ln, t, ts)
                continue
            if typ != "user":
                continue

            c = msg.get("content")
            # A：AskUserQuestion 的回答以 tool_result 形式回来
            if isinstance(c, list):
                for b in c:
                    if not (isinstance(b, dict) and b.get("type") == "tool_result"
                            and b.get("tool_use_id") in askq):
                        continue
                    aln, ainput, ats = askq[b["tool_use_id"]]
                    ans = b.get("content")
                    if isinstance(ans, list):
                        ans = " ".join(x.get("text", "") for x in ans if isinstance(x, dict))
                    follow = ""
                    for j in range(idx + 1, min(idx + 4, len(recs))):
                        _, o2 = recs[j]
                        if o2.get("type") == "user":
                            s2 = F.strip_noise(F.text_of((o2.get("message") or {}).get("content")))
                            if F.is_real_user_text(s2):
                                follow = s2[:600]
                                break
                        if o2.get("type") == "assistant" and \
                                F.text_of((o2.get("message") or {}).get("content")).strip():
                            break
                    frags.append({"kind": "A", "proj": proj, "sess": sess, "line": aln,
                                  "date": ats or ts, "ask": ainput,
                                  "answer": str(ans)[:2000], "follow": follow})
                    stats["A"] += 1

            # B / C / D
            s = F.strip_noise(F.text_of(c))
            if not F.is_real_user_text(s):
                continue
            key = hashlib.md5((sess + s[:200]).encode()).hexdigest()
            if key in seen:
                continue
            ctx = last_asst[1] if (last_asst and last_asst[0] < ln) else ""
            # 征询判定只看 Claude 末尾 200 字，避免被长篇汇报里的措辞误命中
            soliciting = bool(ctx and F.RE_ASK_TAIL.search(ctx[-200:]))

            if F.RE_META.search(s):            # D 优先：元反馈不依赖上下文，长度也不设限
                seen.add(key)
                frags.append({"kind": "D", "proj": proj, "sess": sess, "line": ln,
                              "date": ts, "claude_ctx": ctx[-350:], "user_msg": s[:1500]})
                stats["D"] += 1
            elif soliciting and len(s) < 400:
                seen.add(key)
                frags.append({"kind": "B", "proj": proj, "sess": sess, "line": ln,
                              "date": ts, "claude_ask": ctx[-600:], "user_reply": s})
                stats["B"] += 1
            elif ctx and len(s) < 250 and F.RE_REACT.search(s):
                seen.add(key)
                frags.append({"kind": "C", "proj": proj, "sess": sess, "line": ln,
                              "date": ts, "claude_ctx": ctx[-350:], "user_msg": s})
                stats["C"] += 1
    return frags, stats


def _fingerprint(text):
    return hashlib.md5(text.strip()[:120].encode()).hexdigest()


def scan_history(claude_dir, existing, since=None):
    """扫 history.jsonl，返回 (片段列表, 统计)。existing 为会话源已有片段，用于去重。"""
    hist = os.path.join(claude_dir, "history.jsonl")
    stats = collections.Counter()
    if not os.path.exists(hist):
        return [], stats

    seen = set()
    for f in existing:
        body = f.get("user_msg") or f.get("user_reply") or f.get("follow") or ""
        if body:
            seen.add(_fingerprint(body))

    rows = []
    with open(hist, encoding="utf-8") as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    rows.sort(key=lambda r: r.get("timestamp", 0))
    stats["inputs"] = len(rows)

    prev_in_sess, frags = {}, []
    for r in rows:
        s = (r.get("display") or "").strip()
        sid = r.get("sessionId", "")
        ts = r.get("timestamp", 0)
        date = datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else ""
        if since and date and date < since:
            continue
        proj = os.path.basename((r.get("project") or "").rstrip("/")) or "?"
        prev = prev_in_sess.get(sid, "")          # 同会话上一条输入 = 弱上下文
        prev_in_sess[sid] = s[:200]

        if not F.usable_history_input(s):
            continue
        fp = _fingerprint(s)
        if fp in seen:
            stats["dup"] += 1
            continue
        if F.RE_META.search(s):
            kind = "E-meta"
        elif len(s) < 600 and F.RE_STRONG_FIX.search(s):
            kind = "E-fix"
        else:
            continue
        seen.add(fp)
        frags.append({"kind": kind, "proj": proj, "sess": sid[:8], "line": -1,
                      "date": date, "prev_user": prev, "user_msg": s[:1500],
                      "src": "history.jsonl"})
        stats[kind] += 1
    return frags, stats


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]
