# 0009. Every path is anchored to the repository

**Status:** Accepted

## Context

A host chooses its own working directory. uWSGI happens to `chdir` into the project, which hid two
cwd-dependent paths for a long time.

`secret.py` used `os.path.abspath('./games')`, which resolves against the working directory. The
ship type registry scanned a relative `'arena/engine/objects/registry'`, and when that missed it
produced an empty registry with no error at all: no ship types, no game creation, a blank
reference page.

## Decision

Every path is derived from `__file__`. `arena/cfg.py` computes `REPO_ROOT` that way, and a relative
setting is joined onto it.

Nothing calls `os.path.abspath()` on a relative path, and nothing globs a relative directory.

## Consequences

The application runs correctly from any working directory, which is what a host, a cron job and a
test all need.

A relative value in `secret.py` means "inside the repository", which is the safer way to write it.

The one place still resolving through the working directory is the CLI, deliberately: running it as
a module (`python -m arena.cli.main`) puts the repository on `sys.path`, and running it as a script
does not. `arena-link.sh` cds to the repository first for that reason.

## Alternatives rejected

**Relying on the host's chdir.** It works until it doesn't, and the failure is silent. An empty
registry raised nothing; it just quietly made a feature stop existing.

**An environment variable for the root.** One more thing to set correctly on every host, to
document, and to get wrong. `__file__` is always right and needs no configuration.
