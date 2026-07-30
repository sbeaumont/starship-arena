"""One WSGI application serving the API, the game UI and the console. See docs/deployment.md.

Point a WSGI host at `arena.serve:application`. To try it locally: uv run python arena/serve.py
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
    """Built on first use, inside the worker: the host preforks. See docs/deployment.md."""
    return ASGIMiddleware(api_app)


def _dispatch(environ, start_response):
    """Send API calls to the API and everything else to the console.

    Matched rather than mounted: mounting would strip the /api the routes already carry."""
    if environ.get('PATH_INFO', '').startswith('/api/'):
        return _api()(environ, start_response)
    return admin_app(environ, start_response)


_static = SharedDataMiddleware(_dispatch, {'/play': GAME_UI_DIST})


def application(environ, start_response):
    """The entry point a WSGI host should be pointed at."""
    path = environ.get('PATH_INFO', '')
    if path == '/play':
        # Without the trailing slash the page's relative asset links resolve against the site
        # root and it comes up blank. See docs/deployment.md.
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