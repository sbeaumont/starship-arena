"""Failures that cross the seam: raised in the engine, answered by an interface.

Here rather than in either, because the engine imports nothing above it and an interface reaches
nothing below the services layer, so neither can name the other's exception.
See docs/architecture.md."""


class UnreadableWorld(Exception):
    """A saved round this code can no longer read. Regenerating the game is the cure."""

    def __init__(self, game: str, file_name: str):
        super().__init__(f"{game}: {file_name} was saved by code this no longer matches.")
        self.game = game
        self.file_name = file_name