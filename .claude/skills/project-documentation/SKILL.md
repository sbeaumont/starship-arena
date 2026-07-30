---
name: project-documentation
description: Use when setting up or maintaining a project's documentation, writing architecture overviews or ADRs, deciding whether something belongs in a comment or a doc, or adding agent instruction files. Also when an agent keeps drifting from a project's conventions and the fix is written guardrails.
---

# Documentation that stops drift

Two readers: a person new to the code, and an agent asked to change it. Both want the same thing.
What the pieces are, and why they're that way rather than some other way.

An agent drifts because nothing told it the rule, or because what told it was too long to survive
in context. So the rules go where the work happens, short, with the reasoning one link away.

## The four places, and what each is for

| | |
|---|---|
| **Comments** | Why *this line*. Never what it does, never what used to be there |
| **`docs/`** | Why *this design*. Describes what is true now |
| **`docs/adr/`** | Why this design *and not the other one*. Frozen once accepted |
| **Instruction files** | The rules a change must not break. Short, absolute, per directory |
| **`TODO.md`** | What is not done yet |

The last one earns its place: **docs describe and decide, the backlog plans.** Intentions written
into documentation age badly, because nothing forces them to come true. Move anything aspirational
out.

## Write it clean

Documentation full of AI tells gets skimmed, and skimmed documentation stops nobody from drifting.
Apply [`anti-ai-writing-style`](../anti-ai-writing-style/SKILL.md) to every word here: docs, ADRs,
instruction files, commit messages.

The ones that matter most in documentation:

- No em dashes.
- Never negate a framing to set up a claim. "It's not X, it's Y" says nothing "Y" doesn't.
- Short paragraphs, uneven rhythm, contractions.
- Be specific. Name the file, quote the number, show the output.
- Stop when the point is made. No summary of what was just read.

A project without that skill available should carry the rules as a file of its own, so they travel.

## Layout

```
docs/
  README.md         what is here, and which file answers which question
  architecture.md   the layers, what lives where, how the main flows work
  glossary.md       the words the code uses
  <domain>.md       data formats, deployment, development, whatever the project needs
  adr/
    README.md       the format, and an index
    NNNN-title.md   one decision each
AGENTS.md           the rules, at the root
<subdir>/AGENTS.md  the rules that bind only that directory
TODO.md             the backlog
```

Name the instruction file whatever the tool reads: `CLAUDE.md` for Claude Code, `GEMINI.md` for
Gemini CLI, `AGENTS.md` for anything following that convention. One canonical file, copied or
symlinked to the names your tools want.

## The ADR format

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

Numbered in the order accepted. Numbers never reused, never renumbered.

**An accepted ADR is never edited.** A decision that changes gets a new ADR that supersedes it, and
the old one stays readable with `Superseded by NNNN`.

**The last section is the whole point.** "We use DTOs" prevents nothing. "Passing engine objects
upward was rejected, because that is what made the old report generator impossible to change" stops
the next person proposing it again. Without it you have a decision log, not a guardrail.

## Writing the instruction files

Short. Numbered. Absolute. Each rule links to the ADR that argues for it.

The root file holds what binds everywhere. A subdirectory's file holds only what binds there, so an
agent working in one area reads six lines instead of an architecture.

Test each rule by asking: would an agent that hadn't read this make the mistake? If not, cut it.
Aspirations, encouragement and descriptions of the codebase all belong elsewhere.

## Extracting rationale from code

A codebase that has been documented in docstrings has ADRs hiding in it. A module docstring
explaining a design, especially one that mentions what was considered and dropped, is an ADR
already written in the wrong place.

Move it, then leave a pointer:

```python
"""Base class for anything built: ships, starbases, missiles, mines.

A machine asks its type for anything about the model. See docs/adr/0003-type-objects.md."""
```

Watch for documentation that has gone stale in the move. Two modules with identical docstrings, or
one describing a feature that was removed, are the usual finds.

## Doing this with the author

The facts come from the code. Measure them, don't remember them: which package imports which, what
the real file format is, what the tests actually cover.

The intent comes from the author, and guessing it is how you write documentation that is wrong and
confident. Draft what you measured, mark what you inferred, and ask about the rest.

## Templates

`templates/` holds copyable skeletons, and doubles as a portable kit for another project or
another agent: zip it, unzip, point the agent at `AGENTS.md`. Include the prose rules in the zip,
since the target may have no skills mechanism.
