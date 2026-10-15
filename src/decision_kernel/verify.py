"""原话校验：每条裁决记录的 verbatim 必须能在语料的**用户侧文本**里原样找到。

这是整条流水线的反幻觉闸门。下游会拿 verbatim 当「用户原话」给内核背书，
一旦掺进 Claude 的转述、或把上一轮的话张冠李戴，错误就会被当成用户的原则长期固化。

判定：
  OK / OK-elided / OK-otherSess / OK-prev-noted   通过
  PREV      只在 prev_user 里找到（那是上一轮的话，不是本条）
  CLAUDE    只在 Claude 侧字段里找到（最严重：把 Claude 的话当成了用户的）
  PARTIAL   只有最长的一段能找到（多半是跨片段拼接）
  MISSING   哪儿都找不到（改写、润色或编造）
  BADJSON   记录本身不是合法 JSON
"""
import collections
import json
import re
from pathlib import Path

USER_FIELDS = ("user_msg", "user_reply", "answer", "follow")
CLAUDE_FIELDS = ("claude_ask", "claude_ctx")


def norm(s):
    """去空白，统一全半角标点和引号，避免排版差异被判成改写。"""
    s = re.sub(r"\s+", "", s or "")
    for a, b in ((",", "，"), ("!", "！"), ("?", "？"), (":", "："), (";", "；"),
                 ("(", "（"), (")", "）"), ("~", "～")):
        s = s.replace(a, b)
    return re.sub(r"[“”„‟\"'‘’`´]", '"', s)


def _haystacks(frag):
    def as_text(v):
        return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    u = " ".join(norm(as_text(frag[k])) for k in USER_FIELDS if frag.get(k))
    a = " ".join(norm(frag.get(k, "")) for k in CLAUDE_FIELDS if frag.get(k))
    return u, a, norm(frag.get("prev_user", ""))


def _verdict(r, corpus, by_sess, index):
    v = norm(r.get("verbatim", ""))
    if len(v) < 4:
        return "EMPTY"
    # 省略号拼接的摘录：拆段分别验，全部命中才算通过（是摘录，不是编造）
    parts = [x for x in re.split(r"\.{2,}|…+|。。。+", v) if len(x) >= 4]
    elided = len(parts) > 1
    probe = parts if elided else [v]

    def hit(hay):
        return all(x in hay for x in probe)

    verdict = "MISSING"
    for c in by_sess.get(r.get("sess", ""), []) or corpus:     # 优先同会话，找不到再全局
        u, a, p = index[id(c)]
        if hit(u):
            return "OK-elided" if elided else "OK"
        if hit(p) and verdict == "MISSING":
            verdict = "OK-prev-noted" if r.get("src_note") else "PREV"
        if hit(a) and verdict == "MISSING":
            verdict = "CLAUDE"
    if verdict != "MISSING":
        return verdict
    for c in corpus:
        if hit(index[id(c)][0]):
            return "OK-otherSess"
    longest = max(probe, key=len)          # 退一步只验最长的一段，区分「改写」与「跨片段拼接」
    for c in corpus:
        if longest in index[id(c)][0]:
            return "PARTIAL"
    return "MISSING"


def verify(corpus_path, record_files):
    """返回 (各判定计数, 问题条目列表[(文件, 行号, 判定, 原话前 90 字)])。"""
    corpus = [json.loads(l) for l in Path(corpus_path).read_text(encoding="utf-8").splitlines() if l.strip()]
    by_sess = collections.defaultdict(list)
    for c in corpus:
        by_sess[c["sess"]].append(c)
    index = {id(c): _haystacks(c) for c in corpus}

    results, issues = collections.Counter(), []
    for path in record_files:
        path = Path(path)
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                results["BADJSON"] += 1
                issues.append((path.name, i, "BADJSON", line[:80]))
                continue
            verdict = _verdict(r, corpus, by_sess, index)
            if verdict == "EMPTY":
                results[verdict] += 1
                continue
            results[verdict] += 1
            if not verdict.startswith("OK"):
                issues.append((path.name, i, verdict, r.get("verbatim", "")[:90]))
    return results, issues
