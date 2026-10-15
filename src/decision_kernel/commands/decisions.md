---
description: 增量复盘决策内核——扫上次之后的新会话，找内核没覆盖的新模式和与内核相悖的裁决，出报告等确认后修订
---

# /decisions — 决策内核增量复盘

把上次复盘之后的新会话过一遍，检验 `~/.claude/rules/decision-kernel.md` 还对不对、缺不缺。
内核是判断依据不是规则，所以复盘找的不是「新规则」，是**新的动机、内核没覆盖的取舍、与内核相悖的裁决**。
工作目录默认 `~/.decision-kernel`（可用 `DK_WORKBENCH` 改）。先跑 `dk details`：启用了场景细则层（见 `DETAILS_GUIDE.md`），下文标「细则」的部分才做。

## 步骤

### 1. 还原点
```bash
cd ~/.decision-kernel && git add -A && git commit -qm "decisions: 复盘前快照 $(date +%Y-%m-%d)" || true
```

### 2. 增量硬筛
```bash
dk scan          # 从 last-run 起；上一轮已 finish 的 incr/ 会自动归档
```
**少于 30 条片段就说「增量太少，不值得复盘」，停。**

### 3. 抽取裁决记录
- 片段 ≤ 150 条：主会话自己按工作目录里的 `EXTRACT_GUIDE.md` 逐条转录，写 `incr/extracted/records_<前缀>1.jsonl`。
- 片段 > 150 条：`dk batch`（前缀自动避开历史编号），每批交一个 subagent，先读 EXTRACT_GUIDE.md，产物写文件、只回报统计。
- 抽完 `dk verify`，`MISSING` / `CLAUDE` / `PREV` 必须处理到通过。

### 4. 对照内核（核心步骤）
读 `~/.claude/rules/decision-kernel.md` 全文和工作目录的 `watchlist.md`（上轮暂缓的候选与试行修订，本轮要报它们的新增证据数）；
启用了细则的，再读细则目录里的各篇（判断某个具体做法写过没有）。对每条新裁决判断：

| 类 | 含义 | 处理 |
|---|---|---|
| **已覆盖** | 某条内核的提问能直接推出这个裁决 | **每条**都写进 `incr/kernel_map.jsonl`（`{"id","kernel"}`），溯源表才完整 |
| **新模式** | 没有内核能推出它，且 ≥3 次或跨 ≥2 项目 | 候选新内核或现有内核的新边界 |
| **相悖** | 裁决方向与某条内核相反 | 先找隐藏条件（多半是内核漏了边界）；找不到才是内核错了 |
| **提问行为偏差** | Claude 该自己定却问了 / 该问却没问 | 单独统计——这是内核落地效果的直接指标 |

用户的**理由陈述**单独按 `MOTIVE_GUIDE.md` 抽到 `incr/motives.jsonl`，那是动机层的增量。

**发现往哪写**：新判据、新边界 → 内核（过证据门槛）；已有内核在具体场景下的新做法 → 细则（单次即可，用户确认后写）；
可能是新判据但证据不够 → `watchlist.md`。口诀：内核的用法 → 细则；可能是新判据 → 观察清单；证据够了 → 内核。
没启用细则时，「新做法」只在报告里提一句，问用户要不要启用。

### 5. 出报告，等确认
```
增量：N 片段 → M 裁决（YYYY-MM-DD ~ YYYY-MM-DD，项目：…）
已覆盖 a 条 · 新模式 b 条 · 相悖 c 条 · 提问行为偏差 d 条

【新模式】  …（证据 ≥3 条 / 项目数，建议：新内核 / 加进 K-x 边界）
【相悖】    内核 K-x 说 A，但 YYYY-MM-DD 你选了 B。隐藏条件可能是 …
【提问行为】 内核已覆盖但仍在问的 / 该问没问的
【场景细则】 按文件列：往哪篇加什么做法（对应哪条内核、依据哪几条裁决）
【观察清单】 每个暂缓候选和试行修订本轮的新增证据数
【动机增量】 …
【建议修订】 逐条列：改哪个文件、改什么
```
除非用户明确说「直接执行」，否则打印报告后等确认。

### 6. 执行
- **改之前先留底**（内核和细则都不在工作目录里，第 1 步的快照管不到它们）：
  ```bash
  WB="${DK_WORKBENCH:-$HOME/.decision-kernel}"
  cp ~/.claude/rules/decision-kernel.md "$WB/incr/kernel-before.md"
  cp -R <细则目录> "$WB/incr/details-before"      # 启用了细则时；目录见 dk details
  ```
- 按确认修改内核。**每改一处都自问：这是动机和判据，还是又写成了规则？**
- 按确认修改细则：沿用该篇格式加条目，注明依据的裁决 id；新增一篇时确认内核里的指引仍然对得上（`dk details`）。
- 暂缓的候选、试行的修订写进 `watchlist.md`。
```bash
dk merge
dk evidence --kernel ~/.claude/rules/decision-kernel.md
dk finish
cd ~/.decision-kernel && git add -A && git commit -qm "decisions: 复盘 — <一句话>"
```

## 硬约束
- 内核正文不写原话、不写项目名和业务对象；原话只留在工作目录里溯源。
- 相悖不等于内核错——先找条件，多数「矛盾」是漏了边界。
- 不为凑数新增内核：新模式要 ≥3 次证据或跨 ≥2 项目；证据不够的进 watchlist。
- 细则只写已有内核的用法，不借细则加新判据。
- 未确认不改内核和细则；改完必须更新 evidence 并 finish。
