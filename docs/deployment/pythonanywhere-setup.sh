#!/usr/bin/env bash
#
# Sets up the virtualenv the PythonAnywhere web app needs. Run it from a Bash console there,
# after a git pull:
#
#     ~/starship-arena/pythonanywhere-setup.sh
#
# It is safe to run again; an existing virtualenv is reused and its packages brought up to date.
#
# Note it uses `python -m venv` rather than `mkvirtualenv`: virtualenvwrapper's commands are
# shell functions that only exist in an interactive shell, not in a script. The virtualenv still
# lands in ~/.virtualenvs, which is where virtualenvwrapper and the Web tab look, so the tab
# accepts the bare name.
#
set -euo pipefail

# Must match the Python the web app is configured for; a virtualenv on a different version will
# not work. Override either of these from the command line if needed.
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
VENV_NAME="${VENV_NAME:-starship-arena}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HOME/.virtualenvs/$VENV_NAME"
# PythonAnywhere keeps its interpreters here; PYTHON can be set outright if a host differs.
PYTHON="${PYTHON:-/usr/bin/python$PYTHON_VERSION}"

if [ ! -x "$PYTHON" ]; then
    echo "There is no $PYTHON here." >&2
    echo "Set PYTHON_VERSION to whatever your web app uses, e.g." >&2
    echo "    PYTHON_VERSION=3.11 $0" >&2
    exit 1
fi

echo "project : $PROJECT_DIR"
echo "python  : $PYTHON ($("$PYTHON" -V 2>&1))"
echo "venv    : $VENV_DIR"
echo

if [ -d "$VENV_DIR" ]; then
    echo "Virtualenv already exists, installing into it."
else
    mkdir -p "$HOME/.virtualenvs"
    "$PYTHON" -m venv "$VENV_DIR"
    echo "Created the virtualenv."
fi

"$VENV_DIR/bin/pip" install --quiet --upgrade pip

# A virtualenv starts empty, so everything the app imports has to go in - not only the packages
# PythonAnywhere preinstalls for its system Pythons. uvicorn is deliberately absent: it only
# runs the development API server. If WeasyPrint fails to build or work here, pin it to the
# version this host is happy with rather than chasing the newest.
echo
echo "Installing packages..."
"$VENV_DIR/bin/pip" install \
    flask jinja2 weasyprint pillow wtforms \
    fastapi pydantic a2wsgi

echo
echo "Installed:"
"$VENV_DIR/bin/pip" list 2>/dev/null \
    | grep -iE '^(flask|jinja2|weasyprint|pillow|wtforms|fastapi|starlette|pydantic|a2wsgi)[[:space:]]' \
    | sed 's/^/  /' || true

# Loading the application here catches a missing package or a broken path now, rather than as a
# 502 after reloading the web app.
echo
echo "Checking that the application loads..."
"$VENV_DIR/bin/python" -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from arena.serve import application
print('  arena.serve imported, application is ready')
"

cat <<EOF

Done here. Three things left, on the Web tab:

  1. Virtualenv:  $VENV_NAME
  2. WSGI file :  replace its contents with those of
                  $PROJECT_DIR/wsgi.py
                  (make sure project_home reads $PROJECT_DIR)
  3. Reload the web app.

Then: the game UI at /, the admin pages at /director/ and the API at /api/health
EOF