"""
Data Transfer Objects for the application-services layer (arena/app).

Plain dataclasses, deliberately free of any UI/framework dependency (no FastAPI,
no pydantic) so this layer stays UI-agnostic. They carry domain data only and never
storage details such as GameDirectory or file paths.
"""

from dataclasses import dataclass, field
from enum import Enum

from arena.app.naming import for_display


@dataclass
class Named:
    """Anything a person reads the name of. `display` is `name` with its underscores back."""
    name: str
    display: str = field(init=False, default='')

    def __post_init__(self):
        self.display = for_display(self.name)


@dataclass
class GameStanding:
    """What the round being planned is still waiting for.

    Orders are counted per ship, because that is what gates processing. Saved and ready are
    counted per commander, because a player says they are ready once and saves their whole
    fleet in one go."""
    round_nr: int
    all_in: bool           # every ship has orders: the round can be processed
    ships: int
    orders_in: int
    missing: list[str]     # ships still owing orders
    players: int
    players_saved: int     # commanders whose ships all have orders in
    players_ready: int

    @property
    def percent_in(self) -> int:
        return round(100 * self.orders_in / self.ships) if self.ships else 0

    @property
    def percent_ready(self) -> int:
        return round(100 * self.players_ready / self.players) if self.players else 0

    @property
    def all_ready(self) -> bool:
        return bool(self.players) and self.players_ready == self.players


@dataclass
class GameSummary(Named):
    current_round: int = 0
    process_hours: list[int] = field(default_factory=list)  # hours of server time it runs on
    # When it next will, ISO 8601 with the offset. None when the director processes it by hand.
    # A moment rather than a schedule, so a reader's browser can put it in their own clock.
    next_processing: str | None = None
    # None while a game is still collecting registrations: nothing is being planned yet.
    standing: GameStanding | None = None


@dataclass
class FormingGame(Named):
    """A game collecting registrations, as the director's list shows it."""
    scenario: str = ''
    players: int = 0
    ships: int = 0
    assigned: int = 0   # how many of those players the director has put in a faction


@dataclass
class OpenGame(Named):
    """A game collecting registrations, and what the player asking put down for it."""
    scenario: str = ''
    blurb: str = ''
    max_ships: int = 0
    players: int = 0       # how many have registered so far
    my_ships: list[str] = field(default_factory=list)


@dataclass
class SoloGame:
    """The one game a player may start on their own, and what starting a new one allows.

    `game` is None until they have. Starting another throws the one they had away, so this is
    both the offer and the state of it."""
    scenario: str
    blurb: str
    max_ships: int
    game: GameSummary | None = None


@dataclass
class ShipSummary:
    name: str
    ship_type: str
    player: str | None   # None for a ship no one commands
    score: int
    alive: bool
    orders_in: bool      # whether orders for the current round have been handed in
    player_ready: bool   # whether their player has said they are done with the round


@dataclass
class FactionSummary:
    name: str
    score: int           # what its ships have scored between them
    ships: list[ShipSummary]


@dataclass
class GameOverview(Named):
    """Who is playing a game and how they are doing, enough to pick whose view to open."""
    last_round: int = 0
    factions: list[FactionSummary] = field(default_factory=list)


@dataclass
class ServerTime:
    """The clock a game's hours are in, so an interface can put a reader's own beside it."""
    now: str    # ISO 8601 with the offset
    zone: str   # what the server calls it: 'CEST', 'UTC'


@dataclass
class ShipLimits:
    """Per-tick movement limits from the ship's type -- what a planner may not exceed."""
    max_turn: float
    max_delta_v: float
    max_speed: float


@dataclass
class ScanInfo:
    name: str
    x: float
    y: float
    distance: float
    direction: float  # relative bearing from the scanning ship
    heading: float    # absolute heading to the scanned object
    friendly: bool


@dataclass
class TickState:
    """The scanning ship's own state at the end of one tick, plus what it saw."""
    tick: int
    x: float
    y: float
    heading: float
    speed: float
    events: list[str] = field(default_factory=list)
    scans: list[ScanInfo] = field(default_factory=list)


@dataclass
class ShipRound:
    game: str
    ship: str
    ship_type: str
    round: int
    start: TickState | None  # state at the end of the previous round (the path's origin)
    ticks: list[TickState]
    limits: ShipLimits


@dataclass
class CommandCheck:
    line: str
    ok: bool
    feedback: list[str]


@dataclass
class TrackPoint:
    tick: int
    x: float
    y: float


@dataclass
class Pulse:
    """What a waiting player wants to know, cheap enough to ask for repeatedly."""
    last_round: int
    ready: dict[str, bool]   # per player in the asker's factions


@dataclass
class GamePulse:
    """The same question for a whole game, which is what the console watches."""
    round_nr: int            # the round being planned
    orders: dict[str, bool]  # per ship
    ready: dict[str, bool]   # per player


@dataclass
class GameSettings:
    """How a game decides to process a round by itself. Both off means the director does it."""
    on_all_ready: bool
    process_hours: list[int]   # hours of the day it runs on. Empty means never
    announce: bool = True      # tell the players a round has been processed


class By(str, Enum):
    """Who did something. Spelled the 3.10-compatible way; the host has no StrEnum."""
    DIRECTOR = 'director'
    CRON = 'cron'
    PLAYER = 'player'

    def __str__(self):
        return self.value


class ProcessingTrigger(str, Enum):
    """What set a round going."""
    MANUAL = 'manual'
    MANUAL_FORCED = 'manual forced'
    DEADLINE = 'deadline'
    ALL_READY = 'all players ready'

    def __str__(self):
        return self.value


@dataclass
class StaleRound:
    """One saved round, read against the code as it is now.

    `missing` is what the round names that has since gone, against how many times it appears.
    `error` is filled when not even a stand-in got it open, and then nothing else is known."""
    round_nr: int
    missing: dict[str, int]
    error: str = ''

    @property
    def reads(self) -> bool:
        return not (self.missing or self.error)


@dataclass
class JournalEntry:
    """One thing that happened to a game, and when.

    `detail` is the entry's own reported dict, so a screen prints its pairs without knowing their
    names and a new kind of entry needs no template edit."""
    at: str      # ISO 8601 with the offset, in server time
    event: str   # 'processed', 'failed', 'regenerated'
    detail: dict[str, str]


@dataclass
class LoginInfo:
    """A person the director can hand a link to. `token` is empty when they have none yet."""
    name: str
    is_director: bool
    token: str
    games: list[str]
    active: bool   # a deactivated player keeps their name and their games, but cannot log in


@dataclass
class Me:
    """Who the caller is. `games` are the games they have ships in, theirs to plan.

    `admin_url` is where the console is, and empty for anyone who may not use it - so an
    interface offers the way through by having been told, not by knowing the rule."""
    name: str
    is_director: bool
    games: list[str]
    admin_url: str


@dataclass
class ShipTypeInfo:
    """A model as the registry defines it, for a reference page."""
    type_name: str
    name: str
    category: str          # 'Ship' | 'Starbase'
    specs: dict[str, str]


@dataclass
class ComponentInput:
    """One input a component needs before it can be given an order. `kind` tells an interface
    which control to offer; min/max are filled in when the input is a bounded number."""
    name: str
    kind: str
    min: float | None = None
    max: float | None = None
    # The names this input may take, when it is a short list rather than anything on the map.
    choices: list[str] | None = None


@dataclass
class ComponentStatus:
    """What a component reports, next to what the type object reports for a pristine one.

    The pairs are the component's own, so a reader renders what it is handed. Ordered as the
    machine carries them: defense, weapons, ECM. `name` is the selector an order addresses it
    by, and `group` is the machine's own collection, which is what tells an interface which
    order the component takes."""
    name: str
    group: str   # 'defense' | 'weapons' | 'ecm' | 'control'
    status: dict[str, str]
    full: dict[str, str]
    inputs: list[ComponentInput]   # empty for a component that takes no orders


@dataclass
class TickCondition:
    """What a ship was down to at the end of a tick. The map already shows where it was.

    Hull and battery are fractional because an impact is: the damage is a mass times the speed
    it arrived at, and movement costs a tenth of a speed a collision left fractional."""
    tick: int
    hull: float
    battery: float
    shields: dict[str, str]


@dataclass
class TickEvent:
    """Something that happened to a ship on a tick. Scans are left out; the map draws those.

    Both numbers for the one moment, as `Tick` itself holds them: `tick` reads as the round shows
    it, `abs_tick` orders across rounds, which is what a playhead scrubs on."""
    tick: int
    abs_tick: int
    text: str
    kind: str   # 'internal' | 'hit' | 'explosion' | 'replenish'


@dataclass
class Contact:
    """A detected object as a chronological track of sightings (fog of war).

    One point = a single blip; the last element is the most recent known position.
    Scans record where a contact was, not its own heading, so movement is read from
    the track itself and there is no projection.
    """
    name: str
    type_name: str      # the object's model: 'H2545', 'Rocket', 'SplinterMine', ...
    category_name: str  # the family it belongs to: 'Ship', 'Starbase', 'Missile', 'Mine'
    stance: str         # 'Friend', 'Foe' or 'Neutral' towards the faction being planned for
    track: list[TrackPoint]
    radius: float = 0   # above 0 is something solid, and drawn at its true size


@dataclass
class WeaponInfo:
    """What the map needs to draw a weapon's shot, on top of what every component reports."""
    name: str
    description: str
    firing_arc: tuple[float, float] | None   # relative to the ship's heading; None = all round
    ammo: int | None                         # live count; None = does not use ammunition
    max_ammo: int | None                     # the full load, from the type object
    payload: str | None                      # what it launches, e.g. 'Rocket'; None if nothing
    # The speed the payload carries of its own, so a shot can be drawn the distance it really
    # covers in a tick. None when the payload has no speed of its own: a mine leaves at the
    # ship's speed and slows to a stop, which is not a single figure worth drawing to scale.
    payload_speed: float | None
    inputs: list[ComponentInput]


@dataclass
class ShipPlan:
    name: str
    ship_type: str
    category_name: str   # 'Ship' or 'Starbase'; a starbase is drawn, and flies, differently
    x: float
    y: float
    heading: float
    speed: float
    hull: float          # fractional after an impact; see TickCondition
    max_hull: int
    battery: float
    max_battery: int
    player: str | None   # who commands it
    player_ready: bool   # whether they have said they are done with the round being planned
    owned: bool          # True = this player's ship (editable); False = faction ally (context)
    limits: ShipLimits
    # How far this notices a standard object without pinging for it. What a scanner actually
    # reaches depends on how visible the thing is, so this is the neutral case.
    scan_range: float
    components: list[ComponentStatus]   # shields, weapons and ECM as they stand
    specs: dict[str, str]               # what the type object says this model can do
    weapons: list[WeaponInfo]
    track: list[TrackPoint]   # where it actually went during the round: your own ships are
                              # ground truth, not fog of war
    events: list[TickEvent]   # what happened to it during the round, tick by tick
    conditions: list[TickCondition]   # what it was down to, tick by tick
    alive: bool               # False for a ship destroyed in this round, kept so its player
                              # can read what happened to it
    commands: list[str]  # any plan already saved for the upcoming round


@dataclass
class Explosion:
    """An explosion one of the faction's ships witnessed. The radius is a real world
    distance, set by the warhead of the ordnance that went off."""
    tick: int
    x: float
    y: float
    radius: float
    damage_type: str   # 'Explosion', 'Nanocyte' or 'EMP'


@dataclass
class Effect:
    """What one layer of a target did with a blow the faction landed, and where it happened.

    The engine's word, kept: `part` is the layer as it names itself, a component or `hull` /
    `battery` for the machine, and `outcome` is `Unaffected`, `Damaged` or `Breached`, where
    Breached on the hull is a kill. What each of those is worth drawing is the interface's call.

    `bearing` is the direction the target was struck from, which is the face that took it, because
    the layer that answers is always the one pointing at whoever hit it."""
    tick: int
    x: float             # where the target was when it took this
    y: float
    bearing: float
    target: str
    part: str
    outcome: str
    amount: int
    points: int


@dataclass
class Beam:
    """A hit that arrived along a line, as the line. What a blast is as a circle.

    Both numbers for the one moment, as `TickEvent` carries them. Placed from where each end was
    on that tick, so it is drawn between two ships rather than at whatever they are doing now.

    Nameless, like a blast and for the same reason: whoever catches one going off sees that it
    happened and where, and who was at either end of it still has to be scanned."""
    tick: int
    abs_tick: int
    x1: float            # where it was fired from
    y1: float
    x2: float            # where it landed
    y2: float
    damage_type: str


@dataclass
class ObjectTick:
    """Where one object was at one tick. `abs_tick` orders across rounds.

    Heading and speed are None where it was seen rather than known: a scan records a position and
    never a course."""
    abs_tick: int
    x: float
    y: float
    heading: float | None
    speed: float | None


@dataclass
class ReplayObject:
    """One object over a whole game: what it is, and where it was at every tick it is known for.

    `owner` is what put it there, so a salvo reads as one ship's: a missile's owner is the ship
    that fired it, and a ship's owner is itself.

    `contact` says the path is a track of sightings rather than the object's own record, which is
    what a faction knows about anything it does not own. The end of such a path is losing sight of
    it and not its end."""
    name: str
    type_name: str
    category_name: str
    faction: str | None
    owner: str | None
    radius: float             # above 0 is terrain, drawn at its true size
    contact: bool
    path: list[ObjectTick]
    events: list[TickEvent]


@dataclass
class GameReplay:
    """A game as it was played, for a playhead to scrub over.

    `faction` is whose war it is. Only that side is built, and everything else is in it as the
    sightings its ships took, so nothing it never saw is there to be read out of what was sent.
    None is every side at once, which is more than anybody saw and is the director's alone."""
    game: str
    faction: str | None
    first_tick: int
    last_tick: int
    objects: list[ReplayObject]
    beams: list[Beam]


@dataclass
class PlayerPlan:
    game: str
    player: str
    factions: list[str]  # normally one; a player commanding ships in several gets all of them
    round: int           # the round this picture is drawn from
    last_round: int      # the newest round there is. Orders can only be changed while
                         # looking at it, since that is what the current round plans from.
    ready: bool          # the player has said they are done with the round being planned
    ships: list[ShipPlan]
    contacts: list[Contact]
    explosions: list[Explosion]
    effects: list[Effect]   # what the faction's own blows did, tick by tick
    beams: list[Beam]       # and the lines the beams among them arrived along