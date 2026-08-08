# Architecture decisions

How the thing is built: layers, storage, components, hosting, UI technology.

**Decisions about how the game is played live in [`../gddr/`](../gddr/)**, and the two share one run
of numbers, so a reference to 0020 is unambiguous and nothing is ever renumbered. A gap is a number
the other family holds, or one that merged into another record: 0024 is inside 0023.

One decision per file, numbered in the order they were accepted. Numbers are never reused and
never renumbered.

**An ADR says what we do now.** When the decision moves, edit the ADR to say the new one and put
what it replaced into `Alternatives rejected`, which is where a reason worth remembering belongs.
Git holds every earlier version.

A record of a decision we no longer take is worse than no record. It reads as current, to a person
skimming and to an agent that has no way to tell, and the argument inside it argues for the thing
we already moved away from.

| | |
|---|---|
| [0001](0001-layered-architecture.md) | Layered architecture with a services seam |
| [0002](0002-deterministic-rounds.md) | Rounds are deterministic |
| [0003](0003-type-objects-for-machines.md) | Type objects instead of a class per ship |
| [0004](0004-components-own-their-parameters.md) | Components own their parameters and their status |
| [0005](0005-commands-validated-before-execution.md) | Commands are validated before they run |
| [0006](0006-game-data-is-files.md) | Game data is files, and the derived part is disposable |
| [0007](0007-one-wsgi-application.md) | One WSGI application serves everything |
| [0008](0008-stateless-and-lazy.md) | Nothing is built at import, nothing held between requests |
| [0009](0009-paths-anchored-to-the-repository.md) | Every path is anchored to the repository |
| [0010](0010-objects-describe-themselves.md) | Objects describe themselves through abstract properties |
| [0011](0011-snapshots-hold-values.md) | Snapshots hold values, never references |
| [0014](0014-magic-link-logins.md) | Logins are a magic link per person |
| [0015](0015-svelte-without-a-framework.md) | Svelte 5 and Vite, without SvelteKit |
| [0016](0016-the-view-lives-in-the-url.md) | The whole view lives in the URL |
| [0017](0017-two-svg-layers.md) | The map is two SVG layers, world and screen |
| [0019](0019-machines-drive-components-through-one-vocabulary.md) | Machines drive their components through one vocabulary |
| [0021](0021-scenarios-sit-in-the-services-layer.md) | Scenarios sit in the services layer |
| [0022](0022-a-game-directory-moves-between-three-places.md) | A game directory moves between three places |
| [0023](0023-a-tick-advances-by-encounters.md) | A tick advances by encounters, and contact transmits an impulse |
| [0026](0026-a-game-keeps-a-journal.md) | A game keeps a journal of its processing |
| [0027](0027-the-server-keeps-one-timezone.md) | The server keeps one timezone, and shifting is a UI concern |

## Template

```markdown
# NNNN. Title in the present tense

**Status:** Accepted

## Context
What forced a decision. The constraint, the problem, what was true at the time.

## Decision
What we do. Present tense, specific.

## Consequences
What this costs and what it buys. Including the bits that will annoy someone later.

## Alternatives rejected
What else was considered, and why it lost. Be concrete about the cost of the alternative.
```

The last section carries the weight. "We use DTOs" prevents nothing. "Passing engine objects
upward was rejected, because that is what made the old report generator impossible to change"
stops the next person, human or agent, from proposing it again.