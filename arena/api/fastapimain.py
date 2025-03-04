from fastapi import FastAPI, Response, status
from pydantic import BaseModel

from arena.web.appfacade import AppFacade

app = FastAPI()

class Commands(BaseModel):
    lines: list[str]


@app.get("/")
async def root():
    return {"message": "Hello World. Bork Bork Bork"}


@app.get("/game_state/{game_name}")
async def read_game_state(game_name: str):
    facade = AppFacade()
    game = facade.game(game_name)
    ois = [obj.simple_snapshot for obj in game.current_round.ois.values()]
    return {
        "name": game.name,
        "current_round": game.current_round_nr,
        "ready": game.command_file_status,
        "ois": ois}

@app.post("/game/{game_name}/ship/{ship_name}/commands")
async def update_commands(game_name: str, ship_name: str, commands: Commands, response: Response):
    facade = AppFacade()
    feedback = facade.check_commands(game_name, ship_name, commands.lines)
    if all(e[0] for e in feedback):
        facade.save_last_commands(game_name, ship_name, commands.lines)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return feedback
