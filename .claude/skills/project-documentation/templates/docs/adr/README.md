# Architecture decisions

One decision per file, numbered in the order accepted. Numbers are never reused or renumbered.

**An ADR says what you do now.** When the decision moves, edit the ADR and put what it replaced
into `Alternatives rejected`. Version control holds the history.

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
