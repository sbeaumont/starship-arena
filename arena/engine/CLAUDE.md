# The engine

The game itself. Knows nothing about interfaces, HTTP or storage locations.

1. **Import nothing from above.** Not `arena.app`, not `arena.api`, not `arena.admin_ui`.
2. **Stay deterministic.** No clock, no random numbers in round processing.
   [ADR 0002](../../docs/adr/0002-deterministic-rounds.md)
3. **Snapshots hold values, never references.** A snapshot that shares a mutable object records
   how the round ended, once per tick.
4. **Objects answer for themselves.** `type_name`, `category_name`, `Event.kind`, `Parameter.kind`
   are abstract properties each subclass implements. Never a class attribute, never inspection of
   the class hierarchy, never matching on a name.
   [ADR 0004](../../docs/adr/0004-components-own-their-parameters.md)
5. **A machine asks all its components the same questions.** Iterate `all_components`; never index
   by name, never `isinstance`, never `hasattr`. A new question goes on `Component` with a neutral
   default that the components it means something for shadow, the way `Weapon.ammo` does. Name it
   for what is asked, not for the component that prompted it.
   [ADR 0019](../../docs/adr/0019-machines-drive-components-through-one-vocabulary.md)
6. **A refused order is feedback.** Record an `InternalEvent` rather than silently doing nothing.
7. **Fail loudly.** Bad input raises. No clamping, no silent fallbacks; if something needs
   clamping, the caller has a bug.

A model is a type object in `objects/registry/`, and the registry loads by reflection.
[ADR 0003](../../docs/adr/0003-type-objects-for-machines.md)
