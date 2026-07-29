"""One WSGI application serving the whole game, for hosts that run a single WSGI app.

    /api/...   the JSON API (FastAPI, an ASGI app, run through an adapter)
    /play/...  the built game UI - static files, no Node involved
    everything else, the Flask admin and director pages

Because it is all one origin, the game UI's relative /api/... calls just work and no CORS is
needed. In development the three are run separately instead (see arena-dev.sh), which is what
gives hot reloading.

For a WSGI host, point it at `arena.serve:application`. To try it locally:

    uv run python arena/serve.py
"""

import os
from functools import cache

from a2wsgi import ASGIMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware

from arena.admin_ui.app import app as admin_app
from arena.api.app import app as api_app
from arena.cfg import GAME_UI_DIST


@cache
def _api():
    """The API as a WSGI app, built on first use rather than at import.

    a2wsgi runs the ASGI app on an event loop in a thread of its own, started the moment the
    adapter is constructed. A preforking host (uWSGI, so PythonAnywhere) imports the
    application in its master process and then forks the workers, and a fork inherits only the
    thread that called it - so an adapter built at import time leaves its loop behind in the
    master, and the worker that has to answer waits on it until the host kills the request.
    Building it on first use puts the thread in the process that uses it."""
    return ASGIMiddleware(api_app)


def _dispatch(environ, start_response):
    """Send API calls to the API and everything else to the admin pages.

    The API's routes already carry their own /api prefix, so the path is matched rather than
    mounted under one: mounting would strip the prefix and leave the routes unreachable."""
    if environ.get('PATH_INFO', '').startswith('/api/'):
        return _api()(environ, start_response)
    return admin_app(environ, start_response)


_static = SharedDataMiddleware(_dispatch, {'/play': GAME_UI_DIST})


def application(environ, start_response):
    """The entry point a WSGI host should be pointed at."""
    path = environ.get('PATH_INFO', '')
    if path == '/play':
        # The page links its assets relatively. Without the trailing slash a browser resolves
        # those against the site root and asks for /assets/..., which is nothing, so the page
        # comes up blank - redirect instead of serving it from here.
        target = environ.get('SCRIPT_NAME', '') + '/play/'
        query = environ.get('QUERY_STRING', '')
        if query:
            target = f'{target}?{query}'
        start_response('301 Moved Permanently',
                       [('Location', target), ('Content-Length', '0')])
        return [b'']
    if path == '/play/':
        # Static file serving has no notion of a directory index, so name the page.
        environ['PATH_INFO'] = '/play/index.html'
    return _static(environ, start_response)


if __name__ == '__main__':
    from werkzeug.serving import run_simple

    if not os.path.isdir(GAME_UI_DIST):
        raise SystemExit(f"No built game UI at {GAME_UI_DIST}. "
                         f"Run: npm run build --prefix game-ui")
    port = int(os.environ.get('PORT', 8080))
    print(f"admin  http://localhost:{port}/\n"
          f"game   http://localhost:{port}/play/\n"
          f"api    http://localhost:{port}/api/health")
    run_simple('0.0.0.0', port, application)