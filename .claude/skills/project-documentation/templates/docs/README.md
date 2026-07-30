# Documentation

Written for two readers: someone new to the code, and an agent asked to change it. Both want the
same thing: what the pieces are, and why they're that way rather than some other way.

| | |
|---|---|
| [architecture.md](architecture.md) | The layers, what lives where, how the main flows work |
| [glossary.md](glossary.md) | The words the code uses |
| [adr/](adr/) | One decision per file, including what was rejected |
| [../writing-style.md](../writing-style.md) | How to write all of this |

## How these fit together

**This directory describes and decides. [`TODO.md`](../TODO.md) plans.** Documentation that
describes intentions ages badly, because nothing forces it to come true.

**The overview describes; the ADRs argue.** So the overview can be rewritten freely while the
reasoning stays put.

**An ADR is never edited once accepted.** A decision that changes gets a new one that supersedes
it, and the old stays readable. The trail is the point.

**Instruction files carry the rules.** `AGENTS.md` at the root for what binds everywhere, one per
subdirectory for what binds there. Short enough to survive in an agent's context.
