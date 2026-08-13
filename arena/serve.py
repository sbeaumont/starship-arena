"""One WSGI application serving the game UI, the API and the console. See docs/deployment.md.

Point a WSGI host at `arena.serve:application`. To try it locally: uv run python -m arena.serve
"""

import os
from functools import cache

from a2wsgi import ASGIMiddleware
from werkzeug.exceptions import NotFound
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware

from arena.admin_ui.app import app as admin_app
from arena.api.app import app as api_app
from arena.cfg import GAME_UI_DIST


@cache
def _api():
    """Built on first use, inside the worker: the host preforks. See docs/deployment.md."""
    return ASGIMiddleware(api_app)


def _dispatch(environ, start_response):
    """Whatever the game UI has no file for: the API, or the game UI itself.

    Matched rather than mounted: mounting would strip the /api the routes already carry.

    Anything else is a view rather than a file, since the whole view is in the path
    (ADR 0016), so the app is served and reads the path itself. A path whose last segment
    names a file is a file that is missing, and that is a 404 rather than a page."""
    path = environ.get('PATH_INFO', '')
    if path.startswith('/api/'):
        return _api()(environ, start_response)
    if '.' in path.rsplit('/', 1)[-1]:
        return NotFound()(environ, start_response)
    environ['PATH_INFO'] = '/index.html'
    return _static(environ, start_response)


# The console is mounted, and that is what makes Flask put /director in front of every URL it
# builds. The game UI is the site itself, so it answers from the root and lets through anything
# it holds no file for.
_console = DispatcherMiddleware(_dispatch, {'/director': admin_app})
_static = SharedDataMiddleware(_console, {'/': GAME_UI_DIST})


def application(environ, start_response):
    """The entry point a WSGI host should be pointed at."""
    if environ.get('PATH_INFO', '') == '/':
        # Static file serving has no notion of a directory index, so name the page.
        environ['PATH_INFO'] = '/index.html'
    return _static(environ, start_response)


if __name__ == '__main__':
    from werkzeug.serving import run_simple

    if not os.path.isdir(GAME_UI_DIST):
        raise SystemExit(f"No built game UI at {GAME_UI_DIST}. "
                         f"Run: npm run build --prefix game-ui")
    port = int(os.environ.get('PORT', 8080))
    print(f"game   http://localhost:{port}/\n"
          f"admin  http://localhost:{port}/director/\n"
          f"api    http://localhost:{port}/api/health")
    run_simple('0.0.0.0', port, application)
