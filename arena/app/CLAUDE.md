# Application services

The seam every interface sits on. [ADR 0001](../../docs/adr/0001-layered-architecture.md)

1. **Return DTOs, never engine objects.** Plain dataclasses, no framework imports.
2. **Nothing leaves here that names storage.** No `GameDirectory`, no paths, no pickles.
3. **No HTTP.** Status codes, cookies and routing belong in `arena/api`.
4. **Hold no state between calls.** The host runs several worker processes, so anything cached in
   memory is a coin flip on which one answers. Read from disk each time.

`GameService` is player-facing and restricted. `AdminService` is the director's.
