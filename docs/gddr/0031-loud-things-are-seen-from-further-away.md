# 0031. Loud things are seen from further away

**Status:** Accepted

## Context

A scanner has a rating: how far it sees a standard object. What counts as standard is the question,
and until now only terrain had an answer. Every machine in the game was equally easy to find, so a
starbase the size of a town was as hard to spot as a fighter, and an explosion was seen only by
whoever was close enough to have been in the fight already.

That last one is what players feel. Two rounds of a first game can pass with an empty map: a full
circle sweep reaches 346, ships are worth nothing extra to a scanner, and a blast four hundred units
away leaves no trace. The game reads as empty rather than as dangerous.

## Decision

**Visibility is a percentage of the looker's reach, and it belongs to the model.** 100 is a standard
object. A scanner that reaches 346 finds a 300 at 1038 and a 500 at 1730. It is the same lever a
cloak pulls the other way, and the two multiply.

| | visibility | found by a 346 sweep | by a 30 degree beam |
|---|---|---|---|
| ship | 100 | 346 | 1200 |
| asteroid | 300 | 1038 | 3600 |
| starbase | 500 | 1730 | 5993 |
| explosion | 1000 | 1800 (passive) | — |

An explosion is checked against the observer's passive rating rather than a swept beam, because you
do not have to be looking to notice one. Those ratings run 156 to 330, so a blast carries 1560 to
3300 against a board about 1000 across: **everybody sees every explosion, wherever it happens.**

They see that it happened and where. What blew up, and whose it was, still has to be scanned.

## Consequences

The map has something on it. A player who has found nobody still watches blasts going off two
sectors away, which is a reason to fly somewhere rather than a reason to stop playing.

A starbase is a landmark. It cannot hide, it is found by anyone pointing a scanner near it, and a
faction planning around one plans in the open. That suits what a base is for and costs it nothing it
had, since it cannot run away in the first place.

Explosions being effectively global is a property of this board, not a rule. It stays a range, so a
scenario laid out over ten thousand units gets distant fighting back as a rumour rather than a
certainty, and nothing has to be rewritten for it.

Visibility is now a per-model number worth varying. The registry sets one value for every ship, and
[docs/ship-balance.md](../ship-balance.md) already argues that identical stats across twenty hulls
are the cheapest thing to spend. A heavy hull that is seen at 150 and a scout seen at 60 is a real
trade nobody has had to make yet.

## Alternatives rejected

**Visibility as an absolute detection range**, "you are scanned at 400", with the scanner reduced to
a multiplier. Convenient to read, and it puts the wrong number in the registry: there are twenty
targets for every sensor, and "3 times easier to see than standard" survives a scanner rewrite where
"seen at 1040" bakes today's Gravscan into every rock in the game. The two are the same arithmetic;
this is only about which factor gets written down.

**A square root on the multiplier**, so that ten times as loud is 3.2 times the range. It is what
physics does for something that emits, since signal falls off with the square of distance, and it
keeps large factors on the board. Rejected because it makes every number in the registry a thing you
have to convert before you can picture it, and the whole point of one linear column is that a
director can read it. If a factor is too big, the answer is a smaller factor.

**Taking the smaller of the scanner's reach and the object's visibility.** Two independent gates
sounds fair and plays flat: whichever is smaller always wins, so a better scanner buys nothing
against a quiet target and being loud buys nothing against a weak scanner. Half the levers in the
system do nothing at any given moment.

**Explosions visible everywhere by rule**, with no range at all. Simpler, and it throws away the
only knob that makes a big scenario feel bigger than a small one. A range that happens to exceed
this board does the same thing today and still means something tomorrow.