# 0008. Nothing is built at import, and nothing is held between requests

**Status:** Accepted

## Context

The host runs uWSGI in preforking mode with 2 workers. It loads the application in a master
process, then forks. A fork keeps only the thread that called it.

Two things follow, and both were learned the hard way.

`a2wsgi` starts an event loop in a background thread the moment its adapter is constructed. Built
at import, that loop stayed in the master. Every worker then blocked forever waiting on it, and
every route timed out at `504-loadbalancer` after 300 seconds. The application imported fine, which
made it look like a routing problem.

Separately, each worker is its own process with its own copy of every module global, and workers
get recycled. Anything cached in memory is a coin flip on which worker answers.

## Decision

Nothing that holds a thread, an event loop or a pool is constructed at import time. Build it on
first use, inside the worker.

No application data is held between requests. Every request reads from disk.

## Consequences

`arena/serve.py` builds its ASGI adapter through a cached function rather than at module level.

The services layer constructs a fresh `GameDirectory` per call and re-reads the pickles. That's
slower and it's correct, which at this scale is the right trade.

The obvious optimisation, caching loaded games in memory, is off the table. If reads ever get slow
the answer is a shared store, not a process-local cache. A cache here fails intermittently
depending on which worker answers, which is the worst kind of bug to chase.

## Alternatives rejected

**Enabling threads on the host.** PythonAnywhere gives no way to pass uWSGI flags, and it wouldn't
help: the problem is the fork, not thread support.

**Caching loaded games per process.** Tempting, since unpickling on every request is the obvious
cost. It's wrong with more than one worker, and it fails in a way that looks like flakiness rather
than a bug.
