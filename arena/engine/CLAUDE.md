# The engine

The game itself. Knows nothing about interfaces, HTTP or storage locations.

1. **Import nothing from above.** Not `arena.app`, not `arena.api`, not `arena.admin_ui`.
2. **Stay deterministic.** No clock, no random numbers in round processing.
   [ADR 0002](../../docs/adr/0002-deterministic-rounds.md)
3. **The order objects are processed in must never change the outcome of a tick.** Landing a hit
   and resolving a kill are separate: hits land as they happen and are simultaneous, the destroyed
   are cleared only when the tick ends. So two gunners can overkill one missile and neither wasted
   the shot, and a warhead still goes off inside a ship that died earlier in the same tick. Both
   are intended. Anything that makes one object's action depend on whether another has already
   acted breaks this, and it is the invariant that
   [order never changes a tick's outcome](../../docs/architecture.md#invariants).
4. **Snapshots hold values, never references.** A snapshot that shares a mutable object records
   how the round ended, once per tick.
5. **Objects answer for themselves.** `type_name`, `category_name`, `Event.kind`, `Parameter.kind`
   are abstract properties each subclass implements. Never a class attribute, never inspection of
   the class hierarchy, never matching on a name.
   [ADR 0004](../../docs/adr/0004-components-own-their-parameters.md)
6. **A machine asks all its components the same questions.** Iterate `all_components`; never index
   by name, never `isinstance`, never `hasattr`. A new question goes on `Component` with a neutral
   default that the components it means something for shadow, the way `Weapon.ammo` does. Name it
   for what is asked, not for the component that prompted it.
   [ADR 0019](../../docs/adr/0019-machines-drive-components-through-one-vocabulary.md)
7. **A refused order is feedback.** Record an `InternalEvent` rather than silently doing nothing.
8. **Fail loudly.** Bad input raises. No clamping, no silent fallbacks; if something needs
   clamping, the caller has a bug.
9. **A race is lore, and the engine must not know it.** The five registry modules named after
   races are a filing convention; nothing reads their names. Who flies what is a scenario's
   business. [ADR 0021](../../docs/adr/0021-scenarios-sit-in-the-services-layer.md)

A model is a type object in `objects/registry/`, and the registry loads by reflection.
[ADR 0003](../../docs/adr/0003-type-objects-for-machines.md)

**Before adding a new piece of information anywhere, read
[docs/information.md](../../docs/information.md).** Six places a fact can live, what each one
claims, and how to choose. Getting it wrong is not a style slip: a model constant says no two
ships can ever differ, and instance state says they can.

**The model is finished until you have proved otherwise.** What an interface needs is nearly always
already here under another name, so grep for it and say what you found before proposing a field.
The neutral default in rule 6 is a licence for `Component` and for nothing else: an event says what
it is by being a subclass, so a beam is a `BeamEvent` rather than a flag on `Event`, and both its
ends were already on `HitEvent` as `source` and `target`. A property added to an abstract base
claims every subclass has an answer, which is a claim about the whole model made while looking at
one caller.
