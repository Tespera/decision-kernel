<div align="center">

# decision-kernel

**让 Claude Code 学会你的判断方式——从你自己的对话记录里。**

不用写规则，不用填问卷。它读你和 AI 的历史对话，找出你做过的每一次取舍、说过的每一句「因为」，<br>
提炼成一份常驻的**决策内核**：下次遇到同类问题，AI 按你的思路自己拿主意，不再一遍遍来问你。

[![Python](https://img.shields.io/badge/python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![零依赖](https://img.shields.io/badge/依赖-零-2ea44f)](pyproject.toml)
[![Claude Code](https://img.shields.io/badge/for-Claude%20Code-D97757)](https://claude.com/claude-code)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**简体中文** | [English](README.en.md)

</div>

---

## 你是不是也这样？

> **Claude：** 这个旧接口要删掉，还是先保留？<br>
> **你：** 保留，先停用。<br>
> *（三天后，另一个项目）*<br>
> **Claude：** 这张旧表要不要直接删？<br>
> **你：** ……我上次不是说过了吗。

AI 每次都在认真征求你的意见，可同一类问题你已经回答过几十遍了。
写进 `CLAUDE.md` 也不管用：你写的是「旧接口先停用」，它遇到的是「旧表」「旧配置」「旧分支」——**规则只覆盖你写过的场景。**

AI 缺的不是规则，是你**为什么**这么选。上面两次回答背后其实是同一个判断：

> **按可逆性分配谨慎，不按事情大小。**
> 停用代替删除、并存代替覆盖、副本代替原地改造。不确定还有没有用 → 保留。删除是不对称的赌注：赌赢省一点事，赌输不可挽回。
>
> <sub>—— 摘自作者本人蒸馏出的内核，[完整 11 条看这里](examples/decision-kernel.md)</sub>

有了这一条，AI 遇到你没写过的「旧表」「旧分支」，也能推出你会怎么选。

## 它产出什么

一份几百行的 Markdown，常驻在每个 Claude Code 会话里。每条内核三段：

| | 写的是 | 作用 |
|---|---|---|
| **为什么** | 你在乎什么、在保护什么 | 让 AI 理解动机，而不是死记行为 |
| **遇到取舍时问自己** | 几个提问 | 让 AI 推出**没写过的场景**该怎么做 |
| **边界** | 什么时候不适用 | 防止一条原则被用过头 |

最后还有一段「冲突裁决」：几条同时命中时，听哪一条的。

## 真实跑出来的数字

作者用它蒸馏了自己约 10 个月的 Claude Code 记录：

```
340 万字符的对话  →  1377 个决策片段  →  784 条裁决记录  →  125 条动机  →  11 条内核
```

- 第一次增量复盘时，新会话里的 **152 条裁决全部能由已有内核推出**，没有出现内核覆盖不到的新模式。
- 原话校验抓到过一个 subagent **替用户续写了一句原话**。这种「AI 替你发明原则」的错误，会被挡在内核之外。

## 为什么值得信任

- **数据不出本机**。纯本地脚本，零依赖，不调任何外部服务。
- **每句「你说过」都能查**。内核背后的每条证据都是逐字原话，脚本会和原始记录逐字比对，对不上的直接打回。
- **每一条都由你拍板**。AI 只出初稿，内核里的每一条都要你逐条确认才会写入。
- **随你一起进化**。每隔几周跑一次 `/decisions`，用新对话检验内核：哪条还对、缺了什么、哪里被你推翻了。

## 三步上手

```bash
# 1. 安装（Python 3.13+，零依赖）
uv tool install git+https://github.com/Tespera/decision-kernel

# 2. 装上两个 Claude Code 命令
git clone https://github.com/Tespera/decision-kernel /tmp/dk
cp /tmp/dk/claude/commands/*.md ~/.claude/commands/

# 3. 在 Claude Code 里输入
/distill
```

`/distill` 会带你走完全程：筛选对话 → 抽取裁决 → 校验原话 → 归纳动机 → 出初稿 → 你逐条确认 → 写入 `~/.claude/rules/decision-kernel.md`。
之后每隔几周跑一次 `/decisions` 做增量复盘。

## 和其他做法有什么不同

| | 手写 CLAUDE.md 规则 | AI 自动记忆 | **decision-kernel** |
|---|---|---|---|
| 来源 | 你凭印象写 | AI 边聊边记 | 你的**全部历史对话** |
| 内容 | 「遇到 X 做 Y」 | 零散的事实和偏好 | **动机 + 判据 + 边界** |
| 没写过的场景 | 管不到 | 管不到 | 能推出来 |
| 会不会记错 | 取决于你的记性 | 可能把 AI 的猜测当成你说的 | 每句原话都经过逐字校验 |
| 谁拍板 | 你 | AI | 你逐条确认 |

它和自动记忆不冲突：记忆记「发生过什么」，内核记「你怎么判断」。

## 常见问题

<details>
<summary><b>需要多少对话记录才够？</b></summary>

越多越稳。片段少于 30 条时，工具会提示「不值得蒸馏」。作者第一次用了约 10 个月的记录，得到 1377 个片段。记录少一些也能跑：证据不足 3 条的候选不会进内核，会先放进观察清单，等后续复盘攒够证据再说。
</details>

<details>
<summary><b>英文对话能用吗？</b></summary>

能跑，但命中率会低：筛选规则目前是针对中文对话调的。欢迎在 `src/decision_kernel/filters.py` 里补充你所用语言的规则，并提交 PR。
</details>

<details>
<summary><b>我的对话内容会上传到哪里吗？</b></summary>

不会。脚本只读本机的 `~/.claude/` 并写入本机的工作目录（默认 `~/.decision-kernel`）。抽取和归纳由你自己的 Claude Code 会话完成，和你平时用它写代码一样。工作目录里有你的原话，**请不要提交到公开仓库**。
</details>

<details>
<summary><b>Claude Code 的旧对话会被清理，会影响吗？</b></summary>

会。Claude Code 会定期删除旧的会话日志，所以越早跑第一次越好。跑过之后，抽出来的片段会留在工作目录里，不再依赖原始日志。
</details>

<details>
<summary><b>为什么不直接让 AI 总结出一份规则？</b></summary>

作者第一次就是这么做的，得到 37 条规则，最后全部推翻：规则太死，遇到没覆盖的场景就没法用。而且按场景归类，会把最重要的那条动机拆散进好几条规则里，哪条都看不出它。完整经过见 [docs/METHOD.md](docs/METHOD.md)。
</details>

## 工作原理

```mermaid
flowchart LR
    A[本地对话记录] -->|dk scan| B[决策片段]
    B -->|Claude 抽取| C[裁决记录]
    C -->|dk verify<br/>逐字校验| D[可信记录]
    D -->|Claude 按动机归纳| E[初稿]
    E -->|你逐条确认| F[决策内核]
    D -.->|dk evidence| G[证据溯源表]
    G -.-> F
```

<details>
<summary><b>每一步具体做什么</b></summary>

| 步骤 | 谁做 | 做什么 |
|---|---|---|
| `dk scan` | 脚本 | 读 `~/.claude/projects/**/*.jsonl`（完整对话）和 `~/.claude/history.jsonl`（你的输入，保留得更久），挑出发生了决策的片段：回答 AI 的提问、对 AI 刚做的事表示认可或否决、规定 AI 该怎么工作。剔除以用户身份注入的系统文本。不调用任何模型。 |
| 抽取 | Claude / subagent | 把每个片段转成结构化记录，核心是逐字原话和权衡轴（「A > B」）。只转录、不解读。 |
| `dk verify` | 脚本 | 反幻觉闸门：每条原话都必须能在原始记录里逐字找到，能抓出改写、把 AI 的话安到你头上、张冠李戴到上一轮的情况。 |
| 归纳 | Claude，和你一起 | 按**动机**而不是按场景归纳。同一条轴上的相反选择不投票，而是找出隐藏条件，那通常就是边界。 |
| 确认 | 你 | 逐条审，保留、改写、删除或合并。 |
| `dk evidence` | 脚本 | 生成溯源表：每条内核由多少条裁决支撑、来自几个项目、时间跨度、背后的动机。 |

</details>

<details>
<summary><b>命令行参考</b></summary>

| 命令 | 作用 |
|---|---|
| `dk init [目录]` | 建工作目录（默认 `~/.decision-kernel`，或 `$DK_WORKBENCH`），放入抽取规范 |
| `dk scan [--all \| --since 日期]` | 筛选片段；默认从上次复盘结束处接着扫 |
| `dk batch [--size 150]` | 切批，交给多个 subagent 并行抽取；编号自动避开历史 |
| `dk verify` | 逐字校验原话；有问题时退出码为 1 |
| `dk axes` | 生成权衡轴清单，供归纳时通览 |
| `dk merge` | 把本轮记录、动机、内核映射并入累积文件 |
| `dk evidence --kernel 路径` | 生成证据溯源表 |
| `dk finish` | 记下本轮完成日期，作为下次扫描的起点 |
| `dk status` | 查看工作目录状态 |

每一轮都在 `incr/` 里进行，完成后自动归档。没完成的那一轮不会被覆盖，`--redo` 只会把它挪走，不会删除。

</details>

## 贡献

欢迎提 Issue 和 PR，尤其是这几类：

- 其他语言的筛选规则；
- 适配其他 AI 编程工具的日志格式；
- 你用它蒸馏出的内核里，有哪些条目对别人也有启发（去掉原话和项目名后再分享）。

如果它帮你少回答了几次同样的问题，欢迎点个 ⭐，让更多人看到它。

## 许可证

[MIT](LICENSE)
