"""
The director's console: setting games up, watching for a round to become ready, processing it.

Player-facing views live in the game UI (game-ui/, on the JSON API) - this app is only the
half a player never sees. It knows about routing and webpage specifics, and delegates
everything else to an AppFacade.
"""

import logging
from collections import defaultdict
from flask import Flask, render_template, request, g, send_file, redirect, url_for

from arena.cfg import WEB_ROOT, GAME_UI_URL
from arena.admin_ui.appfacade import AppFacade, NameValidator

app = Flask('starship-arena', template_folder=f'{WEB_ROOT}/templates', static_folder=f'{WEB_ROOT}/static')
app.logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------- HELPERS


def facade():
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = AppFacade()
    return _facade


# ---------------------------------------------------------------------- ROUTING


@app.route('/')
def overview():
    """Every game, and whether its round can be processed."""
    return render_template('index.html', games=facade().game_lines())


SHIP_FILE_HEADER = 'Name Type Faction Player X Y'


def submitted_rows(form) -> list[dict]:
    """The ship table as it was submitted, one dict per row, in the order shown."""
    fields = ('name', 'type', 'faction', 'player', 'x', 'y')
    columns = [form.getlist(f'ship_{f}') for f in fields]
    return [dict(zip(fields, values)) for values in zip(*columns)]


def ship_file_lines(rows: list[dict], known_types) -> tuple[list[str], list[str]]:
    """Turn the submitted rows into ships.txt lines. Returns (problems, lines).

    The file is whitespace separated, so a name with a space in it would silently become two
    columns and shift everything after it. NameValidator's cleaning - spaces become underscores -
    is what keeps that from happening quietly.

    A row with neither a name nor a player is one the director added and did not use, so it is
    dropped rather than complained about. Those two fields are the test because the others are
    never empty by the time they arrive: a <select> always submits a type, and the Add button
    carries the previous row's faction over. Half-filled rows still get their error.

    Blank coordinates mean (0, 0), which is the engine's signal to place the ship itself:
    distribute_factions only moves ships still sitting on the origin."""
    problems, lines, seen = [], [], set()
    for i, row in enumerate(rows, start=1):
        if not (row['name'].strip() or row['player'].strip()):
            continue
        name_v = NameValidator(row['name'])
        if not name_v.is_valid:
            problems.extend(f"Ship {i}: {m}" for m in name_v.messages)
            continue
        if name_v.cleaned in seen:
            problems.append(f"Ship {i}: '{name_v.cleaned}' is named twice.")
            continue
        if row['type'] not in known_types:
            problems.append(f"Ship {i}: '{row['type']}' is not a known ship type.")
            continue
        faction = NameValidator(row['faction'])
        player = NameValidator(row['player'])
        if not faction.is_valid:
            problems.append(f"Ship {i}: faction - {' '.join(faction.messages)}")
            continue
        if not player.is_valid:
            problems.append(f"Ship {i}: player - {' '.join(player.messages)}")
            continue
        seen.add(name_v.cleaned)
        x = row['x'].strip() or '0'
        y = row['y'].strip() or '0'
        lines.append(f"{name_v.cleaned} {row['type']} {faction.cleaned} {player.cleaned} {x} {y}")
    if not lines and not problems:
        problems.append("A game needs at least one ship.")
    return problems, lines


@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    messages = list()
    game_name = request.form.get('game_name', '')
    rows = submitted_rows(request.form)
    known_types = facade().all_ship_types | facade().all_starbase_types
    if request.method == 'POST':
        name_v = NameValidator(game_name)
        problems, lines = ship_file_lines(rows, known_types)
        if not name_v.is_valid:
            messages = [f"Game name: {m}" for m in name_v.messages]
        elif name_v.cleaned in facade().all_game_names():
            messages.append("Game name already exists.")
        messages.extend(problems)
        if not messages:
            facade().create_new_game(name_v.cleaned, '\n'.join([SHIP_FILE_HEADER] + lines))
            return redirect(url_for('game_overview', game_name=name_v.cleaned))
    return render_template('new-game.html',
                           game_name=game_name,
                           rows=rows,
                           ship_types=facade().all_ship_types.values(),
                           starbase_types=facade().all_starbase_types.values(),
                           messages=messages)


@app.route('/game_overview/<game_name>')
def game_overview(game_name: str):
    """One game: who commands what, and who still owes orders."""
    factions = defaultdict(list)
    game = facade().game(game_name)
    for s in game.player_ships:
        factions[s.faction].append(s)
    command_file = game.command_file_status
    return render_template('game-overview.html',
                           factions=factions,
                           round_nr=game.current_round_nr,
                           game=game.name,
                           command_file=command_file,
                           ships=len(command_file),
                           orders_in=sum(1 for ok in command_file.values() if ok),
                           all_command_files_ok=game.current_round_ready,
                           dead_ships=game.graveyard.values(),
                           game_ui_url=GAME_UI_URL
                           )


@app.route('/process_turn/<game>', methods=['POST'])
def process_turn(game: str):
    """POST rather than GET: a browser is free to prefetch a link, and processing a round twice
    is not something to leave to chance."""
    facade().process_turn(game)
    return redirect(url_for('game_overview', game_name=game))


@app.route('/ship_overview')
def ship_overview():
    return render_template('ship-overview.html',
                           ship_types=facade().all_ship_types.values(),
                           starbase_types=facade().all_starbase_types.values()
                           )


@app.route('/manual_pdf')
def manual_pdf():
    filename = facade().get_manual_pdf()
    return send_file(filename, mimetype='application/pdf', as_attachment=False)


@app.route('/lore')
def lore():
    return render_template('lore.html')