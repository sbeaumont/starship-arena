# AGENTS.md

Rules for working in this repository. The reasoning lives in [`docs/`](docs/); read the page for an
area before changing it. Subdirectories have their own file with the rules that bind only them.

> Copy or symlink this to whatever your tool reads: `CLAUDE.md`, `GEMINI.md`, `.cursorrules`.

<!-- One paragraph: what this project is. -->

## Never break these

<!-- Numbered, absolute, each linking to the ADR that argues for it. Test every line by asking:
     would an agent that had not read this make the mistake? If not, cut it. -->

1.
2.
3.

## How to work here

1. **Measure, don't remember.** Check what the code does before describing it. Run the thing.
   Paste the real output.
2. **Say what you did and what you skipped.** If tests fail, show them. If part of the task is
   incomplete, name it.
3. **Ask when intent is unclear.** Guessing produces confident, wrong work. Facts come from the
   code, intent comes from the author.
4. **Change what was asked for.** Notice other problems, mention them, leave them alone.
5. **Verify before claiming.** "Done" means it ran.

## How to write

Comments say *why this line*, never what it does and never what used to be there. Git holds
history. A paragraph of explanation belongs in `docs/` with a one-line pointer from the code.

Prose follows [`writing-style.md`](writing-style.md). Docs that read as machine-written get
skimmed, and skimmed docs stop nobody from drifting.

## Keep it simple

No abstraction without a present need. No dependency that isn't earning its place. No defensive
programming: fail loudly rather than fall back silently, because a silent fallback hides the bug
that caused it.

## Commands

```bash
# build, test, run
```
