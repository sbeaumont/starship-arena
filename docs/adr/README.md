# Architecture decisions

One decision per file, numbered in the order they were accepted. Numbers are never reused and
never renumbered.

**An accepted ADR is never edited.** When a decision changes, write a new one that supersedes it
and mark the old one `Superseded by NNNN`. The trail is the point.

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
| [0012](0012-open-information.md) | Ship statistics are public |
| [0013](0013-fog-of-war-from-scans.md) | Fog of war is faction-shared and derived from scans |
| [0014](0014-magic-link-logins.md) | Logins are a magic link per person |
| [0015](0015-svelte-without-a-framework.md) | Svelte 5 and Vite, without SvelteKit |
| [0016](0016-the-view-lives-in-the-url.md) | The whole view lives in the URL |
| [0017](0017-two-svg-layers.md) | The map is two SVG layers, world and screen |
| [0018](0018-planning-as-a-jointed-chain.md) | A course is planned by dragging a jointed chain |
| [0019](0019-machines-drive-components-through-one-vocabulary.md) | Machines drive their components through one vocabulary |
| [0020](0020-explosions-do-not-take-sides.md) | An explosion damages everything in range |

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