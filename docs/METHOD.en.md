*English translation of [METHOD.md](METHOD.md); the Chinese original is authoritative.*

# Method: from session logs to a decision kernel

This document records how the method came about, why it ended up in its current shape, and the mistakes made along the way. The numbers come from the author's first distillation (2026-08) and the two incremental reviews since.

## The problem

People who code with AI spend their days answering the AI's questions: which approach, back up first or not, change this or leave it, how detailed should the docs be…
The same kinds of questions keep coming back, and each time you have to decide all over again. What wears you down isn't any single decision. It's **making the same kind of decision dozens of times**.

The goal isn't to stop the AI from asking altogether. It's to downgrade the remaining questions from "decide for me" to "just nod":
whatever can be worked out from how I judge things, it decides itself and mentions in the result ("went with X, per your usual preference"). Only what really needs me (irreversible, external-facing, missing business facts, a fork in direction) comes back as a question.

## Why the first version failed: a rule list

The first distillation took the obvious route: cluster decisions by scenario and write one rule per cluster. It produced **37 rules**, and they were rejected. In the author's words:

> The rules are too rigid. When the AI hits a case they don't cover, it can't use them.

Looking back, there were two fundamental problems:

1. **Rules only cover the cases you wrote down.** "Once the plan is settled, finish it in one go" works for writing code, but not for writing docs, drafting proposals or changing config. Faced with a case nobody wrote down, the AI either forces a bad fit or comes back to ask.
2. **Clustering by scenario breaks up the strongest motives.** The author's strongest motive is "the best solution, not one that merely works" (46 decisions across 12 projects). Clustering by scenario scattered it across 5 different rules, and **it wasn't visible in any of them**.

## Second version: the decision kernel

The second version writes down only **the basis for judgement**, not behavioural rules. Each kernel entry has three parts:

- **Why**: the motive. What I care about, what I'm protecting, which costs I'm weighing.
- **Questions to ask at a trade-off**: a few questions the AI uses to work out what to do in cases nobody wrote down.
- **Boundaries**: when it doesn't apply, and where it ends and neighbouring entries begin.

Plus a **conflict resolution** section: which entry wins when several apply at once (e.g. "reversibility trumps everything").

The result is a general principle, 11 kernel entries and 8 conflict rules: about 300 lines, loaded into every session. The finished kernel is in `examples/decision-kernel.en.md`.

Two deliberate constraints:

- **No quotes, project names or business objects in the kernel body.** It has to be usable as-is in any project. Mention a business object and the AI will treat the entry as a rule for that one project. Quotes and evidence are kept separately, in the evidence map in the workbench.
- **Motives must be backed by the user's own words, not reverse-engineered by the AI.** The second round mined 125 motive statements from the 139 fragments that included a reason, and checked one by one that every entry's "Why" rests on reasons the user actually gave.

## Pipeline

```
local logs ──scan──▶ decision fragments ──Claude extracts──▶ decision records ──verify──▶ trusted records
                                                                                          │
           kernel ◀──user confirms each entry── draft ◀──Claude groups by motive── motive statements + trade-off axis list
             │
             └── evidence: which records and motives back each entry (evidence map)
```

### 1. Hard filter (`dk scan`, pure rules, zero LLM)

Two sources that complement each other:

| Source | Contents | Retention | What it yields |
|---|---|---|---|
| `~/.claude/projects/**/*.jsonl` | Full conversations | Cleaned up periodically | AskUserQuestion answers, replies after Claude asks for input, reactions to Claude's actions, meta-feedback on how to work together |
| `~/.claude/history.jsonl` | User input only | Much longer | Meta-feedback on how to work together, strong corrections |

The two sources are deduplicated on the first 120 characters of the text. Text the system injects under the user role (reminders, skill instructions, context-continuation summaries) must be stripped out. It isn't the user's words, and letting it in would contaminate the core evidence: the user's verbatim quotes.

First run: 3.4M characters → 1,377 fragments (24% of the original).

### 2. Extraction (Claude / subagents, following `EXTRACT_GUIDE.md`)

Each fragment becomes a structured record. The core fields are `verbatim` (the exact quote) and `axis` (the trade-off axis this decision was made on, written as "A > B").
The extractor is **a transcriber, not an analyst**: judgement may appear only in the four fields axis / domain / reusable / confidence. When in doubt, drop it.
Expect to discard 40–60%. First run: 1,377 fragments → 784 records, with 8 subagents in parallel.

### 3. Quote verification (`dk verify`)

Every `verbatim` must appear exactly as written in the **user-side fields** of the original fragment. The first run: 96.6% exact matches; 13 were excerpts joined with ellipses (every piece is in the original, so they pass); 3 attributed the previous turn's words to the current turn; and **in 1, a subagent had added a sentence of its own to the quote**.
Let that last kind through and you get "the AI inventing principles on the user's behalf", the exact failure this whole method exists to prevent. So this step is a gate, and it can't be skipped.

### 4. Synthesis (main session, human in the loop)

`dk axes` condenses the records into a list of trade-off axes, one line per record, so you can read through all of them. Synthesis happens in the main session because:

- **Automatic clustering failed on Chinese.** Clustering trade-off axes by string similarity turned 784 records into 744 groups, with almost nothing merged: reword a Chinese phrase and its characters are completely different. Grouping by meaning can only be done by the model and a human.
- **Counterexamples need explaining, not a vote.** When opposite decisions show up on the same axis, don't go with the majority. Look for the hidden condition first ("go ahead when it only affects me, ask first when it affects others"). That's usually the entry's boundary.
- **Keep only what transfers.** Records marked `reusable: false` (tied to one project) stay out of the kernel. A new entry needs ≥3 independent pieces of evidence or must span ≥2 projects.

### 5. Entry-by-entry confirmation

The draft goes to the user, who reviews it entry by entry. The two most telling changes in the first round: "keep scope strictly limited" was corrected to "finish the job; raise extensions first"; and when two entries were found to have overlapping boundaries, the overlap was replaced with a three-question test. The AI couldn't have arrived at any of this on its own: **the final form of the kernel has to be confirmed by the person it describes**.

### 6. Provenance (`dk evidence`)

`kernel_map.jsonl` records which entry each decision belongs to and is used to generate `evidence-map.md`: for each entry, the number of records, how many projects they come from, the date range, and a summary of the motives.
When anyone later asks "on what grounds?" about an entry, this is where you trace it back to the quotes.

## Incremental review (`/decisions`)

The kernel isn't written in one go. Every few weeks, a review scans only the sessions since the last one and classifies each new decision as: covered / new pattern / contradiction / unnecessary ask.

- First incremental review: 288 fragments → 152 records: 150 covered, 2 unnecessary asks, 0 new patterns, 0 contradictions. Two subagents classified each record by asking "can the entry's questions directly lead to this decision?", and the main session re-checked the flagged ones. 98 of these records predate the final kernel, so this isn't a strict out-of-sample test.
- Second: 541 fragments → 330 records, with 2 new patterns and 1 contradiction. Two trial revisions were added; the remaining candidates went onto a watchlist (`watchlist.md`) until enough evidence builds up.

"Unnecessary ask" is the most direct measure of whether the kernel works: if the kernel can already derive the answer and the AI still asks, that entry's wording isn't actionable enough.

## Pitfalls

- **Treating the AI's synthesis as the user's principle.** A label the AI had come up with itself was written into long-term memory as one of the user's "hard rules", then cited again and again, even for architecture decisions, until it turned out the user had never said it. Hence: quotes must be verifiable, and inferences must be labelled.
- **Writing rules.** Every time you revise the kernel, ask yourself: is this a motive and a test, or has it turned back into "when X, do Y"?
- **Session logs get deleted.** By default Claude Code keeps session logs for only 30 days (`cleanupPeriodDays`, which you can raise in `~/.claude/settings.json`), and once they're gone you can't extract from them again. The corpus in `incr-*/` is the only copy of the original quotes. Don't delete it as if it were an intermediate file you can rebuild.
- **Adding entries to pad the count.** A decision that shows up only once goes into scenario-specific notes or the watchlist, not into the always-loaded kernel. The more always-loaded content there is, the harder it is for the AI to see what matters.

## Limitations

- The filtering regexes are tuned for Chinese conversations. English sessions work, but fewer decisions get caught; `filters.py` needs more patterns.
- It depends on Claude Code's local log format (`~/.claude/projects/*.jsonl`, `history.jsonl`). If the format changes, the scripts have to change with it.
- Extraction and synthesis depend on model quality and human confirmation. The scripts only handle the mechanical steps and the verification gate.
