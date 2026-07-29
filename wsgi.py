# The WSGI entry point, kept here so it lives with the code it loads. PythonAnywhere keeps its
# own copy in the web app's dashboard; paste the contents below into it.
#
# `arena.serve` serves everything from this one application:
#   /api/...   the JSON API
#   /play/...  the built game UI (static files from game-ui/dist, committed to the repo)
#   the rest,  the Flask admin and director pages
#
# Nothing else needs configuring on the host: every default in arena/cfg.py is the deployed one
# and all paths are anchored to the repository rather than the working directory.

import sys

# add your project directory to the sys.path
project_home = '/home/AgFx/starship-arena'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# import the application; it must be called "application" for WSGI to work
from arena.serve import application  # noqa