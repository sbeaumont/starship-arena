# 0033. Colour answers one question

**Status:** Accepted

## Context

The map grew its colours one feature at a time. Red arrived for enemy contacts. Then wrecks and
breaches took it, because damage is red. Then the shot you are planning took it, because weapons
are red. Then a fired beam took it too.

By the time beams were drawn, red was answering three different questions at once: whose ship that
is, what got hurt, and what your own guns are doing. **Your own gunfire was drawn in the enemy's
colour.** Explosion orange sat right beside it at `#ff9d4a`, so the whole violent half of the board
was one smear, while the quiet half was three shades of blue.

A player reads friend against foe before they read anything else, and that was the reading the map
made hardest.

## Decision

A mark on the map answers one of three questions, and no colour answers two of them.

**Whose it is.** Hue carries allegiance and nothing else.

| | | |
|---|---|---|
| `--amber` | `#ffb454` | yours |
| `--cyan` | `#57d8ff` | a faction mate's |
| `--foe` | `#ff4d5e` | theirs, and nothing else on the board is this red |
| slate | `#7b86a4`, `#2b3648` | terrain, and anything nobody owns |

**Which of your plans your hand is on.** Only your own courses split, and only the line splits: a
ship of yours is amber whether or not it is the one selected, so allegiance still reads off the
marker while the lines say which plan is live.

| | | |
|---|---|---|
| `--amber` | `#ffb454` | the course you are dragging |
| `--laid` | `#57d98a` | a course of yours already laid in |
| `--cyan` | `#57d8ff` | a faction mate's saved plan, the colour they already are |

**What happened to it.** One band, the orange a blast already used, and two hues inside it for harm
that is not ordinary. A blast says what it carried, and a kind nobody has heard of is drawn as an
ordinary one rather than not drawn.

| | | |
|---|---|---|
| `--hit` | `#ff9d4a` | a kill, a breach, a blow landing, and the explosion itself |
| `--kill` | `#ffdcae` | the heart of the burst that marks one |
| `--nanocyte` | `#7ef0a0` | a blast that eats a hull instead of opening it |
| `--emp` | `#8fb4ff` | a blast that takes the lights out |

**What a weapon did.** Light, which is no hue at all.

| | | |
|---|---|---|
| `--beam` | `#fff2cc` | a shot: dashed and dim while planned, solid and bright once fired |

**What the interface is telling you.** A pair, and neither of them draws anything in space.

| | | |
|---|---|---|
| `--ok` | `#57d98a` | yes: orders saved, a gauge that is healthy, a base that restocked you |
| `--warn` | `#ff5d6c` | no: a rejected command, a pinned limit, an empty magazine |

`--ok` and `--laid` hold the same value today and are two tokens on purpose. One is a course on the
map and one is a word in a panel, so the day either wants tuning, it moves without dragging the
other with it.

The replay has no friend and no foe, so it rings factions in payload order and the side being
watched comes first: amber, then red, then cyan, green, magenta. The first two mean a game of two
sides reads there the way it reads on the map. None of the five is the blast orange or the beam's
light, because a faction is not something that happened.

## Consequences

A firefight is legible at a glance. Red ships, pale light between them, orange where it landed.

Anything new has to say which of the three questions it belongs to before it gets a colour. Something
that answers two is two marks, drawn separately. That is the rule the next weapon will be tested
against.

Retuning is one line. Every hostile mark reads `--foe`, so the eight places that used to hold their
own literal now move together.

**`--laid` is invisible to most players, and that is correct.** A course is only drawn in it when you
command a ship you are not currently editing, so a single-ship commander never sees green on the map
at all. Green appearing is the map telling you that you have a fleet.

**A beam cannot be coloured by whoever fired it**, and it never will be. Being noticed is what
[0031](0031-loud-things-are-seen-from-further-away.md) grants, and a witness gets the two ends
without the two names, the same way a blast tells you where and never who. So a beam belongs to the
event band by necessity as well as by taste.

The cost is colour blindness. Enemy red against your green courses is the classic confusion pair,
and amber sits near red for a deuteranope too. Form carries the difference today: an enemy is a
filled marker, a course is a thin line, a beam is thinner and brighter. If somebody cannot read it,
the lever is marker shape, which `markers.js` already varies by category, and the palette can stay.

## Alternatives rejected

**Violet for the enemy, freeing red for damage.** Tried, built and reverted inside an hour. Cyan
already holds your own side, so violet lands beside it and the board goes blue: at marker size
`#c98cff` and `#57d8ff` stop being separable, and the distinction a player reads first becomes the
hardest one on the map. Red for the enemy is a convention worth more than a tidy split of the warm
end. The thing to move was your own gunfire, which had no convention behind it at all.

**Colouring a beam by whoever fired it.** Semantically the best answer, since a shot does belong to
a ship, and the data forbids it. A beam is handed to everybody within range and carries no names, so
the browser holding one has no idea whose it is. Colouring by owner means shipping the names to
every witness, which hands out an unscanned ship's identity for free and breaks
[0013](0013-fog-of-war-from-scans.md).

**Giving damage a hue of its own, away from explosions.** One more colour to tell apart, for a
distinction nobody needs: a wreck is what a blast leaves behind, and a breach is a blast getting
inside. They read as one thing because they are one thing.

**One green token for both the course and the panels**, since the value is the same. It is the shape
this whole record exists to prevent, one step earlier: a colour that answers two questions is fine
right up to the morning somebody wants the map's green a shade cooler and quietly restyles every
"saved" in the game.