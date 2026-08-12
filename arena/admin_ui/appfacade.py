"""
Facade that keeps the director's console from knowing too much about the internals.

It is the semantic layer for this one UI: everything the console asks about a game, in the
console's own terms. Player-facing operations live in the application-services layer instead.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime

from arena.app.clock import server_now, zone_name
from arena.app.dto import By, GameSettings, GameStanding, ProcessingTrigger
from arena.app.naming import for_display
from arena.app.services import AdminService
from arena.cfg import GAME_DATA_DIR, MANUAL_FILENAME

logger = logging.getLogger('starship-arena.facade')


class NameValidator(object):
    """Validation of ship names."""

    def __init__(self, name):
        self.name = name
        self.messages = list()

        self._check_not_empty()
        # The other two have nothing to say about a name that isn't there, and saying it anyway
        # buries the one message that matters under two that don't.
        if self.name and self.name.strip():
            self._check_correct_characters()
            self._check_first_character_is_letter()

    @property
    def is_valid(self):
        return len(self.messages) == 0

    def _check_correct_characters(self):
        if not re.match(r'^[A-Za-z0-9\- ]+$', self.name):
            self.messages.append('Only letters, numbers, dashes and spaces in name.')

    def _check_first_character_is_letter(self):
        if not re.match(r'^[A-Za-z]', self.name):
            self.messages.append('First character must be a letter.')

    def _check_not_empty(self):
        if not self.name or len(self.name.strip()) == 0:
            self.messages.append('Name can not be empty.')


@dataclass
class JournalLine:
    """One journal entry as the console prints it: a time to read, and pairs to show."""
    game: str
    when: str
    event: str
    detail: dict[str, str]

    @property
    def display(self) -> str:
        return for_display(self.game)


@dataclass
class Journal:
    """Journal entries as a table: the detail columns they use between them, and the rows.

    The columns come from the entries rather than from a list held here, so a new detail on an
    entry gets a column of its own and nothing needs editing."""
    columns: list[str]
    lines: list[JournalLine]


@dataclass
class GameDetail:
    """One game as the console's own page shows it: the living ships by faction, the dead, and
    what the round is waiting for."""
    name: str
    standing: GameStanding
    factions: dict[str, list]   # faction -> its living ships, best faction first
    dead: list                  # what is in the graveyard, whatever faction it flew for

    @property
    def display(self) -> str:
        return for_display(self.name)


class AppFacade(object):
    """Object that hides specifics from the web interface."""

    def __init__(self):
        self.admin = AdminService(GAME_DATA_DIR)

    # ---------------------------------------------------------------------- QUERIES - Reference

    def get_manual_pdf(self) -> str:
        return MANUAL_FILENAME

    def types_by_category(self) -> dict[str, list]:
        """Every model that can be fielded, grouped as the forms offer them. The categories are
        the types' own, so a new kind of machine needs nothing here."""
        grouped = {}
        for t in self.admin.list_ship_types():
            grouped.setdefault(t.category, []).append(t)
        return grouped

    def known_type_names(self) -> set:
        return {t.type_name for t in self.admin.list_ship_types()}

    # ---------------------------------------------------------------------- QUERIES - Game

    def game_names_in_use(self) -> set:
        return self.admin.game_names_in_use()

    def game_lines(self) -> list:
        """Every game being played, each with what its round is waiting for."""
        return self.admin.list_games()

    def rounds_played(self, game: str) -> int:
        """Read off the file names, so it answers for a game whose rounds cannot be loaded."""
        return self.admin.playable_games_on_disk()[game]

    def game_detail(self, game: str) -> GameDetail:
        overview = self.admin.game_overview(game)
        return GameDetail(name=game,
                          standing=self.admin.standing(game),
                          factions={f.name: [s for s in f.ships if s.alive]
                                    for f in overview.factions},
                          dead=[s for f in overview.factions for s in f.ships if not s.alive])

    # ---------------------------------------------------------------------- COMMANDS

    def process_turn(self, game_name: str) -> bool:
        return self.admin.process_turn(game_name)

    def regenerate_game(self, game_name: str) -> int:
        return self.admin.regenerate_game(game_name)

    def force_process_turn(self, game_name: str) -> list[str]:
        return self.admin.force_process_turn(game_name, By.DIRECTOR,
                                             ProcessingTrigger.MANUAL_FORCED)

    @staticmethod
    def _journal_line(game: str, entry) -> JournalLine:
        return JournalLine(game=game,
                           when=f"{datetime.fromisoformat(entry.at):%d %b %H:%M}",
                           event=entry.event,
                           detail={k.replace('_', ' '): v for k, v in entry.detail.items()})

    @staticmethod
    def _as_table(lines: list[JournalLine]) -> Journal:
        return Journal(columns=list(dict.fromkeys(k for line in lines for k in line.detail)),
                       lines=lines)

    def journal(self, game: str, limit: int = 0) -> Journal:
        return self._as_table([self._journal_line(game, e)
                               for e in self.admin.journal(game, limit)])

    def all_journals(self, limit: int = 0) -> Journal:
        """Every game's journal in one run, newest first."""
        found = [(g.name, e) for g in self.admin.list_games() for e in self.admin.journal(g.name)]
        found.sort(key=lambda pair: datetime.fromisoformat(pair[1].at), reverse=True)
        return self._as_table([self._journal_line(name, e) for name, e in found[:limit or None]])

    @property
    def server_zone(self) -> str:
        return zone_name()

    @property
    def server_time(self) -> str:
        return f"{server_now():%H:%M}"

    def standing(self, game: str):
        return self.admin.standing(game)

    def game_pulse(self, game: str):
        return self.admin.game_pulse(game)

    def settings(self, game: str):
        return self.admin.settings(game)

    def save_settings(self, game: str, on_all_ready: bool, hours: list[int],
                      announce: bool) -> None:
        self.admin.save_settings(game, GameSettings(on_all_ready=on_all_ready,
                                                    process_hours=hours, announce=announce))

    def archived_games(self) -> list:
        return self.admin.list_archived_games()

    def registering_games(self) -> list:
        return self.admin.list_registering_games()

    def open_registrations(self, name: str, scenario: str) -> None:
        self.admin.open_registrations(name, scenario)

    def scenario_of(self, game: str) -> str:
        return self.admin.scenario_of(game)

    def registrations(self, game: str) -> list:
        return self.admin.registrations(game)

    def assign(self, game: str, factions: dict) -> None:
        self.admin.assign(game, factions)

    def forming_games(self) -> list:
        return self.admin.forming_games()

    def start_game(self, game: str, ships: list[dict], on_all_ready: bool, hours: list[int],
                   announce: bool):
        self.admin.start_game(game, ships, GameSettings(on_all_ready=on_all_ready,
                                                        process_hours=hours, announce=announce))

    def reopen_registrations(self, game: str) -> None:
        self.admin.reopen_registrations(game)

    def is_reopenable(self, game: str) -> bool:
        return self.admin.is_reopenable(game)

    def archive_game(self, name: str) -> None:
        self.admin.archive_game(name)

    def unarchive_game(self, name: str) -> None:
        self.admin.unarchive_game(name)

    def delete_archived_game(self, name: str) -> None:
        self.admin.delete_archived_game(name)

    # ---------------------------------------------------------------------- LOGINS

    def player_holding(self, token: str):
        """Who this token belongs to, or None. The console is the director's, so callers check
        `is_director` rather than merely that somebody answered."""
        return self.admin.players.by_token(token)

    def logins(self) -> list:
        return self.admin.logins()

    def issue_login(self, name: str, director: bool = False):
        return self.admin.issue_login(name, director)

    def reissue_login(self, name: str):
        return self.admin.reissue_login(name)

    def remove_login(self, name: str) -> None:
        self.admin.remove_login(name)

    def remove_player(self, name: str) -> None:
        self.admin.remove_player(name)

    def set_player_active(self, name: str, active: bool) -> None:
        self.admin.set_player_active(name, active)

    def spawn_ship(self, game: str, name: str, ship_type: str, player: str, faction: str,
                   x: int, y: int, heading: int, round_nr: int) -> None:
        self.admin.spawn_ship(game, name, ship_type, player=player, faction=faction,
                              x=x, y=y, heading=heading, round_nr=round_nr)

    def active_players(self) -> list:
        return [p for p in self.logins() if p.active]

    def create_new_game(self, name: str, ships: list[dict], scenario: str):
        logger.info(f"Creating new game: {name}")
        self.admin.create_game(name, ships, scenario)
