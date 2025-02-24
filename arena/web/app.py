"""
Main entry point for the web interface.

Knows about routing and webpage specifics.

Does not know anything about databases and model objects.
Delegates the specifics to an AppFacade.
"""

import logging
from collections import defaultdict
from flask import Flask, render_template, request, g, send_file, redirect, url_for

from arena.engine.history import Tick
from arena.web.appfacade import AppFacade, NameValidator

app = Flask('starship-arena', template_folder='./arena_web/templates', static_folder='./arena_web/static')
app.logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------- HELPERS


def facade():
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = AppFacade()
    return _facade


def cleanup_command_form(contents):
    return [line.strip() for line in contents.splitlines() if line != '']


# ---------------------------------------------------------------------- ROUTING


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    messages = list()
    if request.method == 'POST':
        if ('action' in request.form) and (request.form['action'] == 'New game'):
            name_v = NameValidator(request.form['game_name'])
            if name_v.is_valid:
                if name_v.cleaned not in facade().all_games():
                    facade().create_new_game(name_v.cleaned)
                else:
                    messages.append("Game name already exists.")
            else:
                messages = name_v.messages
    return render_template('./templates/admin.html',
                           games=facade().all_games(),
                           messages=messages)


@app.route('/')
def overview():
    """Home page."""
    return render_template('./templates/index.html',
                           games=facade().all_games())


@app.route('/game_overview/<game>')
def game_overview(game: str):
    """Overview of all known games."""
    factions = defaultdict(list)
    for s in facade().ships_for_game(game):
        factions[s.faction].append(s)
    return render_template('./templates/game-overview.html',
                           factions=factions,
                           round_nr=facade().current_round_of_game(game),
                           game=game,
                           command_file=facade().command_file_status_of_game(game),
                           all_command_files_ok=facade().all_command_files_ok(game),
                           dead_ships=facade().dead_ships_for_game(game).values()
                           )


@app.route('/process_turn/<game>')
def process_turn(game: str):
    facade().process_turn(game)
    return redirect(url_for('game_overview', game=game))


@app.route('/ship_overview')
def ship_overview():
    return render_template('./templates/ship-overview.html',
                           ship_types=facade().all_ship_types.values(),
                           starbase_types=facade().all_starbase_types.values()
                           )


@app.route('/past_round/<game>/<ship_name>/<round>', methods=['GET', 'POST'])
def past_round(game: str, ship_name: str, round: int):
    round = int(round)
    ship = facade().get_ship(game, ship_name, round)
    return render_template('./templates/past-round.html',
                           ship=ship,
                           game=game,
                           round=round,
                           total_rounds=facade().current_round_of_game(game),
                           start_tick=Tick.for_start_of_round(round),
                           commands=facade().commands_of_round(game, ship_name, round)
                           )


@app.route('/turn_picture/<game>/<ship_name>/<round>')
def turn_picture(game: str, ship_name:str, round: int):
    filename = facade().get_turn_picture_name(game, ship_name, round)
    return send_file(filename, mimetype='image/png')


@app.route('/turn_pdf/<game>/<ship_name>/<round>')
def turn_pdf(game: str, ship_name:str, round: int):
    filename = facade().get_turn_pdf_name(game, ship_name, round)
    return send_file(filename, mimetype='application/pdf', as_attachment=False)


@app.route('/manual_pdf')
def manual_pdf():
    filename = facade().get_manual_pdf()
    return send_file(filename, mimetype='application/pdf', as_attachment=False)


@app.route('/lore')
def lore():
    return render_template('./templates/lore.html')


@app.route('/plan_round/<game>/<ship_name>', methods=['GET', 'POST'])
def plan_round(game: str, ship_name: str):
    message = ''
    if request.method == 'POST':
        if request.form['action'] == 'Check':
            commands = facade().check_commands(cleanup_command_form(request.form['commands']), game, ship_name)
        elif request.form['action'] == 'Save':
            commands = facade().check_commands(cleanup_command_form(request.form['commands']), game, ship_name)
            if all([e[0] for e in commands]):
                facade().save_last_commands(game, ship_name, cleanup_command_form(request.form['commands']))
                message = 'Saved.'
            else:
                message = 'Still errors in file.'
        else:
            commands = [False, 'Wrong action']
            message = 'Wrong Action!'
    else:
        commands = facade().check_commands(facade().get_last_commands(game, ship_name), game, ship_name)
    return render_template('./templates/plan-round.html',
                           game=game,
                           ship=facade().get_ship(game, ship_name),
                           commands=commands,
                           message=message,
                           total_rounds=facade().current_round_of_game(game)
                           )

