---
description: 首次蒸馏——从全部 Claude Code 会话记录里提炼你的决策内核，逐条确认后落地
---

# /distill — 首次蒸馏决策内核

从你和 Claude Code 的全部本地记录里，找出你做过的取舍和说过的理由，提炼成一份**决策内核**：
每条 = 为什么（动机）+ 遇到取舍时问自己（判据）+ 边界。目标是让 AI 在没见过的场景里也能按你的方式判断，
从而少来问你。方法与踩过的坑见工作目录里的 `METHOD.md`（`dk init` 放入），**动手前先读一遍**。

工作目录默认 `~/.decision-kernel`（可用 `DK_WORKBENCH` 改）。内核成品默认写到 `~/.claude/rules/decision-kernel.md`。
可选的第二层「场景细则」（某条内核在具体场景下怎么用，按需查阅）见工作目录里的 `DETAILS_GUIDE.md`。

## 步骤

### 1. 准备
```bash
dk init                      # 建工作目录，放入抽取规范
cd ~/.decision-kernel && git init -q && git add -A && git commit -qm "init"   # 建议：每步可回滚
```

### 2. 语料硬筛（纯脚本）
```bash
dk scan --all
```
报告片段数、按项目分布。片段太少（几十条）不值得蒸馏，先攒一段时间。

### 3. 抽取裁决记录
```bash
dk batch --size 150
```
每批交给一个 subagent，prompt 要求：先读工作目录里的 `EXTRACT_GUIDE.md`，按它把 `incr/batches/<批次>.jsonl`
转成 `incr/extracted/records_<批次>.jsonl`，只回报条数统计，不要把记录贴回对话。

抽完必须过原话校验：
```bash
dk verify
```
`MISSING` / `CLAUDE` / `PREV` 必须逐条处理（改成真实原话、补 `src_note`、或删掉），直到通过。**这一步不能跳。**

### 4. 抽取动机
从记录里挑出用户**说了理由**的（「因为」「为了」「不然」……），按 `MOTIVE_GUIDE.md` 写 `incr/motives.jsonl`，`kernel` 先留空。
动机是内核「为什么」一节的来源，比裁决本身更值钱。

### 5. 归纳内核（主会话做，不要交给脚本）
```bash
dk axes          # 生成 incr/axes.md：每条记录一行「权衡轴 · 领域 · 可迁移性 · 置信度」
```
读 `axes.md` 和动机，按**动机**而不是按行为场景归纳。要点（详见工作目录里的 `METHOD.md`）：
- 同一个动机会散落在很多场景里——按场景分组会把最强的动机拆碎，找不到它。
- 同一权衡轴上出现相反的裁决，不要取多数：先找隐藏条件，那通常就是边界。
- 只保留可迁移的（`reusable: true`）；绑死在某个项目上的不进内核。
- 每条内核要有 ≥3 条独立证据或跨 ≥2 个项目；证据不足的放进 `watchlist.md`。

### 6. 出初稿，逐条确认
按工作目录里 `decision-kernel.example.md`（作者本人的内核，`dk init` 放入）的格式写初稿：

```
总则（一两句）
## K1 · <名称>
**为什么**          动机，不是规则
**遇到取舍时问自己**  能推导出没写过的场景的提问
**边界**            什么时候不适用、和哪条内核的分界
……
## 冲突裁决          多条同时命中时的优先级
```

**内核正文不写原话、不写项目名和业务对象**——它要能被任何项目引用，证据留在工作目录。
把初稿给用户**逐条审**：保留 / 改写 / 删除 / 合并。用户说「太死」时，多半是写成了规则，退回动机层重写。

归纳时会遇到一类东西：它是某条内核在具体场景下的做法（「删数据时先停用」「推送前先本地验证」），太具体、放进内核会撑大常驻内容。
把它们单独列成**细则候选**，和初稿一起给用户看，问要不要启用场景细则层。用户要，就 `dk init --details`（默认目录
`~/.claude/decision-kernel-details`，也可以指定），按 `DETAILS_GUIDE.md` 写；用户不要，就留在溯源表里，不硬塞进内核。

### 7. 落地
- 写入 `~/.claude/rules/decision-kernel.md`。`rules/` 下的文件 Claude Code 每个会话自动加载，不需要再在 `CLAUDE.md` 里引用。
- 启用了场景细则：按确认把细则写进细则目录，在内核总则下加一行指向细则目录的指引，跑 `dk details` 检查（指引缺失会提示）。
- 把每条有效记录归到对应内核，写 `incr/kernel_map.jsonl`（`{"id":"J1-003","kernel":"K2"}`），动机回填 `kernel`。
```bash
dk merge                                            # 记录、动机、映射并入累积文件
dk evidence --kernel ~/.claude/rules/decision-kernel.md   # 生成证据溯源表
dk finish                                           # 记下日期，下次增量从这里开始
cd ~/.decision-kernel && git add -A && git commit -qm "distill: 首次蒸馏"
```

## 硬约束
- 原话必须过 `dk verify`；任何「用户原话」都要能在原始记录里搜到。
- 内核只写动机与判据，不写成「遇到 X 就做 Y」。
- 未经用户逐条确认，不写入 `~/.claude/rules/`，也不写细则。
- 细则只写已有内核的用法，不借细则加新判据。
