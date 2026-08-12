import ast
import re
import unittest
from pathlib import Path

from arena.cfg import REPO_ROOT

ENGINE = Path(REPO_ROOT) / 'arena' / 'engine'

# Whose subclasses answer for themselves, so asking what class they are bypasses the vocabulary.
ROOTS = ('Component', 'ObjectInSpace', 'Event')

# A site the record in docs/adr/ already knows about carries its anchor.
ANCHOR = re.compile(r'#.*\b(?:ADR|GDDR)\d{4}-[a-z]\b')


def named_roots(bases: dict) -> set:
    """A root that has been renamed would leave this checking nothing, so it has to be found."""
    missing = [root for root in ROOTS if root not in bases]
    if missing:
        raise LookupError(f"{', '.join(missing)} no longer exists in the engine; rename in ROOTS")
    return set(ROOTS)


def name_of(node):
    """The bare name of a class reference, whether written plain or qualified."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def parse_engine() -> dict:
    return {path: ast.parse(path.read_text()) for path in sorted(ENGINE.rglob('*.py'))}


def bases_by_class(trees: dict) -> dict:
    bases = {}
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases[node.name] = [name_of(b) for b in node.bases]
    return bases


def self_describing(bases: dict) -> set:
    """Every class in the engine that descends from one of the roots."""
    named = named_roots(bases)
    grew = True
    while grew:
        grew = False
        for cls, parents in bases.items():
            if cls not in named and named.intersection(parents):
                named.add(cls)
                grew = True
    return named


def guards(tree) -> set:
    """Calls inside an assert, which are the loud-failure checks the engine asks for."""
    inside = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            inside.update(id(n) for n in ast.walk(node) if isinstance(n, ast.Call))
    return inside


def asked_about(arg) -> list:
    return [name_of(e) for e in arg.elts] if isinstance(arg, ast.Tuple) else [name_of(arg)]


def owning_spans(tree) -> list:
    """The line range of every function, so an anchor anywhere inside one covers what it holds."""
    return [(node.lineno, node.end_lineno) for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def anchored(path: Path, tree, line: int) -> bool:
    """Whether the function holding this line carries an anchor into the record that knows about it."""
    lines = path.read_text().splitlines()
    spans = [(first, last) for first, last in owning_spans(tree) if first <= line <= last]
    if not spans:
        return False
    first, last = max(spans)
    return any(ANCHOR.search(lines[n - 1]) for n in range(first, last + 1))


def inspections() -> list:
    """Every place the engine branches on what class something is, anchored or not."""
    trees = parse_engine()
    named = self_describing(bases_by_class(trees))
    found = []
    for path, tree in trees.items():
        asserted = guards(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or name_of(node.func) != 'isinstance':
                continue
            if id(node) in asserted:
                continue
            asked = [n for n in asked_about(node.args[1]) if n in named]
            if asked:
                found.append((path.relative_to(REPO_ROOT), node.lineno, asked,
                              anchored(path, tree, node.lineno)))
    return sorted(found)


class TestTheEngineAsksRatherThanInspects(unittest.TestCase):
    """A machine asks all its components the same questions, and objects answer for themselves."""

    def test_nothing_branches_on_the_class_of_a_self_describing_object(self):
        found = [row for row in inspections() if not row[3]]

        if found:
            report = '\n'.join(f"  {path}:{line} asks whether something is {' or '.join(asked)}"
                               for path, line, asked, _ in found)
            self.fail(f"the engine inspects a class where it should ask. Fix it, or if it is going "
                      f"on the list in ADR 0019, mark it with that record's anchor:\n{report}")