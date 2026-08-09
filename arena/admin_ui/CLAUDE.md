# The director's console

Flask pages for running games. A player never sees this.

1. **Go through `AdminService`.** The console is an interface like any other, and imports nothing
   from `arena/engine`. [ADR 0001](../../docs/adr/0001-layered-architecture.md)
2. **Everything is behind the director check.** `before_request` gates the whole app.
3. **Anything that changes state is a POST.** Browsers prefetch links, and processing a round
   twice is not something to leave to chance.
4. **Templates render what they are handed.** Logic belongs in the route or the facade.

`AppFacade` is this UI's own vocabulary. Shared logic goes down into `arena/app`, not sideways.
