# 0013. Fog of war is faction-shared and derived from scans

**Status:** Accepted

## Context

Ships scan. A scan records that a ship saw something, where it was, how far away and in which
direction.

Two questions follow. Who gets to see a scan, and what can be told from it.

## Decision

**Fog of war is shared across a faction.** A player's picture pools every scan from every ship in
their faction during that round. Allies are ground truth, not contacts.

**A contact is a track of sightings**, in order, with no projection. The most recent point is the
last known position.

**Course is inferred client-side from the last two sightings.** A `ScanEvent`'s heading is the
bearing from scanner to target, not the target's own heading. The engine never reveals that.

A contact seen once has no known course and is drawn without direction.

## Consequences

Faction mates coordinate without copying screenshots to each other, which is what they did before.

What the map shows is honestly what was observed. A course arrow means "it moved this way between
two sightings", not "it is heading this way".

Asking for an earlier round gives the picture as it was known then, because the scans are in the
history.

A crowded round is genuinely crowded: 94 contacts in one round of a real game, most of them
transient ordnance. The map needs filtering, which is why the layer toggles exist.

## Alternatives rejected

**Per-ship fog of war.** More faithful, and it makes a fleet unplayable in one view, which is the
view the game is built around.

**Exposing the scanned object's real heading.** The engine has it. Handing it over would turn a
track of observations into perfect telemetry, and the uncertainty is where the tactics live.
