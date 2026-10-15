import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from decision_kernel import cli, evidence, records, scan, verify

FIXTURE = Path(__file__).parent / "fixtures" / "claude"


def jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def run_cli(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cli.main(list(argv))
    return buf.getvalue()


class ScanTest(unittest.TestCase):
    def test_sessions_classify_each_kind(self):
        frags, stats = scan.scan_sessions(str(FIXTURE))
        kinds = {f["kind"]: f for f in frags}
        self.assertEqual(stats["A"], 1)
        self.assertEqual(kinds["A"]["answer"], "Excel")
        self.assertEqual(kinds["A"]["follow"], "只要 Excel 就行，别弹设置框")
        self.assertEqual(kinds["B"]["user_reply"], "先保留，等下周再说")
        self.assertIn("要不要", kinds["B"]["claude_ask"])
        self.assertEqual(kinds["C"]["user_msg"], "不对，没让你改样式")
        self.assertEqual(kinds["A"]["proj"], "demo")

    def test_injected_text_is_never_user_text(self):
        frags, _ = scan.scan_sessions(str(FIXTURE))
        blob = json.dumps(frags, ensure_ascii=False)
        self.assertNotIn("注入的提醒", blob)
        self.assertNotIn("session is being continued", blob)

    def test_since_filters_old_messages(self):
        frags, _ = scan.scan_sessions(str(FIXTURE), since="2026-09-01")
        self.assertNotIn("以后先跑测试再提交", [f.get("user_msg") for f in frags])

    def test_history_dedupes_against_sessions_and_drops_noise(self):
        s_frags, _ = scan.scan_sessions(str(FIXTURE))
        h_frags, stats = scan.scan_history(str(FIXTURE), s_frags)
        msgs = [f["user_msg"] for f in h_frags]
        self.assertEqual(stats["dup"], 1)
        self.assertNotIn("以后这种小事直接做，不用问我", msgs)
        self.assertNotIn("/clear", msgs)
        self.assertNotIn("继续", msgs)
        self.assertEqual({f["kind"] for f in h_frags}, {"E-meta", "E-fix"})
        fix = next(f for f in h_frags if f["kind"] == "E-fix")
        self.assertEqual(fix["prev_user"], "每次都要我提醒，下次记住先备份")


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.corpus = self.tmp / "corpus.jsonl"
        jsonl(self.corpus, [
            {"kind": "C", "sess": "s1", "claude_ctx": "我顺手把样式也重做了",
             "user_msg": "不对，没让你改样式。下次只改我说的那一处"},
            {"kind": "E-fix", "sess": "s2", "prev_user": "先别动数据库",
             "user_msg": "怎么又改了表结构"},
        ])

    def check(self, verbatim, **extra):
        rec = self.tmp / "r.jsonl"
        jsonl(rec, [{"id": "J1-001", "sess": extra.pop("sess", "s1"), "verbatim": verbatim, **extra}])
        results, _ = verify.verify(self.corpus, [rec])
        return next(iter(results))

    def test_exact_quote_passes_despite_spacing_and_punctuation(self):
        self.assertEqual(self.check("不对,没让你改样式"), "OK")

    def test_elided_quote_needs_every_part(self):
        self.assertEqual(self.check("不对，没让你改样式…只改我说的那一处"), "OK-elided")
        self.assertEqual(self.check("不对，没让你改样式…顺便改下颜色"), "PARTIAL")

    def test_claude_words_are_caught(self):
        self.assertEqual(self.check("我顺手把样式也重做了"), "CLAUDE")

    def test_previous_turn_is_caught_unless_noted(self):
        self.assertEqual(self.check("先别动数据库", sess="s2"), "PREV")
        self.assertEqual(self.check("先别动数据库", sess="s2", src_note="出自上一条输入"), "OK-prev-noted")

    def test_paraphrase_is_missing(self):
        self.assertEqual(self.check("你不要擅自修改界面样式"), "MISSING")

    def test_bad_json_is_reported(self):
        rec = self.tmp / "bad.jsonl"
        rec.write_text("{not json\n", encoding="utf-8")
        results, issues = verify.verify(self.corpus, [rec])
        self.assertEqual(results["BADJSON"], 1)
        self.assertEqual(issues[0][2], "BADJSON")


class RecordsTest(unittest.TestCase):
    def test_merge_skips_identical_and_refuses_conflicts(self):
        tmp = Path(tempfile.mkdtemp())
        allp = tmp / "all.jsonl"
        a = {"id": "J1-001", "verbatim": "x"}
        self.assertEqual(records.merge_into(allp, [a]), (1, 0))
        self.assertEqual(records.merge_into(allp, [a]), (0, 1))
        with self.assertRaises(SystemExit):
            records.merge_into(allp, [{"id": "J1-001", "verbatim": "y"}])


class EvidenceTest(unittest.TestCase):
    def test_build_groups_by_kernel_and_reports_gaps(self):
        tmp = Path(tempfile.mkdtemp())
        jsonl(tmp / "all.jsonl", [
            {"id": "J1-001", "proj": "demo", "date": "2026-09-01"},
            {"id": "J1-002", "proj": "other", "date": "2026-09-03"},
        ])
        jsonl(tmp / "km.jsonl", [
            {"id": "J1-001", "kernel": "K1"}, {"id": "J1-002", "kernel": "K1"},
            {"id": "J9-999", "kernel": "K2"}, {"id": "J1-001", "kernel": "K7"},
        ])
        jsonl(tmp / "mot.jsonl", [{"kernel": "K1", "motive": "m", "src": "s", "strength": "explicit"}])
        kernel = "# 内核\n\n## K1 · 要最佳解\n正文\n## K2 · 前提要硬\n"
        text, st = evidence.build(kernel, tmp / "km.jsonl", tmp / "all.jsonl", tmp / "mot.jsonl")
        self.assertIn("## K1 要最佳解", text)
        self.assertIn("裁决记录 **2** 条 · 项目 2 个 · 2026-09-01 ~ 2026-09-03", text)
        self.assertIn("动机陈述 **1** 条（explicit 1）", text)
        self.assertEqual(st["missing"], ["J9-999"])
        self.assertEqual(st["unknown_kernels"], ["K7"])


class CliTest(unittest.TestCase):
    def test_round_trip_archives_previous_run(self):
        wb = Path(tempfile.mkdtemp()) / "wb"
        run_cli("init", str(wb))
        self.assertTrue((wb / "EXTRACT_GUIDE.md").exists())
        run_cli("-w", str(wb), "scan", "--all", "--claude-dir", str(FIXTURE))
        corpus = scan.read_jsonl(wb / "incr" / "corpus_all.jsonl")
        self.assertEqual(len(corpus), 8)

        out = run_cli("-w", str(wb), "batch", "--size", "5")
        self.assertIn("2 批", out)
        self.assertTrue((wb / "incr" / "batches" / "J1.jsonl").exists())

        user = next(f for f in corpus if f["kind"] == "C")
        jsonl(wb / "incr" / "extracted" / "records_J1.jsonl", [
            {"id": "J1-001", "sess": user["sess"], "proj": user["proj"], "date": user["date"],
             "verbatim": user["user_msg"], "axis": "只做被要求的 > 顺手扩展", "domain": "collab",
             "reusable": True, "confidence": "high"}])
        self.assertIn("OK", run_cli("-w", str(wb), "verify"))
        run_cli("-w", str(wb), "merge")
        run_cli("-w", str(wb), "finish", "--date", "2026-09-02")
        self.assertEqual(len(scan.read_jsonl(wb / "all_records.jsonl")), 1)

        out = run_cli("-w", str(wb), "scan", "--claude-dir", str(FIXTURE))
        self.assertIn("incr-2026-09-02", out)
        self.assertIn("2026-09-02 起", out)                                  # 默认从 last-run 接着扫
        self.assertEqual(scan.read_jsonl(wb / "incr" / "corpus_all.jsonl"), [])
        with self.assertRaises(SystemExit):                                  # 本轮没 finish，不许静默覆盖
            run_cli("-w", str(wb), "scan", "--all", "--claude-dir", str(FIXTURE))
        out = run_cli("-w", str(wb), "scan", "--all", "--redo", "--claude-dir", str(FIXTURE))
        self.assertIn("incr-abandoned-", out)
        self.assertTrue((wb / "incr-2026-09-02" / "extracted" / "records_J1.jsonl").exists())
        run_cli("-w", str(wb), "batch")
        self.assertTrue((wb / "incr" / "batches" / "K1.jsonl").exists())   # J 已被上一轮用掉


if __name__ == "__main__":
    unittest.main()
