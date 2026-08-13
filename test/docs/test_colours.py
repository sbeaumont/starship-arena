"""A colour with a meaning is a token, and a component spells it `var(--name)`.

The rule and the meanings are in docs/gddr/0033-colour-answers-one-question.md. This only guards
the half a grep can see: that nothing restates a token's value instead of naming it. A structural
hex, a panel background or a grid line, means nothing to the game and is left alone."""

import re
import unittest
from pathlib import Path

from arena.cfg import REPO_ROOT
from test.docs.test_references import walk

TOKENS = Path(REPO_ROOT) / 'game-ui' / 'src' / 'app.css'

DEFINITION = re.compile(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;')
LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}\b')
STYLE = re.compile(r'<style[^>]*>(.*)</style>', re.DOTALL)


def tokens() -> dict:
    """Every colour app.css names, by the value it holds."""
    found = {}
    for name, value in DEFINITION.findall(TOKENS.read_text()):
        found.setdefault(value.lower(), name)
    return found


def styled() -> list:
    """Every stylesheet the UI has, and the style block of every component.

    A `.svelte` file is cut down to its `<style>` because the faction ramp lives in script, where a
    CSS variable cannot reach and a literal is the only spelling."""
    out = []
    for path in walk(frozenset({'.css', '.svelte'})):
        if 'game-ui' not in path.parts or path == TOKENS:
            continue
        text = path.read_text()
        if path.suffix == '.svelte':
            block = STYLE.search(text)
            if not block:
                continue
            text = block.group(1)
        out.append((path, text))
    return out


def restated() -> list:
    """Places spelling out a value that app.css already has a name for."""
    named, found = tokens(), []
    for path, text in styled():
        for number, line in enumerate(text.splitlines(), 1):
            for hit in LITERAL.findall(line):
                token = named.get(hit.lower())
                if token:
                    found.append(f"{path.relative_to(Path(REPO_ROOT))}: {hit} is {token}")
    return sorted(set(found))


class TestAColourWithAMeaningIsNamed(unittest.TestCase):
    """Fourteen copies of one green is how a colour quietly comes to mean two things."""

    def test_no_style_restates_a_token(self):
        found = restated()

        self.assertFalse(found, "these spell out a colour app.css already names, so retuning the "
                                "token leaves them behind:\n  " + '\n  '.join(found))

    def test_the_tokens_are_readable(self):
        """A guard with nothing to read would pass forever."""
        self.assertIn('#ff4d5e', tokens())