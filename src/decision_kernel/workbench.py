"""工作目录（workbench）的布局与定位。

<workbench>/
  last-run              上次复盘完成的日期，下次 scan 从这里开始
  EXTRACT_GUIDE.md      抽取裁决记录的规范（给 Claude / subagent 读）
  MOTIVE_GUIDE.md       抽取动机陈述的规范
  METHOD.md             方法说明；decision-kernel.example.md 作者本人的内核，作初稿格式参考（init 时更新）
  all_records.jsonl     累积的全部裁决记录
  motives.jsonl         累积的动机陈述
  kernel_map.jsonl      裁决记录 → 内核编号 的映射（{"id", "kernel"}）
  evidence-map.md       每条内核的证据溯源表（evidence 命令生成）
  watchlist.md          暂缓的候选与试行修订
  incr/                 本轮工作目录；下一轮 scan 开始时归档为 incr-<上次日期>/
  incr-YYYY-MM-DD/      历次归档

定位顺序：命令行 --workbench > 环境变量 DK_WORKBENCH > ~/.decision-kernel
"""
import os
from pathlib import Path

DEFAULT = Path.home() / ".decision-kernel"


class Workbench:
    def __init__(self, root=None):
        root = root or os.environ.get("DK_WORKBENCH") or DEFAULT
        self.root = Path(root).expanduser()

    @property
    def run(self):
        return self.root / "incr"

    @property
    def last_run_file(self):
        return self.root / "last-run"

    def path(self, name):
        return self.root / name

    def last_run(self):
        """上次完成复盘的日期（YYYY-MM-DD）；从没跑过返回 None。"""
        f = self.last_run_file
        if f.exists():
            s = f.read_text(encoding="utf-8").strip()
            return s or None
        return None

    def require(self):
        if not self.root.is_dir():
            raise SystemExit(f"工作目录不存在：{self.root}\n先运行 dk init {self.root}")
        return self
