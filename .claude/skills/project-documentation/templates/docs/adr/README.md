# Architecture decisions

One decision per file, numbered in the order accepted. Numbers are never reused or renumbered.

**An accepted ADR is never edited.** When a decision changes, write a new one that supersedes it
and mark the old `Superseded by NNNN`.

| | |
|---|---|
| [0001](0001-example.md) | Example |

## Template

```markdown
# NNNN. Title in the present tense

**Status:** Accepted

## Context
What forced a decision. The constraint, the problem, what was true at the time.

## Decision
What we do. Present tense, specific.

## Consequences
What this costs and what it buys, including what will annoy someone later.

## Alternatives rejected
What else was considered, and why it lost. Be concrete about the cost.
```

The last section carries the weight. "We use X" prevents nothing. "Y was rejected, because it cost
us Z last time" stops the next person, human or agent, proposing it again.
