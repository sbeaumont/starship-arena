import logging
from flask import Flask, render_template, request, g, send_file, redirect, url_for

from webapp.appfacade import AppFacade

app = Flask('starship-arena', template_folder='.')
app.logger.setLevel(logging.DEBUG)


def facade():
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = AppFacade()
    return _facade


def cleanup_command_form(contents):
    return [line.strip() for line in contents.splitlines() if line != '']


@app.route('/')
def overview():
    return render_template('./templates/index.html',
                               games=facade().all_games())


@app.route('/game_overview/<game>')
def game_overview(game: str):
    return render_template('./templates/game-overview.html',
                           ships=facade().ships_for_game(game),
                           round_nr=facade().current_round_of_game(game),
                           game=game,
                           command_file=facade().command_file_status_of_game(game),
                           all_command_files_ok=facade().all_command_files_ok(game)
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
    ship = facade().get_ship(game, ship_name, round)
    return render_template('./templates/past-round.html',
                           ship=ship,
                           game=game,
                           round=round,
                           total_rounds=facade().current_round_of_game(game)
                           )


@app.route('/turn_picture/<game>/<ship_name>/<round>')
def turn_picture(game: str, ship_name:str, round: int):
    filename = facade().get_turn_picture_name(game, ship_name, round)
    return send_file(filename, mimetype='image/png')


@app.route('/turn_pdf/<game>/<ship_name>/<round>')
def turn_pdf(game: str, ship_name:str, round: int):
    filename = facade().get_turn_pdf_name(game, ship_name, round)
    return send_file(filename, mimetype='application/pdf', as_attachment=False)


@app.route('/plan_round/<game>/<ship_name>', methods=['GET', 'POST'])
def plan_round(game: str, ship_name: str):
    ship = facade().get_ship(game, ship_name)
    message = ''
    if request.method == 'POST':
        if request.form['action'] == 'Check':
            commands = facade().check_commands(cleanup_command_form(request.form['commands']), ship)
        elif request.form['action'] == 'Save':
            commands = facade().check_commands(cleanup_command_form(request.form['commands']), ship)
            if all([e[0] for e in commands]):
                facade().save_last_commands(game, ship_name, cleanup_command_form(request.form['commands']))
                message = 'Saved.'
            else:
                message = 'Still errors in file.'
        else:
            commands = [False, 'Wrong action']
            message = 'Wrong Action!'
    else:
        commands = facade().check_commands(facade().get_last_commands(game, ship_name), ship)

    return render_template('./templates/plan-round.html',
                           game=game,
                           ship=ship,
                           commands=commands,
                           message=message,
                           total_rounds=facade().current_round_of_game(game)
                           )
