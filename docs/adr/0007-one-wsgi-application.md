# 0007. One WSGI application serves everything

**Status:** Accepted

## Context

Three things need serving: a JSON API, a Svelte single-page app, and the Flask console.

The host is PythonAnywhere, which runs exactly one WSGI application per web app. It has no Node,
no build step and no way to run a second process.

## Decision

`arena/serve.py` is one WSGI callable that dispatches on the path:

    /api/...    the FastAPI app, run inside WSGI through a2wsgi
    /play/...   the built game UI, static files from game-ui/dist
    everything else, the Flask console

`game-ui/dist` is committed, because the host cannot build it.

In development the three run separately for hot reloading, with Vite proxying `/api` so the
browser still sees one origin.

## Consequences

One origin. The UI's relative `/api/...` calls need no configuration and there's no CORS in
production.

Deploying is `git pull` and a reload. A WSGI host needs one line and no other settings.

The UI build is a manual step before committing, and forgetting it ships stale JavaScript.

Committing `dist` means a delete and an add on every UI change, because the bundle filename carries
a content hash. That hash is also what makes browsers fetch new code.

Development and production differ in shape, so something can work under `arena-dev.sh` and break
under one origin. `arena-serve.sh` exists to catch that before deploying.

## Alternatives rejected

**Separate deployments.** The natural shape, and impossible on this host without paying for more
web apps. It also reintroduces CORS and a second address to configure.

**Serving the UI from a CDN or static host.** Another moving part, another origin, and the game is
private behind a site password anyway.

**Node at runtime.** Not available, and not worth requiring for files that never change between
deploys.
