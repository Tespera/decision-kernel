# decision-kernel

[简体中文](README.md) | **English**

Distill your own **decision kernel** from your Claude Code history, so the AI makes trade-offs the way you would instead of asking you the same kind of question again and again.

A decision kernel is not a rule list. Each entry has three parts:

- **Why**: the motive. What you care about and what you're protecting.
- **Questions to ask at a trade-off**: questions the AI can use to work out situations nobody wrote down.
- **Boundaries**: when the entry doesn't apply, and where it hands off to its neighbours.

A short **conflict-resolution** section then says which entry wins when several apply at once. The result is loaded into every session as `~/.claude/rules/decision-kernel.md`. A real one is in [`examples/decision-kernel.md`](examples/decision-kernel.md) (in Chinese).

## Why not just write rules?

The first attempt produced 37 rules from about 800 recorded decisions. The author rejected them: *"Rules are too rigid. When the AI hits a case they don't cover, they're useless."* Grouping decisions by scenario had also split the strongest motive ("get the best solution, not one that merely works", backed by 46 decisions across 12 projects) into five unrelated rules, so it was no longer visible anywhere.

Motives generalise and rules don't. The full story, with numbers and pitfalls, is in [`docs/METHOD.md`](docs/METHOD.md) (in Chinese).

## How it works

```
local history ─scan─▶ decision fragments ─Claude extracts─▶ decision records ─verify─▶ trusted records
                                                                                   │
        kernel ◀─you confirm each entry─ draft ◀─Claude groups by motive─ motives + trade-off axes
          │
          └─ evidence: which records and motives back each entry
```

| Step | Who | What |
|---|---|---|
| `dk scan` | script | Reads `~/.claude/projects/**/*.jsonl` (full conversations) and `~/.claude/history.jsonl` (your inputs only, kept much longer). Picks out fragments where a decision happened: AskUserQuestion answers, replies to Claude's questions, reactions to what Claude just did, and instructions about how Claude should work. Drops text that the system injected as the user. No LLM. |
| extract | Claude / subagents | Turns each fragment into a record whose key fields are the verbatim quote (`verbatim`) and the trade-off axis ("A > B"). The extractor transcribes and does not interpret. 40–60% of fragments are expected to be dropped. |
| `dk verify` | script | **The anti-hallucination gate.** Every verbatim quote must appear word for word in the user side of the source fragment. It catches paraphrases, Claude's words passed off as yours, and quotes taken from the wrong turn. On the first real run it caught a subagent that had extended a quote with a sentence of its own. |
| synthesise | Claude, with you | Groups records by **motive** rather than scenario. Opposite decisions on the same axis are explained by a hidden condition (which usually becomes a boundary), not settled by majority vote. Only reusable decisions count, and each new entry needs at least 3 pieces of evidence or at least 2 projects. |
| confirm | you | You review every entry. AI cannot get this step right on its own. |
| `dk evidence` | script | Builds an evidence map: for each kernel entry, the records, projects, date range and motives behind it. |

After the first distillation, `/decisions` re-runs this on new sessions every few weeks. It classifies each new decision as *covered*, *new pattern*, *contradiction*, or *questioning-behaviour mismatch* (the AI asked when the kernel already gave an answer, or didn't ask when it should have). Candidates without enough evidence wait in `watchlist.md`.

## Install

Requires Python ≥ 3.13. Standard library only, no dependencies.

```bash
uv tool install git+https://github.com/Tespera/decision-kernel
# or: pipx install git+https://github.com/Tespera/decision-kernel
```

Install the two Claude Code commands that drive the steps needing judgement:

```bash
git clone https://github.com/Tespera/decision-kernel
cp decision-kernel/claude/commands/*.md ~/.claude/commands/
```

## Usage

In Claude Code, run **`/distill`** for the first distillation and **`/decisions`** for later incremental reviews. The commands call `dk` for the mechanical steps and stop for your confirmation before changing the kernel.

The CLI on its own:

| Command | Does |
|---|---|
| `dk init [DIR]` | Create the workbench (default `~/.decision-kernel`, or `$DK_WORKBENCH`) with the extraction guides |
| `dk scan [--all \| --since DATE]` | Filter fragments into `incr/corpus_all.jsonl`; by default it continues from the last finished review |
| `dk batch [--size 150]` | Split fragments into batches for parallel subagents; the ID prefix automatically avoids earlier ones |
| `dk verify` | Check every verbatim quote; exits 1 if anything needs fixing |
| `dk axes` | Write a one-line-per-record list of trade-off axes for review |
| `dk merge` | Append this round's records, motives and kernel mappings to the cumulative files |
| `dk evidence --kernel PATH` | Regenerate `evidence-map.md` |
| `dk finish` | Record today as the starting point for the next `scan` |
| `dk status` | Show the workbench state |

Each round works in `incr/`. Once you've run `finish` on it, the next `scan` archives it as `incr-<date>/`. An unfinished round is never overwritten: `--redo` moves it aside instead of deleting it.

## Privacy

Everything stays on your machine. The workbench holds your verbatim words, project names and session IDs, so **keep it private and never commit it to a public repository.** The kernel itself is written without quotes or project names, so it can be shared.

Claude Code periodically deletes old session logs. The corpora in `incr-*/` may be the only remaining copy of what you said, so don't treat them as disposable.

## Limitations

- The filtering patterns are tuned for **Chinese** conversations. English sessions work but match less; extend `src/decision_kernel/filters.py` for your language.
- Depends on Claude Code's local log format (`~/.claude/projects/*.jsonl`, `~/.claude/history.jsonl`).
- Scripts handle only the mechanical steps and the verification gate. The quality of the kernel depends on the extraction model and on your review.
- `docs/METHOD.md`, the extraction guides and the example kernel are currently in Chinese.

## Development

```bash
uv run python -m unittest discover -s tests
```

## License

MIT
