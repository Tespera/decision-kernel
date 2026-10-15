<div align="center">

# decision-kernel

**Teach Claude Code how *you* make decisions, learned from your own conversation history, not hand-written CLAUDE.md rules.**

No rules to write, no questionnaire to fill in. It reads your past sessions with the AI, finds every trade-off you made and every "because" you said, <br>
and distils them into an always-loaded **decision kernel**. The next time a similar question comes up, the AI decides your way instead of asking you again.

[![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-2ea44f)](pyproject.toml)
[![Claude Code](https://img.shields.io/badge/for-Claude%20Code-D97757)](https://claude.com/claude-code)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[简体中文](README.md) | **English**

</div>

---

## Sound familiar?

> **Claude:** Should I delete this old endpoint, or keep it for now?<br>
> **You:** Keep it. Just disable it.<br>
> *(three days later, different project)*<br>
> **Claude:** Should I just drop this old table?<br>
> **You:** …didn't I already tell you?

The AI is conscientiously asking for your input, but you've answered this kind of question dozens of times.
Writing it into `CLAUDE.md` doesn't help either. You wrote "disable old endpoints"; next it meets an old table, an old config, an old branch. **Rules only cover the cases you wrote down.**

What the AI is missing isn't a rule. It's **why** you chose what you chose. Both answers above come from the same judgement:

> **Match caution to reversibility, not to how big the change looks.**
> Disable instead of delete, run side by side instead of overwriting, copy instead of modifying in place. Not sure it's still needed → keep it. Deleting is an asymmetric bet: win and you save a little effort, lose and it can't be undone.
>
> <sub>Translated from the author's own distilled kernel. [See all 11 entries](examples/decision-kernel.en.md).</sub>

With that one entry, the AI can work out what you'd do with an old table or an old branch, even though you never mentioned either.

## What you get

A few hundred lines of Markdown, loaded into every Claude Code session. Each entry has three parts:

| | Contains | Purpose |
|---|---|---|
| **Why** | What you care about and what you're protecting | The AI understands the motive instead of memorising behaviour |
| **Questions to ask at a trade-off** | A handful of questions | The AI can reason about **situations you never wrote down** |
| **Boundaries** | When it doesn't apply | Stops a principle from being over-applied |

A final conflict-resolution section says which entry wins when several apply at once.

## Real numbers

The author distilled about 10 months of their own Claude Code history:

```
3.4M characters of conversation → 1,377 decision fragments → 784 decision records → 125 motives → 11 kernel entries
```

- **New sessions test the kernel, and sometimes correct it.** In the first incremental review (2026-09), **150 of 152 decisions could be derived from the existing kernel**. The other 2 were "the kernel already answers this, yet the AI still asked" signals. No new pattern, no contradiction. Some of those decisions predate the final kernel, though, so this isn't a strict out-of-sample test. The second review (2026-10) turned up 2 new patterns and 1 contradiction among 330 decisions; the author revised two entries and parked the other candidates on a watchlist. Each decision was classified by Claude against "can the entry's questions directly lead to this decision?", and the author signed off on the report.
- The quote verifier once caught a subagent **extending the user's quote with a sentence of its own**. This kind of error, where the AI invents a principle in your name, is kept out of the kernel.

<details>
<summary><b>How much evidence backs each entry</b> (from the author's own <code>dk evidence</code> output, as of 2026-10, including two incremental reviews)</summary>

| Entry | Decision records | Projects | Date range |
|---|--:|--:|---|
| K1 · Aim for the best solution, not one that merely works | 64 | 11 | 2026-04 – 2026-10 |
| K2 · Solid premises, judgements on visible things | 56 | 13 | 2026-03 – 2026-09 |
| K3 · Interrupt me only when only I can answer | 40 | 11 | 2026-03 – 2026-09 |
| K4 · Match caution to reversibility | 51 | 10 | 2026-03 – 2026-09 |
| K5 · Fix it at the root cause | 42 | 6 | 2026-04 – 2026-09 |
| K6 · An output's standard is set by its readers | 103 | 15 | 2026-03 – 2026-10 |
| K7 · Don't rely on people remembering | 35 | 8 | 2026-03 – 2026-09 |
| K8 · Never make the same decision twice | 23 | 8 | 2026-04 – 2026-09 |
| K9 · Purpose before means | 26 | 8 | 2026-03 – 2026-09 |
| K10 · Keep real information and judgement | 7 | 4 | 2026-06 – 2026-08 |
| K11 · Finish what was asked; don't add what wasn't | 28 | 8 | 2026-04 – 2026-09 |

Only the counts are public. The verbatim quotes and project names behind each record stay on the author's machine.
</details>

## Why you can trust it

- **Your data only goes through your own Claude Code.** `dk` is a local script with zero dependencies and no network access. The steps that need understanding, extraction and synthesis, run in your own Claude Code session, through the same channel as everything you already send Claude while coding. No third-party service is involved.
- **Every "you said" is checkable.** Each piece of evidence behind the kernel is a verbatim quote, and the script checks it word for word against your original sessions. Quotes that don't match get sent back.
- **You approve every entry.** The AI only drafts. Nothing goes into the kernel until you've reviewed it entry by entry.
- **It evolves with you.** Run `/decisions` every few weeks to test the kernel against new sessions: what still holds, what's missing, and where you've changed your mind.

## Get started in three steps

```bash
# 1. Install (Python 3.10+, zero dependencies)
uv tool install git+https://github.com/Tespera/decision-kernel

# 2. Add the /distill and /decisions commands to Claude Code
dk install-commands

# 3. In Claude Code, run
/distill
```


`/distill` walks you through the whole process: filter sessions → extract decisions → verify quotes → group by motive → draft → you confirm each entry → written to `~/.claude/rules/decision-kernel.md`.
After that, run `/decisions` every few weeks for an incremental review.

> [!TIP]
> By default Claude Code keeps session logs for only **30 days** and deletes them silently. If you haven't changed it, add `"cleanupPeriodDays": 3650` to `~/.claude/settings.json` so future sessions aren't lost.

## How it compares

| | Hand-written CLAUDE.md rules | AI auto-memory | **decision-kernel** |
|---|---|---|---|
| Source | Your recollection | Notes the AI takes as you chat | **Your entire session history** |
| Content | "When X, do Y" | Scattered facts and preferences | **Motive + questions + boundaries** |
| Unwritten situations | Not covered | Not covered | Can be reasoned out |
| Can it misremember? | Depends on your memory | May record the AI's guess as your words | Every quote is verified word for word |
| Who decides | You | The AI | You, entry by entry |

It complements auto-memory: memory records *what happened*; the kernel records *how you judge*.

## FAQ

<details>
<summary><b>How much history do I need?</b></summary>

More is better. With fewer than 30 fragments, the tool tells you a distillation isn't worth it yet. The author's first run used about 10 months of history, which gave 1,377 fragments. Smaller histories work too: a candidate with fewer than 3 pieces of evidence doesn't enter the kernel. It waits in a watchlist until later reviews collect enough evidence.
</details>

<details>
<summary><b>How long does a run take, and how much usage does it cost?</b></summary>

The author's measurements:

| | First distillation | Incremental review (each) |
|---|---|---|
| Scale | 1,377 fragments → 784 decisions | 288–541 fragments → 152–330 decisions |
| Actual running time | about 2 hours | 13–29 minutes |
| Of which extraction | 8 parallel subagents, about 19 minutes | 4 parallel subagents, 6–8 minutes |
| Tokens | about 33M, of which about 760K output; most of it is cache reads | about 9M, of which about 160K output |

The first distillation spanned 3 calendar days, but the machine ran for only about 2 hours; the rest was the session sitting idle while the author read drafts and made calls. Extraction is pure transcription, so Sonnet-class subagents are enough (5 of the author's 8 first-run batches used Sonnet), which saves a good deal of usage.
</details>

<details>
<summary><b>Does it work with English conversations?</b></summary>

It runs, but matches less: the filtering patterns are currently tuned for Chinese. PRs adding patterns for your language in `src/decision_kernel/filters.py` are very welcome.
</details>

<details>
<summary><b>Is my conversation data uploaded anywhere?</b></summary>

Nowhere except your own Claude Code session. The `dk` script has no network access: it only reads your local `~/.claude/` and writes to a local workbench (default `~/.decision-kernel`). Extraction and synthesis happen in your own Claude Code session, where fragments are sent to Claude as conversation content, the same way you normally use it for coding. No third-party service is involved. The workbench contains your verbatim words, so **don't commit it to a public repository.**
</details>

<details>
<summary><b>Claude Code deletes old sessions. Does that matter?</b></summary>

Yes. By default Claude Code keeps session logs (the full conversations under `~/.claude/projects/`) for 30 days, then deletes them silently in the background. Your input history, `history.jsonl`, isn't affected by this setting and lasts longer.

So do two things early:

1. Raise the retention period in `~/.claude/settings.json`, for example `"cleanupPeriodDays": 3650` (in days, minimum 1), so nothing more is lost from today on. Logs already deleted can't be recovered.
2. Run your first distillation soon. After that, the extracted fragments stay in your workbench and no longer depend on the original logs.
</details>

<details>
<summary><b>Why not just ask the AI to summarise a list of rules?</b></summary>

That's exactly what the author tried first. It produced 37 rules, and every one was rejected: rules were too rigid to handle cases they didn't cover. Grouping decisions by scenario also split the single most important motive across several rules, so it was no longer visible in any of them. The full story is in [docs/METHOD.en.md](docs/METHOD.en.md).
</details>

## How it works

```mermaid
flowchart LR
    A[Local sessions] -->|dk scan| B[Decision fragments]
    B -->|Claude extracts| C[Decision records]
    C -->|dk verify<br/>word for word| D[Trusted records]
    D -->|Claude groups by motive| E[Draft]
    E -->|you confirm each entry| F[Decision kernel]
    D -.->|dk evidence| G[Evidence map]
    G -.-> F
```

<details>
<summary><b>What each step does</b></summary>

| Step | Who | What |
|---|---|---|
| `dk scan` | script | Reads `~/.claude/projects/**/*.jsonl` (full conversations) and `~/.claude/history.jsonl` (your inputs, kept much longer). Picks out fragments where a decision happened: answers to the AI's questions, approval or rejection of what the AI just did, and instructions about how the AI should work. Removes system text that was injected in the user's name. Calls no model. |
| extract | Claude / subagents | Turns each fragment into a structured record whose core is the verbatim quote and the trade-off axis ("A > B"). Transcribes; does not interpret. |
| `dk verify` | script | The anti-hallucination gate: every quote must appear word for word in the original session. It catches paraphrases, the AI's words attributed to you, and quotes taken from the wrong turn. |
| synthesise | Claude, with you | Groups by **motive**, not scenario. Opposite choices on the same axis aren't settled by vote; they're explained by a hidden condition, which usually becomes a boundary. |
| confirm | you | Review each entry: keep, rewrite, delete or merge. |
| `dk evidence` | script | Builds an evidence map: for each entry, how many decisions back it, how many projects they come from, the date range, and the motives behind it. |

</details>

<details>
<summary><b>CLI reference</b></summary>

| Command | Does |
|---|---|
| `dk install-commands [--force]` | Install `/distill` and `/decisions` into `~/.claude/commands/`. An existing file with different content is skipped; `--force` backs it up as `.bak` first |
| `dk init [DIR]` | Create the workbench (default `~/.decision-kernel`, or `$DK_WORKBENCH`) with the extraction guides, the method notes and the example kernel |
| `dk scan [--all \| --since DATE]` | Filter fragments; by default it continues from where the last review ended |
| `dk batch [--size 150]` | Split fragments into batches for parallel subagents; IDs automatically avoid earlier ones |
| `dk verify` | Check every quote word for word; exits 1 if anything needs fixing |
| `dk axes` | Write the list of trade-off axes for review |
| `dk merge` | Append this round's records, motives and kernel mappings to the cumulative files |
| `dk evidence --kernel PATH` | Build the evidence map |
| `dk finish` | Record the completion date as the starting point for the next scan |
| `dk status` | Show the workbench state |

Each round works in `incr/` and is archived automatically once finished. An unfinished round is never overwritten: `--redo` moves it aside instead of deleting it.

</details>

## Contributing

Issues and PRs are welcome, especially:

- Filtering patterns for other languages.
- Adapters for other AI coding tools' log formats.
- Kernel entries from your own distillation that could help others (strip quotes and project names first).

If it saved you from answering the same question one more time, a ⭐ helps others find it.

## License

[MIT](LICENSE)
