# How we write

Two audiences read this codebase: people, and agents asked to change it. Both are badly served by
padding.

## Prose

Docs, commit messages and anything else a human reads follow
[`.claude/skills/anti-ai-writing-style`](../.claude/skills/anti-ai-writing-style/SKILL.md). The
rules that bite hardest here:

- No em dashes. Commas, colons, brackets and full stops do the job.
- Never negate a framing to set up a claim. "It's not about X, it's about Y" says nothing that "Y"
  doesn't. Delete everything before the claim.
- Short paragraphs, uneven rhythm. Contractions. Say "you".
- Be specific. Name the file, quote the number, show the output.
- Never state a count of something you also list. "Three rules follow" is wrong the day a fourth
  arrives, and the sentence sits far enough from the list that nobody sees it happen. Write "the
  rules:" and let the list speak.
- Stop when the point is made.

## Comments in code

Sparse. A comment earns its place by explaining something the code can't say for itself: why this
way, what breaks otherwise, which trap is being avoided.

Don't narrate what the line does. Don't document what used to be there, git holds that. Don't
leave a comment where a better name would do.

If an explanation runs to a paragraph, it belongs in `docs/` or an ADR, and the code gets a
pointer:

```python
# Built on first use, inside the worker: see docs/deployment.md on preforking.
```

Docstrings: one line saying what the thing is for. Extra paragraphs only for a trap the next
reader will otherwise fall into, and then in the same voice as the docs.

## Pointing at things

Say a fact once. Everywhere else points at it. Two copies of one rule drift apart, and on the day
they disagree neither of them is the authority.

Cite code by a name that survives an edit above it: a symbol, `Component.decide`, or an anchor
comment, `# ADR0019-b`, dropped at the spot the prose is about. A line number is true until
somebody adds an import.

Cite an invariant by its wording, linked to
[the list](architecture.md#invariants). Numbers renumber.

`test/docs/test_references.py` fails on a reference that resolves to nothing. Run it as a module
and it also prints what still resolves today and will rot next.

## The split

Comments say *why this line*. Docs say *why this design*. ADRs say *why this design and not the
other one*. All three describe what is true now, and are edited when it stops being true.

An ADR holds the decision and the alternatives it beat, and nothing else. A backlog inside one
rots, and a description of how the code works today rots faster. Those belong in `work/TODO.md`
and in `docs/`.
