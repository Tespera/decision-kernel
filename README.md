# decision-kernel

**简体中文** | [English](README.en.md)

从你的 Claude Code 历史记录里蒸馏出一份**决策内核**，让 AI 按你的方式做取舍，而不是一遍遍拿同一类问题来问你。

决策内核不是规则清单。每条三段：

- **为什么**：动机。你在乎什么、在保护什么。
- **遇到取舍时问自己**：几个提问，AI 用它们推出没写过的场景该怎么做。
- **边界**：什么时候不适用，和相邻的条目怎么分界。

末尾再加一段**冲突裁决**：多条同时命中时谁优先。成品写成 `~/.claude/rules/decision-kernel.md`，在每个会话里常驻。真实样例见 [`examples/decision-kernel.md`](examples/decision-kernel.md)。

## 为什么不直接写规则？

第一次尝试从约 800 条决策里提炼出 37 条规则，被作者否掉了：「**规则太死，AI 遇到没覆盖的场景没法用。**」而且按场景分组，把最强的那条动机（「要最佳解，不要能用的解」，46 条决策、12 个项目）拆进了 5 条互不相干的规则，哪一条都看不出它。

动机能泛化，规则不能。完整经过、数字和踩过的坑见 [`docs/METHOD.md`](docs/METHOD.md)。

## 怎么运作

```
本地记录 ─scan─▶ 决策片段 ─Claude 抽取─▶ 裁决记录 ─verify─▶ 可信记录
                                                       │
        内核 ◀─你逐条确认─ 初稿 ◀─Claude 按动机归纳─ 动机陈述 + 权衡轴清单
         │
         └─ evidence：每条内核由哪些记录、哪些动机支撑
```

| 步骤 | 谁做 | 做什么 |
|---|---|---|
| `dk scan` | 脚本 | 读 `~/.claude/projects/**/*.jsonl`（完整对话）和 `~/.claude/history.jsonl`（只有你的输入，保留更久），挑出发生了决策的片段：AskUserQuestion 的回答、对 Claude 提问的回复、对 Claude 刚做的事的反应、对 Claude 工作方式的要求。剔除以用户身份注入的系统文本。不用 LLM。 |
| 抽取 | Claude / subagent | 每个片段转成一条记录，核心是逐字原话（`verbatim`）和权衡轴（「A > B」）。只转录、不解读，预期丢弃 40–60%。 |
| `dk verify` | 脚本 | **反幻觉闸门。**每条原话必须能在原片段的用户侧逐字找到，能抓出改写、把 Claude 的话安到你头上、张冠李戴到上一轮。第一次真跑就抓到一个 subagent 给原话续写了一句。 |
| 归纳 | Claude，和你一起 | 按**动机**而不是按场景归纳。同一条轴上的相反裁决不投票，找出隐藏条件（通常就是边界）。只用可迁移的裁决；每条新内核要 ≥3 条证据或跨 ≥2 个项目。 |
| 确认 | 你 | 逐条审。这一步 AI 单靠自己做不对。 |
| `dk evidence` | 脚本 | 生成溯源表：每条内核由哪些记录支撑、来自哪些项目、时间跨度、背后的动机。 |

首次蒸馏之后，每隔几周用 `/decisions` 对新会话做增量复盘，把每条新裁决归为：*已覆盖*、*新模式*、*相悖*、*提问行为偏差*（内核已有答案还在问，或该问没问）。证据不够的候选先放进 `watchlist.md` 观察。

## 安装

需要 Python ≥ 3.13。只用标准库，没有任何依赖。

```bash
uv tool install git+https://github.com/Tespera/decision-kernel
# 或：pipx install git+https://github.com/Tespera/decision-kernel
```

再装两个 Claude Code 命令，它们负责需要判断的步骤：

```bash
git clone https://github.com/Tespera/decision-kernel
cp decision-kernel/claude/commands/*.md ~/.claude/commands/
```

## 使用

在 Claude Code 里，首次蒸馏跑 **`/distill`**，之后的增量复盘跑 **`/decisions`**。机械步骤由命令调用 `dk` 完成，改内核之前会停下等你确认。

单独使用命令行：

| 命令 | 作用 |
|---|---|
| `dk init [目录]` | 建工作目录（默认 `~/.decision-kernel`，或 `$DK_WORKBENCH`），放入抽取规范 |
| `dk scan [--all \| --since 日期]` | 硬筛片段到 `incr/corpus_all.jsonl`；默认从上次完成的复盘接着扫 |
| `dk batch [--size 150]` | 切批供 subagent 并行抽取；编号前缀自动避开历史 |
| `dk verify` | 校验每条原话；有要处理的问题时退出码为 1 |
| `dk axes` | 生成一行一条的权衡轴清单，供归纳时通览 |
| `dk merge` | 把本轮记录、动机、内核映射并入累积文件 |
| `dk evidence --kernel 路径` | 重新生成 `evidence-map.md` |
| `dk finish` | 记下今天，作为下次 `scan` 的起点 |
| `dk status` | 查看工作目录状态 |

每一轮都在 `incr/` 里进行。跑过 `finish` 的那一轮，会在下次 `scan` 时归档为 `incr-<日期>/`。没 finish 的不会被覆盖：`--redo` 只会把它挪走，不会删除。

## 隐私

所有数据都留在你本机。工作目录里有你的逐字原话、项目名和会话编号，**请保持私有，绝不要提交到公开仓库。**内核本身不含原话和项目名，可以分享。

Claude Code 会定期删除旧的会话日志。`incr-*/` 里的语料可能是你原话仅存的一份，不要当成可随手删掉的中间产物。

## 局限

- 筛选规则针对**中文**对话调过。英文会话能跑但命中率低，可以按你的语言扩充 `src/decision_kernel/filters.py`。
- 依赖 Claude Code 的本地日志格式（`~/.claude/projects/*.jsonl`、`~/.claude/history.jsonl`）。
- 脚本只负责机械环节和校验闸门，内核质量取决于抽取模型和你的确认。

## 开发

```bash
uv run python -m unittest discover -s tests
```

## 许可证

MIT
