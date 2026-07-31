"""
The director's console: setting games up, watching for a round to become ready, processing it.

Player-facing views live in the game UI (game-ui/, on the JSON API) - this app is only the
half a player never sees. It knows about routing and webpage specifics, and delegates
everything else to an AppFacade.
"""

import logging
import re
from collections import defaultdict
from dataclasses import asdict
from flask import Flask, render_template, request, g, jsonify, send_file, redirect, url_for

from arena.app.players import LOGIN_COOKIE, LOGIN_COOKIE_MAX_AGE
from arena.cfg import WEB_ROOT, GAME_UI_URL
from arena.admin_ui.appfacade import AppFacade, NameValidator

app = Flask('starship-arena', template_folder=f'{WEB_ROOT}/templates', static_folder=f'{WEB_ROOT}/static')
app.logger.setLevel(logging.DEBUG)
# Player-facing pages live in the game UI; the console links out to them.
app.jinja_env.globals['game_ui_url'] = GAME_UI_URL


# ---------------------------------------------------------------------- HELPERS


def facade():
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = AppFacade()
    return _facade


# ---------------------------------------------------------------------- WHO IS ASKING


@app.before_request
def only_the_director():
    """The console runs the game, so only the director gets in.

    A director's link works here as well as on the game UI: both live on one origin, so trading
    it for the cookie at either end signs you in at both."""
    if request.endpoint == 'static':
        return None
    token = request.args.get('login')
    if token:
        player = facade().player_holding(token)
        if player and player.is_director:
            stripped = {k: v for k, v in request.args.items() if k != 'login'}
            answer = redirect(url_for(request.endpoint, **(request.view_args or {}), **stripped))
            answer.set_cookie(LOGIN_COOKIE, player.token, max_age=LOGIN_COOKIE_MAX_AGE,
                              httponly=True, samesite='lax', secure=True)
            return answer
    player = facade().player_holding(request.cookies.get(LOGIN_COOKIE))
    if player and player.is_director:
        return None
    return render_template('no-entry.html', player=player, game_ui_url=GAME_UI_URL), 403


# ---------------------------------------------------------------------- ROUTING


@app.route('/')
def overview():
    """Every game, and whether its round can be processed."""
    return render_template('index.html',
                           games=facade().game_lines(),
                           archived=facade().archived_games())


@app.route('/settings/<game>', methods=['POST'])
def save_settings(game: str):
    facade().save_settings(game,
                           on_all_ready=bool(request.form.get('on_all_ready')),
                           hours=[int(h) for h in request.form.getlist('hour')])
    return redirect(url_for('game_overview', game_name=game))


@app.route('/archive/<game>', methods=['POST'])
def archive(game: str):
    facade().archive_game(game)
    return redirect(url_for('overview'))


@app.route('/unarchive/<game>', methods=['POST'])
def unarchive(game: str):
    facade().unarchive_game(game)
    return redirect(url_for('overview'))


@app.route('/delete_archived/<game>', methods=['POST'])
def delete_archived(game: str):
    facade().delete_archived_game(game)
    return redirect(url_for('overview'))


def submitted_rows(form) -> list[dict]:
    """The ship table as it was submitted, one dict per row, in the order shown."""
    fields = ('name', 'type', 'faction', 'player', 'x', 'y')
    columns = [form.getlist(f'ship_{f}') for f in fields]
    return [dict(zip(fields, values)) for values in zip(*columns)]


def ship_records(rows: list[dict], known_types) -> tuple[list[str], list[dict]]:
    """Turn the submitted rows into ship records. Returns (problems, ships).

    Blank coordinates mean "place it for me", which is a zero. A row with neither a name nor a
    player was added and never used, so it is dropped; those two are the test because a <select>
    always submits a type and Add carries the faction over."""
    problems, ships, seen = [], [], set()
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
        coordinates = {}
        for axis in ('x', 'y'):
            value = row[axis].strip() or '0'
            if not re.match(r'^-?\d+$', value):
                problems.append(f"Ship {i}: {axis} '{value}' is not a whole number.")
            else:
                coordinates[axis] = int(value)
        if len(coordinates) < 2:
            continue
        seen.add(name_v.cleaned)
        ships.append({'name': name_v.cleaned, 'type': row['type'], 'faction': faction.cleaned,
                      'player': player.cleaned, **coordinates})
    if not ships and not problems:
        problems.append("A game needs at least one ship.")
    return problems, ships


@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    messages = list()
    game_name = request.form.get('game_name', '')
    rows = submitted_rows(request.form)
    known_types = facade().all_ship_types | facade().all_starbase_types
    if request.method == 'POST':
        name_v = NameValidator(game_name)
        problems, ships = ship_records(rows, known_types)
        if not name_v.is_valid:
            messages = [f"Game name: {m}" for m in name_v.messages]
        elif name_v.cleaned in facade().all_game_names():
            messages.append("Game name already exists.")
        messages.extend(problems)
        if not messages:
            facade().create_new_game(name_v.cleaned, ships)
            return redirect(url_for('game_overview', game_name=name_v.cleaned))
    return render_template('new-game.html',
                           game_name=game_name,
                           rows=rows,
                           known_players=[p.name for p in facade().active_players()],
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
    ready = {p: facade().is_ready(game.name, p) for p in game.players if p}
    return render_template('game-overview.html',
                           factions=factions,
                           ready=ready,
                           settings=facade().settings(game.name),
                           round_nr=game.current_round_nr,
                           game=game.name,
                           command_file=command_file,
                           ships=len(command_file),
                           orders_in=sum(1 for ok in command_file.values() if ok),
                           all_command_files_ok=game.current_round_ready,
                           dead_ships=game.graveyard.values(),
                           known_players=[p.name for p in facade().active_players()],
                           ship_types=facade().all_ship_types.values(),
                           starbase_types=facade().all_starbase_types.values(),
                           spawn_error=request.args.get('spawn_error')
                           )


@app.route('/spawn/<game>', methods=['POST'])
def spawn(game: str):
    """Schedule a ship for the start of a round. It takes its first orders the round after."""
    form = request.form
    try:
        facade().spawn_ship(game,
                            name=form.get('name', '').strip(),
                            ship_type=form.get('type', ''),
                            player=form.get('player', '').strip(),
                            faction=form.get('faction', '').strip(),
                            x=int(form.get('x') or 0),
                            y=int(form.get('y') or 0),
                            heading=int(form.get('heading') or 0),
                            round_nr=int(form.get('round') or 0))
    except ValueError as refused:
        return redirect(url_for('game_overview', game_name=game, spawn_error=str(refused)))
    return redirect(url_for('game_overview', game_name=game))


@app.route('/game_status/<game>')
def game_status(game: str):
    """What the overview page polls for: who has handed in, and who has said they are ready."""
    return jsonify(asdict(facade().game_pulse(game)))


@app.route('/process_turn/<game>', methods=['POST'])
def process_turn(game: str):
    """POST rather than GET: a browser is free to prefetch a link, and processing a round twice
    is not something to leave to chance."""
    was = facade().game(game).current_round_nr
    facade().process_turn(game)
    now = facade().game(game).current_round_nr
    told = f"Round {was} processed." if now > was else "Nothing processed: orders are still missing."
    return redirect(url_for('game_overview', game_name=game, msg=told))


@app.route('/force_process/<game>', methods=['POST'])
def force_process(game: str):
    """Run the round now, whatever the state of the orders."""
    was = facade().game(game).current_round_nr
    silent = facade().force_process_turn(game)
    told = f"Round {was} processed."
    if silent:
        told += f" No orders from {', '.join(silent)}."
    return redirect(url_for('game_overview', game_name=game, msg=told))


@app.route('/regenerate/<game>', methods=['POST'])
def regenerate(game: str):
    was = facade().game(game).current_round_nr - 1
    now = facade().regenerate_game(game)
    told = f"Replayed to round {now}."
    if now < was:
        told += f" It stopped short of round {was}: orders are missing for a round in between."
    return redirect(url_for('game_overview', game_name=game, msg=told))


@app.route('/players')
def players():
    """Who can log in, and the link each of them holds."""
    return render_template('players.html', logins=facade().logins())


@app.route('/players/issue', methods=['POST'])
def issue_login():
    name_v = NameValidator(request.form.get('name', ''))
    if name_v.is_valid:
        facade().issue_login(name_v.cleaned, director=bool(request.form.get('director')))
    return redirect(url_for('players'))


@app.route('/players/revoke', methods=['POST'])
def revoke_login():
    facade().revoke_login(request.form['name'])
    return redirect(url_for('players'))


@app.route('/players/active', methods=['POST'])
def set_player_active():
    facade().set_player_active(request.form['name'], bool(request.form.get('active')))
    return redirect(url_for('players'))


@app.route('/manual_pdf')
def manual_pdf():
    filename = facade().get_manual_pdf()
    return send_file(filename, mimetype='application/pdf', as_attachment=False)