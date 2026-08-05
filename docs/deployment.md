# Deployment

Starship Arena runs on PythonAnywhere as a single WSGI application. Deploying is `git pull` and a
reload. Nothing on the host's dashboard needs configuring, because every default in `arena/cfg.py`
is the deployed one and every path is anchored to the repository rather than the working
directory.

## One application, three jobs

`arena/serve.py` is a switchboard:

```mermaid
flowchart TD
    Req(["Request"]) --> Static{"a file in<br/>game-ui/dist ?"}
    Static -->|yes| Files["SharedDataMiddleware<br/><i>the game UI, at the root</i>"]
    Static -->|no| Dir{"path starts<br/>with /director ?"}
    Dir -->|yes| Flask["Flask console<br/><i>mounted</i>"]
    Dir -->|no| Api{"path starts<br/>with /api/ ?"}
    Api -->|yes| Fast["FastAPI<br/><i>through a2wsgi</i>"]
    Api -->|no| NF["404"]
```

The game is the site: it answers at the root. The console lives under `/director` and the API
under `/api`.

Development runs the same three parts as separate servers, which is what gives hot reloading:

```mermaid
flowchart TD
    subgraph dev ["Development: arena-dev.sh"]
        direction TB
        B1(["Browser"]) --> V["Vite :5173<br/><i>game UI, hot reload</i>"]
        V -->|"proxies /api"| U["Uvicorn :8000<br/><i>the API</i>"]
        B1 --> F["Flask :8080<br/><i>the console</i>"]
    end

    subgraph prod ["Deployed: one WSGI app"]
        direction TB
        B2(["Browser"]) --> W["arena/serve.py<br/><i>one origin</i>"]
    end
```

The browser sees one origin either way, because Vite proxies `/api`. Cookies ignore ports, so
signing in on 5173 also signs you in on 8080.

Three details in that file exist for reasons that aren't obvious from the code:

**The API is matched, not mounted.** Its routes already carry their own `/api` prefix. Mounting it
under one would strip the prefix and leave every route unreachable.

**The console is mounted, not matched.** Mounting sets `SCRIPT_NAME`, and that is what makes Flask
write `/director` in front of every URL it builds. No route in the console names its own prefix,
so moving it stays one line here.

**The root is rewritten to `/index.html`.** Static file serving has no notion of a directory
index, so the page has to be named. Vite builds with `base: './'`, which keeps the asset links
relative and the bundle servable from wherever it is put.

## The host preforks, with threads disabled

uWSGI loads the application in a master process and forks the workers. A fork keeps only the
thread that called it.

So anything holding a thread, an event loop or a connection pool must be built on first use inside
the worker, never at import. `a2wsgi` starts an event loop thread the moment its adapter is
constructed, which is why `arena/serve.py` builds that adapter lazily.

Get this wrong and every route times out at `504-loadbalancer` after 300 seconds, with
`HARAKIRI ON WORKER` in the server log. The application imports fine, which makes it look like a
routing problem.

The server log also says `*** Python threads support is disabled ***`. On Python 3.10 the GIL is
always initialised, so threads created inside a worker do run.

## No Node at runtime

`game-ui/dist` is committed, because the host has no build step. Rebuild it whenever the UI
changes:

```
npm run build --prefix game-ui
```

The bundle filename carries a content hash, so a deploy is a delete plus an add in git. That hash
is what makes a browser fetch the new code instead of serving the old from cache.

`index.html` is served with the same 12-hour cache as everything else, so a returning player can
keep an old page for a while after a deploy. Telling people to refresh is the current answer.

## Per-host settings

`secret.py` is gitignored, so each machine has its own. Both values are read by `arena/cfg.py`
from the environment first, then from `secret.py`:

```python
GAME_DATA_DIR = 'games'                                        # relative means inside the repo
SITE_URL = 'https://starship-arena-agfx.pythonanywhere.com'    # the address players use
```

`GAME_DATA_DIR` must never use `os.path.abspath()`. That resolves against the working directory,
which the host picks for itself, and a relative value is already anchored to the repository.

`SITE_URL` is read only where a login link is made whole: the CLI printing one, and the console's
player page. It's the address a link is *for*, not where this machine serves from, so the same
value belongs in both copies.

## Rolling out logins

The console refuses everyone until a director exists, so the order matters:

1. `git pull`
2. `./arena-link.sh <you> https://your.site --director` in a Bash console on the host
3. Open that link once

Reload before step 2 and the console shows its 403 page until you go back to the shell.

## The site password

The host has HTTP Basic Auth across the whole site. That's a bot moat, not identity: everyone who
plays shares it. Logins are what tell people apart, and they sit on top of it.
