"""
Data Transfer Objects for the application-services layer (arena/app).

Plain dataclasses, deliberately free of any UI/framework dependency (no FastAPI,
no pydantic) so this layer stays UI-agnostic. They carry domain data only and never
storage details such as GameDirectory or file paths.
"""

from dataclasses import dataclass, field


@dataclass
class GameSummary:
    name: str
    current_round: int


@dataclass
class ShipSummary:
    name: str
    ship_type: str
    player: str | None   # None for a ship no one commands
    score: int
    alive: bool
    orders_in: bool      # whether orders for the current round have been handed in


@dataclass
class FactionSummary:
    name: str
    score: int           # what its ships have scored between them
    ships: list[ShipSummary]


@dataclass
class GameOverview:
    """Who is playing a game and how they are doing, enough to pick whose view to open."""
    name: str
    last_round: int
    factions: list[FactionSummary]


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
class ComponentStatus:
    """What a component reports, next to what the type object reports for a pristine one.

    The pairs are the component's own, so a reader renders what it is handed. Ordered as the
    machine carries them: defense, weapons, ECM."""
    name: str
    status: dict[str, str]
    full: dict[str, str]


@dataclass
class TickCondition:
    """What a ship was down to at the end of a tick. The map already shows where it was."""
    tick: int
    hull: int
    battery: int
    shields: dict[str, str]


@dataclass
class TickEvent:
    """Something that happened to a ship on a tick. Scans are left out; the map draws those."""
    tick: int
    text: str
    kind: str   # 'internal' | 'hit' | 'explosion'


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
    friendly: bool      # owner's faction == the planning faction
    track: list[TrackPoint]


@dataclass
class WeaponInput:
    """One input a weapon needs before it can be given an order. `kind` tells an interface
    which control to offer; min/max are filled in when the input is a bounded number."""
    name: str
    kind: str
    min: float | None = None
    max: float | None = None


@dataclass
class WeaponInfo:
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
    inputs: list[WeaponInput]


@dataclass
class ShipPlan:
    name: str
    ship_type: str
    category_name: str   # 'Ship' or 'Starbase'; a starbase is drawn, and flies, differently
    x: float
    y: float
    heading: float
    speed: float
    hull: int
    max_hull: int
    battery: int
    max_battery: int
    player: str | None   # who commands it
    player_ready: bool   # whether they have said they are done with the round being planned
    owned: bool          # True = this player's ship (editable); False = faction ally (context)
    limits: ShipLimits
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