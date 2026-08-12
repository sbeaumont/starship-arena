"""Every reference the prose makes, classified by how well it survives the code moving."""

import ast
import re
import unittest
from functools import cache
from pathlib import Path

from arena.cfg import REPO_ROOT

ROOT = Path(REPO_ROOT)
SKIP = {'.git', 'node_modules', 'dist', '__pycache__', '.venv', '.idea'}

# A to do list names what does not exist yet, which is what it is for.
UNCHECKED = {'work', 'templates'}

LINK = re.compile(r'\[[^\]]*]\(([^)]+)\)')
CODE_SPAN = re.compile(r'`([^`]+)`')
FILE_LINE = re.compile(r'^([\w./-]+\.\w+):(\d+)(?:-(\d+))?$')
LOOSE_LINE = re.compile(r'^:(\d+)$')
PATH = re.compile(r'^[\w./-]+\.\w+$')
ANCHOR = re.compile(r'^(?:ADR|GDDR)\d{4}-[a-z]$')
SYMBOL = re.compile(r'^([A-Z]\w+)\.(\w+)$')
BY_NUMBER = re.compile(r'\binvariant\s+(\d+)', re.IGNORECASE)

COUNTS = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
          'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
COUNT_WORD = r'\b(?:' + '|'.join(COUNTS) + r')\b'
POINTS_AT_A_LIST = r'\b(?:above|below|following|follow|listed|these|them)\b'
POINTING_AT_A_COUNT = re.compile(f'{COUNT_WORD}[^.]{{0,60}}{POINTS_AT_A_LIST}'
                                 f'|{POINTS_AT_A_LIST}[^.]{{0,60}}{COUNT_WORD}', re.IGNORECASE)


@cache
def walk(suffixes: frozenset = None) -> tuple:
    return tuple(sorted(p for p in ROOT.rglob('*')
                        if p.is_file() and not SKIP.intersection(p.parts)
                        and (suffixes is None or p.suffix in suffixes)))


@cache
def by_name() -> dict:
    index = {}
    for path in walk():
        index.setdefault(path.name, []).append(path)
    return index


@cache
def prose() -> tuple:
    """Every document that describes the code, minus the ones that describe what is not built."""
    missing = [d for d in UNCHECKED if not any(d in p.parts for p in walk())]
    if missing:
        raise LookupError(f"nothing under {', '.join(missing)} any more; UNCHECKED is stale")
    return tuple(p for p in walk(frozenset({'.md'})) if not UNCHECKED.intersection(p.parts))


@cache
def class_graph() -> tuple:
    """What each class defines, and what it inherits from, across the Python in the repo."""
    members, bases = {}, {}
    for path in walk(frozenset({'.py'})):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ClassDef):
                continue
            bases[node.name] = [b.id if isinstance(b, ast.Name) else
                                b.attr if isinstance(b, ast.Attribute) else None
                                for b in node.bases]
            own = members.setdefault(node.name, set())
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    own.add(child.name)
                elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    own.add(child.target.id)
                elif isinstance(child, ast.Assign):
                    own.update(t.id for t in child.targets if isinstance(t, ast.Name))
            own.update(assigned_to_self(node))
    return members, bases


def assigned_to_self(node: ast.ClassDef) -> set:
    """State a class gives itself in its methods answers to a name just as a property does."""
    targets = [t for inner in ast.walk(node) if isinstance(inner, (ast.Assign, ast.AnnAssign))
               for t in (inner.targets if isinstance(inner, ast.Assign) else [inner.target])]
    return {t.attr for t in targets
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == 'self'}


def defines(cls: str, member: str) -> bool:
    """Whether a class answers to a name, through its own body or anything it inherits."""
    members, bases = class_graph()
    seen, todo, complete = set(), [cls], True
    while todo:
        current = todo.pop()
        if current in seen:
            continue
        seen.add(current)
        if member in members.get(current, ()):
            return True
        for base in bases.get(current, []):
            if base in bases:
                todo.append(base)
            else:
                complete = False
    # An unknown base means an incomplete answer, so fall back to the whole repository.
    return not complete and member in set().union(*members.values())


def resolve(doc: Path, text: str) -> list:
    """Where a reference could mean, given a bare name may match several game directories."""
    for candidate in ((doc.parent / text), (ROOT / text)):
        if candidate.exists():
            return [candidate]
    return by_name().get(Path(text).name, [])


def looks_like_a_file(text: str) -> bool:
    """A dotted identifier is not a path, and neither is a number."""
    return '/' in text or Path(text).name in by_name()


def cited(doc: Path) -> list:
    """Every reference in one document, as (line, kind, text)."""
    out = []
    for number, line in enumerate(doc.read_text().splitlines(), 1):
        for target in LINK.findall(line):
            if not target.startswith(('http://', 'https://', '#', 'mailto:')):
                out.append((number, 'link', target.split('#')[0]))
        for span in CODE_SPAN.findall(line):
            if FILE_LINE.match(span) and looks_like_a_file(FILE_LINE.match(span).group(1)):
                out.append((number, 'file_line', span))
            elif LOOSE_LINE.match(span):
                out.append((number, 'loose_line', span))
            elif ANCHOR.match(span):
                out.append((number, 'anchor', span))
            elif PATH.match(span) and looks_like_a_file(span):
                out.append((number, 'path', span))
            elif SYMBOL.match(span):
                out.append((number, 'symbol', span))
    return out


def anchors_in_code() -> dict:
    """Where each anchor comment sits, whatever file it has drifted into."""
    placed = {}
    for path in walk():
        if path.suffix in {'.py', '.js', '.svelte', '.sh', '.html', '.css'}:
            for number, line in enumerate(path.read_text().splitlines(), 1):
                for token in re.findall(r'(?:ADR|GDDR)\d{4}-[a-z]', line):
                    placed.setdefault(token, []).append(f"{path.relative_to(ROOT)}:{number}")
    return placed


def broken() -> list:
    """References that no longer resolve at all."""
    placed, found = anchors_in_code(), []

    def report(doc, number, text, why):
        found.append(f"{doc.relative_to(ROOT)}:{number} `{text}` — {why}")

    for doc in prose():
        for number, line in enumerate(doc.read_text().splitlines(), 1):
            for cite in BY_NUMBER.findall(line):
                report(doc, number, f"invariant {cite}",
                       "an invariant is cited by name, never by number")
        for number, kind, text in cited(doc):
            if kind in ('link', 'path'):
                if not resolve(doc, text):
                    report(doc, number, text, "resolves to nothing")
            elif kind == 'file_line':
                name, first, _ = FILE_LINE.match(text).groups()
                targets = resolve(doc, name)
                if not targets:
                    report(doc, number, text, "resolves to nothing")
                elif all(int(first) > len(t.read_text().splitlines()) for t in targets):
                    report(doc, number, text, "the file has fewer lines than that")
            elif kind == 'symbol':
                cls, member = SYMBOL.match(text).groups()
                if cls in class_graph()[0] and not defines(cls, member):
                    report(doc, number, text, f"{cls} answers to no {member}")
            elif kind == 'anchor':
                where = placed.get(text, [])
                if len(where) != 1:
                    report(doc, number, text, f"marks {len(where)} places in the code")
    return found


def drifting() -> list:
    """References that resolve today and rot on the next edit above them."""
    return [f"{doc.relative_to(ROOT)}:{number} `{text}`"
            for doc in prose() for number, kind, text in cited(doc)
            if kind in ('file_line', 'loose_line')]


def brittle() -> list:
    """Prose that commits to a count of something it also lists, which the next edit falsifies."""
    return [f"{doc.relative_to(ROOT)}:{number} {line.strip()[:78]}"
            for doc in prose()
            for number, line in enumerate(doc.read_text().splitlines(), 1)
            if POINTING_AT_A_COUNT.search(line)]


class TestTheProseStillPointsAtSomething(unittest.TestCase):
    """A doc that cites the code is only worth reading while the citation resolves."""

    def test_every_reference_resolves(self):
        found = broken()

        if found:
            self.fail("the prose points at things that are not there:\n  " + '\n  '.join(found))


if __name__ == '__main__':
    for title, rows in (("BROKEN", broken()),
                        ("DRIFTING", drifting()),
                        ("BRITTLE", brittle())):
        print(f"\n=== {title} ({len(rows)}) ===")
        for row in rows:
            print(f"  {row}")