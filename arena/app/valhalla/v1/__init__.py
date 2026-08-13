"""Version 1 of the Valhalla format: `schema.json` is the definition, `from_engine.py` the way in.

Every document is validated against the schema on the way out and on the way back in.
See docs/adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md.
"""

import json
from pathlib import Path

import jsonschema

from arena.app.valhalla.v1 import from_engine

SCHEMA = json.loads((Path(__file__).parent / 'schema.json').read_text())
VERSION = SCHEMA['properties']['version']['const']


def write(replay, game: str) -> dict:
    """A played game as a v1 document, or nothing at all."""
    document = {'version': VERSION, 'game': game} | from_engine.document(replay)
    jsonschema.validate(document, SCHEMA)
    return document


def read(raw: dict, validate: bool = True) -> dict:
    """A document, once it is one. Held against the schema unless it already has been."""
    if validate:
        jsonschema.validate(raw, SCHEMA)
    return raw