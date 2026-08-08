"""
The director's console: setting games up, watching for a round to become ready, processing it.

Player-facing views live in the game UI (game-ui/, on the JSON API) - this app is only the
half a player never sees. It knows about routing and webpage specifics, and delegates
everything else to an AppFacade.
"""

import logging
import random
import re
from collections import defaultdict
from dataclasses import asdict
from flask import Flask, abort, render_template, request, g, jsonify, send_file, redirect, url_for

from arena.app.players import LOGIN_COOKIE, LOGIN_COOKIE_MAX_AGE
from arena.cfg import WEB_ROOT, GAME_UI_URL, PLAY_URL
from arena.app import scenarios
from arena.app.registrations import Registration
from arena.app.naming import as_stored, for_display
from arena.admin_ui.appfacade import AppFacade, NameValidator

app = Flask('starship-arena', template_folder=f'{WEB_ROOT}/templates', static_folder=f'{WEB_ROOT}/static')
app.logger.setLevel(logging.DEBUG)
# Player-facing pages live in the game UI; the console links out to them. A login link is copied
# out of the console and sent to somebody else, so that one is whole.
app.jinja_env.globals['game_ui_url'] = GAME_UI_URL
app.jinja_env.globals['play_url'] = PLAY_URL

# How much of a game's journal its own page shows, and how much of every game's the Processing
# screen does.
JOURNAL_LINES = 20
COMBINED_JOURNAL_LINES = 60


# ---------------------------------------------------------------------- HELPERS


def facade():
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = AppFacade()
    return _facade


@app.context_processor
def server_clock():
    """Every hour on every screen here is server time, so every screen says what that is."""
    return {'server_time': facade().server_time, 'server_zone': facade().server_zone}


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


@app.route('/processing')
def processing():
    """What every game has actually done, newest first."""
    return render_template('processing.html', journal=facade().all_journals(COMBINED_JOURNAL_LINES))


@app.route('/settings/<game>', methods=['POST'])
def save_settings(game: str):
    facade().save_settings(game,
                           on_all_ready=bool(request.form.get('on_all_ready')),
                           hours=[int(h) for h in request.form.getlist('hour')])
    return redirect(url_for('game_overview', game_name=game, _anchor='processing'))


@app.route('/reopen/<game>', methods=['POST'])
def reopen(game: str):
    try:
        facade().reopen_registrations(game)
    except ValueError as e:
        return redirect(url_for('game_overview', game_name=game, msg=str(e), _anchor='processing'))
    return redirect(url_for('assign', game=game))


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
        name = as_stored(row['name'])
        if name in seen:
            problems.append(f"Ship {i}: '{name}' is named twice.")
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
        seen.add(name)
        ships.append({'name': name, 'type': row['type'],
                      'faction': as_stored(row['faction']), 'player': as_stored(row['player']),
                      **coordinates})
    if not ships and not problems:
        problems.append("A game needs at least one ship.")
    return problems, ships


def roster_page(game_name: str, rows: list[dict], messages: list[str], starting: str = ''):
    """The roster screen. `starting` names the game being brought out of registration.

    The player list is whoever registered for this game, because those are the only names its
    ships can belong to. Without registrations it is everyone who could play."""
    registered = [e.player for e in facade().registrations(starting)] if starting else []
    return render_template('roster.html',
                           game_name=game_name,
                           rows=rows,
                           starting=starting,
                           display=for_display(starting or game_name),
                           settings=facade().settings(starting) if starting else None,
                           known_players=registered or [p.name for p in facade().active_players()],
                           ship_types=facade().all_ship_types.values(),
                           starbase_types=facade().all_starbase_types.values(),
                           messages=messages)


@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    """Pick a scenario and name a game. One that registers goes on to collect them; the generic
    one goes straight to a roster you type yourself."""
    messages = list()
    if request.method == 'POST':
        typed = request.form.get('game_name', '')
        scenario = scenarios.by_key(request.form['scenario'])
        name_v = NameValidator(typed)
        if not name_v.is_valid:
            messages = [f"Game name: {m}" for m in name_v.messages]
        elif as_stored(typed) in facade().game_names_in_use():
            messages.append("Game name already exists.")
        elif not scenario.registers:
            return roster_page(as_stored(typed), [], [])
        else:
            try:
                facade().open_registrations(as_stored(typed), scenario.key)
                return redirect(url_for('assign', game=as_stored(typed)))
            except (ValueError, KeyError) as e:
                messages.append(str(e).strip("'"))
    return render_template('new-game.html', scenarios=scenarios.ALL, messages=messages)


@app.route('/roster', methods=['POST'])
def create_game():
    """The generic path: a typed roster, created straight away."""
    game_name = request.form.get('game_name', '')
    rows = submitted_rows(request.form)
    problems, ships = ship_records(rows, facade().all_ship_types | facade().all_starbase_types)
    if problems:
        return roster_page(game_name, rows, problems)
    facade().create_new_game(as_stored(game_name), ships)
    return redirect(url_for('game_overview', game_name=as_stored(game_name)))


@app.route('/registering')
def registering():
    """Every game collecting registrations, and how much has come in."""
    return render_template('registering.html', forming=facade().forming_games())


@app.route('/registering/<game>', methods=['GET', 'POST'])
def assign(game: str):
    """Drag each registration into a faction. Whoever is left is spread at random.

    Save keeps the assignment and stays; Next deals it and goes on to the roster."""
    try:
        scenario = scenarios.by_key(facade().scenario_of(game))
    except (KeyError, FileNotFoundError):
        abort(404)
    messages = list()
    if request.method == 'POST':
        facade().assign(game, {p: f for p, f in zip(request.form.getlist('player'),
                                                    request.form.getlist('faction')) if f})
        if 'next' in request.form:
            try:
                dealt = scenario.deal(facade().registrations(game), random.Random())
                return roster_page(game, dealt, [], starting=game)
            except ValueError as e:
                messages.append(str(e))
    return render_template('assign.html', game=game, display=for_display(game),
                           scenario=scenario, entries=facade().registrations(game),
                           messages=messages)


@app.route('/start/<game>', methods=['POST'])
def start_game(game: str):
    rows = submitted_rows(request.form)
    problems, ships = ship_records(rows, facade().all_ship_types | facade().all_starbase_types)
    if problems:
        return roster_page(game, rows, problems, starting=game)
    facade().start_game(game, ships,
                        on_all_ready=bool(request.form.get('on_all_ready')),
                        hours=[int(h) for h in request.form.getlist('hour')])
    return redirect(url_for('game_overview', game_name=game))


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
                           display=for_display(game.name),
                           reopenable=facade().is_reopenable(game.name),
                           factions=factions,
                           ready=ready,
                           settings=facade().settings(game.name),
                           round_nr=game.current_round_nr,
                           game=game.name,
                           command_file=command_file,
                           ships=len(command_file),
                           orders_in=sum(1 for ok in command_file.values() if ok),
                           all_command_files_ok=game.current_round_ready,
                           journal=facade().journal(game.name, JOURNAL_LINES),
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
        return redirect(url_for('game_overview', game_name=game, spawn_error=str(refused),
                                _anchor='edit'))
    return redirect(url_for('game_overview', game_name=game, _anchor='edit'))


@app.route('/game_status/<game>')
def game_status(game: str):
    """What the overview page polls for: who has handed in, and who has said they are ready."""
    return jsonify(asdict(facade().game_pulse(game)))


@app.route('/process_turn/<game>', methods=['POST'])
def process_turn(game: str):
    """POST rather than GET: a browser is free to prefetch a link, and processing a round twice
    is not something to leave to chance."""
    was = facade().game(game).current_round_nr
    told = (f"Round {was} processed." if facade().process_turn(game)
            else "Nothing processed: orders are still missing.")
    return redirect(url_for('game_overview', game_name=game, msg=told, _anchor='processing'))


@app.route('/force_process/<game>', methods=['POST'])
def force_process(game: str):
    """Run the round now, whatever the state of the orders."""
    was = facade().game(game).current_round_nr
    silent = facade().force_process_turn(game)
    told = f"Round {was} processed."
    if silent:
        told += f" No orders from {', '.join(silent)}."
    return redirect(url_for('game_overview', game_name=game, msg=told, _anchor='processing'))


@app.route('/regenerate/<game>', methods=['POST'])
def regenerate(game: str):
    was = facade().game(game).current_round_nr - 1
    now = facade().regenerate_game(game)
    told = f"Replayed to round {now}."
    if now < was:
        told += f" It stopped short of round {was}: orders are missing for a round in between."
    return redirect(url_for('game_overview', game_name=game, msg=told, _anchor='processing'))


@app.route('/players')
def players():
    """Who can log in, and the link each of them holds."""
    everyone = facade().logins()
    return render_template('players.html',
                           directors=[p for p in everyone if p.active and p.is_director],
                           logins=[p for p in everyone if p.active and not p.is_director],
                           deactivated=[p for p in everyone if not p.active],
                           show=request.args.get('show'))


@app.route('/players/issue', methods=['POST'])
def issue_login():
    name = request.form.get('name', '')
    if NameValidator(name).is_valid:
        facade().issue_login(as_stored(name), director=bool(request.form.get('director')))
    return redirect(url_for('players'))


PLAYER_ACTIONS = {
    'new_link': lambda f, name: f.reissue_login(name),
    'remove_link': lambda f, name: f.remove_login(name),
    'deactivate': lambda f, name: f.set_player_active(name, False),
    'reactivate': lambda f, name: f.set_player_active(name, True),
    'remove': lambda f, name: f.remove_player(name),
}


@app.route('/players/act', methods=['POST'])
def act_on_players():
    """One button on one row, or one button over the ticked rows.

    Both arrive here because a row's buttons sit inside the form the tickboxes belong to, and
    HTML has no nested forms. A row button carries its player as its own value."""
    for verb, act in PLAYER_ACTIONS.items():
        if verb in request.form:
            act(facade(), request.form[verb])
            return redirect(url_for('players', show=request.form.get('show')))
    act = PLAYER_ACTIONS[request.form['action']]
    for name in request.form.getlist('selected'):
        act(facade(), name)
    return redirect(url_for('players', show=request.form.get('show')))


@app.route('/manual_pdf')
def manual_pdf():
    filename = facade().get_manual_pdf()
    return send_file(filename, mimetype='application/pdf', as_attachment=False)