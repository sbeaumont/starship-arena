# Where information lives

Six places a fact about the game can go. Each one says something different about what the fact
*is*, so picking one is a design decision rather than a matter of taste. The names below are meant
to be used out loud: "that's a model constant, not instance state" should settle an argument.

Two ADRs already pin parts of this: [0003](adr/0003-type-objects-for-machines.md) for type
objects, [0019](adr/0019-machines-drive-components-through-one-vocabulary.md) for the component
vocabulary. This page is the whole map.

## The six

### 1. Model constant

A number or flag every instance of a model shares, declared once where the model is declared.

```python
class H2545(ShipType):          # arena/engine/objects/registry/human.py
    max_speed = 45
    max_hull = 100

class RocketWarhead(Warhead):   # arena/engine/objects/components/warhead.py
    damage = 50
    range = 20
```

**The same idea lives in two different places**, which is the thing that catches people out. A
machine's constants sit on a separate **type object**, because twenty ship models share one `Ship`
class and something has to tell them apart. A component's constants sit on the **component class
itself**, because `RocketWarhead` and `SplinterWarhead` already are different classes, so a second
object holding their numbers would earn nothing.

A base class declares the neutral default: `MachineType.max_hull = 0`, `Component.range = 0`,
`Weapon.ammo = None`. The default has to be a true answer rather than a placeholder, and that is
what decides how far up it goes. `range = 0` sits on `Component` because a cloak really does reach
nowhere. `ammo = None` sits one level down on `Weapon` because a cloak has nothing to say about
ammunition at all.

Choose this when every one of a kind is identical and only a new kind changes it.

### 2. Model parts

What a model is assembled from. A property on the type object returning fresh components.

```python
@property
def weapons(self) -> list:
    return [Laser('L1', 180), Launcher('R1', Rocket(), 10)]
```

It builds a new list on every read, so it is not somewhere to look up a value. Asking a type for a
component in order to read a number off it constructs a throwaway to do it, and gets none of the
state the live component was carrying.

### 3. Instance state

What this one thing has, right now. Assigned in `__init__`, changed by play.

```python
self.hull = self._type.max_hull      # starts from the model constant, then diverges
self.score = 0
self.player = player
self.temperature = 0                 # Laser
self.ammo = initial_load             # Launcher
```

Choose this when two of the same model can differ, either because they were built differently
(`Laser('L1', 180)` versus `Laser('L2', 90)`) or because the round changed one of them.

Note what this buys that a model constant cannot: per-instance control. `Launcher.ammo` shadows
`Weapon.ammo = None` precisely so one launcher can run dry while its twin is full.

### 4. Derived answer

A question answered from what is already there, stored nowhere.

```python
@property
def is_player_controlled(self):
    return bool(self.player)

@property
def range(self) -> int:
    return max((c.range for c in self.all_components.values()), default=0)
```

Choose this whenever the answer can be worked out, because stored state that duplicates other
state is state that can disagree with itself.

### 5. Self-description

What a thing tells an interface it is. Abstract on the base, so a subclass cannot forget.

```python
type_name       'A2527'
category_name   'Ship', 'Starbase', 'Missile', 'Mine'
Event.kind      'internal', 'hit', 'explosion', 'scan'
Parameter.kind  'direction', 'number_in_range', 'on_off', 'object_name'
```

Interfaces key off these and never hold a list of names.
[ADR 0010](adr/0010-objects-describe-themselves.md).

The difference from a model constant is *enforcement*, and it follows from the question. Identity
is abstract so nobody can forget to answer. Capability gets a default so nobody has to care.

### 6. Reported dict

Name and value, so whatever reads it renders without knowing the names.

`status` is what changes during play. `description` is what a component is. `specs` is what a
model is. [ADR 0004](adr/0004-components-own-their-parameters.md).

```python
@property
def status(self):
    return {'Temperature': f"{self.temperature}/{self.max_temperature}"}
```

Choose this for anything a person reads. A new weapon appears in the condition panel and the
manual without either being told.

## Tags, and the line they must not cross

Some facts are too small to earn a field. Every object in space carries `tags`, a set of strings,
and something true of one object gets marked there instead:

```python
CLAIMED = 'claimed'          # in the module of the rule that sets and reads it

wreck.tags.add(CLAIMED)
if CLAIMED in wreck.tags: ...
```

Plain strings, so a new tag needs no central list edited and no ceremony. The well-known ones get
a constant next to the rule that uses them, so the name exists in one place and a typo is a
`NameError` rather than a condition that is quietly never true.

**A tag is a marker. It is there or it is not, and nothing reads a value off it. The moment you
want a value, it is instance state with a name.**

That line is what stops this from voiding the six above. A bag that takes anything is a bag
nobody has to think about, and then no fact ever gets asked which home it belongs in. Tags are
pickled with the world like any other state, so they are durable, not scratch.

## Picking one

In order, stopping at the first yes:

1. Can it be worked out from what is already there? **Derived answer**.
2. Is it how an interface tells one kind of thing from another? **Self-description**.
3. Is it a marker with no value, true of one object? **Tag**.
4. Can two of the same model differ? **Instance state**.
5. Is it a part rather than a value? **Model parts**.
6. Otherwise **model constant**, on the type object for a machine and on the class for a component.

Then, separately: does a person need to see it? If so it also goes in a **reported dict**, and
that is an addition rather than an alternative.

## Five ways to get it wrong

Shapes rather than instances, so they stay recognisable. Whichever ones are live at any moment are
tracked in [`../work/TODO.md`](../work/TODO.md).

**The reader names the fields.** A reported dict assembled somewhere other than the thing it
describes:

```python
def specs(model):
    return {'Hull': str(model.max_hull), 'Battery': str(model.max_battery)}
```

The list of names now lives away from the values, so a new model constant is invisible until
somebody edits a second file, and whoever assembles it has learned the engine's field names.
*Smell:* adding one fact means editing two places. *Fix:* the thing that owns the fact reports it,
and the caller loops.

**Reaching through an object's type.** `other._type.max_scan_distance` instead of asking `other`.
It works, and it couples the caller to a private attribute and to the type's field names, which is
the same coupling one layer down. *Smell:* a `._type.` in code that did not build the object.
*Fix:* the object answers, as a derived answer.

**A model constant that reads model parts.** Anything computing a type-level value out of
`self.weapons` builds throwaway components to do it, and then has to pick one, usually by index.
*Smell:* a subscript into a parts list. *Fix:* ask the live machine, which has the attached
components and their state.

**Naming one component instead of asking all of them.** `self.weapons['warhead']`,
`isinstance(c, Shields)`, `hasattr(self, ...)`. Each one is a place a new component is silently
ignored. *Smell:* a component's name or class appearing anywhere except the registry.
*Fix:* [ADR 0019](adr/0019-machines-drive-components-through-one-vocabulary.md).

**Storing what could be derived.** Two facts about the same thing can disagree, and eventually
will. *Smell:* an assignment that copies another attribute. *Fix:* a derived answer, unless
measurement shows the cost matters, which so far it never has.

## The list

Every information element in the engine, classified.

| element | kind | where |
|---|---|---|
| `base_type`, `max_hull`, `start_battery`, `mass` | model constant | `MachineType` |
| `max_speed`, `max_turn`, `max_delta_v`, `generators`, `max_battery`, `max_scan_distance` | model constant | `ShipType` |
| `mass`, `radius`, `is_immovable` | model constant, neutral default | `ObjectInSpace` |
| `radius`, `visibility`, `max_scan_distance` | model constant | `BodyType` |
| `energy_per_move`, `max_speed`, `max_turn`, `scan_cone` | model constant | `MissileType` |
| `slow_down_rate`, `energy_per_tick` | model constant | `MineType` |
| `damage`, `damage_type`, `falloff`, `range` | model constant | `Warhead` subclasses |
| `max_temperature`, `energy_per_shot`, `heat_per_shot` | model constant | `Laser` |
| `range`, `ammo`, `payload_type` | model constant, neutral default | `Component`, `Weapon` |
| `shield_break_score`, `quadrants` | model constant | `Shields` |
| `kill_score` | model constant | `Ship` |
| `weapons`, `defense`, `ecm`, `control` | model parts | type objects |
| `name`, `vector`, `moved_from`, `owner`, `faction`, `history`, `visibility` | instance state | `ObjectInSpace` |
| `hull`, `battery`, `all_components`, `_type` | instance state | `MachineInSpace` |
| `score`, `commands`, `player`, `generators` | instance state | `Ship` |
| `target` | instance state | `Missile` |
| `temperature`, `firing_arc`, `damage`, `reach` | instance state | `Laser` |
| `ammo`, `missile_number` | instance state | `Launcher` |
| `strengths`, `max_strengths` | instance state | `Shields` |
| `power`, `half_power` | instance state | `Cloak` |
| `pos`, `xy`, `heading`, `speed` | derived answer | `ObjectInSpace`, from `vector` |
| `is_player_controlled` | derived answer | `Ship`, from `player` |
| `range` | derived answer | `MachineInSpace`, from its components |
| `class_name`, `type_name`, `mass` | derived answer | `MachineInSpace`, from its type |
| `outer_defense`, `scans` | derived answer | `Ship` |
| `is_destroyed` | derived answer | every machine, from `hull` and `battery` |
| `type_name`, `category_name` | self-description | `ObjectInSpace`, abstract |
| `kind` | self-description | `Event`, `Parameter`, abstract |
| `status` | reported dict | every component |
| `description` | reported dict | every component |
| `specs` | reported dict | assembled in the services layer |
| `expected_parameters` | order surface | every component |
| `snapshot` | per-tick values | `ObjectInSpace`, see [ADR 0011](adr/0011-snapshots-hold-values.md) |

The order surface and the snapshot are their own things rather than a seventh kind.
`expected_parameters` returns `Parameter` objects that each carry a self-description (`kind`) and
answer `is_valid` and `value` for themselves. A snapshot is a reported dict frozen per tick,
holding values and never references.