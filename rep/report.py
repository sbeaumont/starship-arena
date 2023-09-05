import os
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict
from weasyprint import HTML
from ois.event import ScanEvent, Event, DrawType, HitEvent
from ois.starbase import Starbase
from ois.ship import Ship
from ois.objectinspace import Point
from rep.visualize import Visualizer, COLORS
from cfg import *
from rep.history import Tick, TICK_ZERO


def text_nudge(pos: Point) -> Point:
    """Give text positions a nudge to clear them from the path lines."""
    return Point(pos.x + 2, pos.y - 2)


def report_events(ship: Ship, vis: Visualizer, start_tick: Tick):
    """Add events of the ship to the report and to the round overview graphic.
        Scans, DrawableEvents and other Events are handled separately."""
    events_per_tick = defaultdict(list)
    scans_per_tick = defaultdict(list)
    score_per_tick = defaultdict(int)
    current_tick = start_tick
    while current_tick.round == start_tick.round:
        if current_tick in ship.history:
            for event in ship.history[current_tick].events:
                assert isinstance(event, Event), f"{event} is not an Event"
                if isinstance(event, ScanEvent):
                    scans_per_tick[current_tick].append(event)
                else:
                    events_per_tick[current_tick].append(str(event))

                if isinstance(event, HitEvent) and event.source.owner == ship:
                    score_per_tick[current_tick] += event.score

                if event.draw_type:
                    match event.draw_type:
                        case DrawType.Line:
                            vis.draw_line(event.pos, color=COLORS[3])
                        case DrawType.Circle:
                            vis.draw_circle(event.pos, color=COLORS[3], size=event.radius)
        current_tick = current_tick.next
    return events_per_tick, scans_per_tick, score_per_tick


def find_boundaries(ship, start_tick: Tick, padding=50):
    """Find the optimal boundaries to fit everything the ship saw this round."""
    min_x = max_x = round(ship.history[start_tick]['pos'].x)
    min_y = max_y = round(ship.history[start_tick]['pos'].y)

    def stretch(xy):
        nonlocal min_x, min_y, max_x, max_y
        x = xy.x
        y = xy.y
        if x < min_x:
            min_x = x
        elif x > max_x:
            max_x = x
        if y < min_y:
            min_y = y
        elif y > max_y:
            max_y = y

    for t in start_tick.ticks_for_round:
        if t in ship.history:
            stretch(ship.history[t]['pos'])
            for scan in ship.history[t].scans:
                stretch(scan.pos)

    return min_x-padding, min_y-padding, max_x+padding, max_y+padding


def draw_round(ship: Ship, vis: Visualizer, start_tick: Tick):
    """Draw the paths of the ship and its scans"""
    # Initial location of ship
    vis.text(text_nudge(ship.history[start_tick.prev_round_end]['pos']), f"{ship.history[start_tick.prev_round_end]['pos'].as_tuple}")

    for t in start_tick.ticks_for_round:
        if t in ship.history:
            # Draw ship's path of this tick
            vis.draw_line((ship.history[t.prev]['pos'], ship.history[t]['pos']), color=COLORS[0])
            vis.draw_point(ship.history[t]['pos'], color=COLORS[0], size=2)

            # Draw scans of this tick
            for scan in ship.history[t].scans:
                vis.draw_point(scan.pos, size=2)
                prev_scan = ship.history[t.prev].scan_by_name(scan.name)
                if prev_scan:
                    # Draw line if there was an earlier scan
                    vis.draw_line((prev_scan.pos, scan.pos))
                if (t == ship.history.last) or (t.next in ship.history) and (not ship.history[t.next].scan_by_name(scan.name)):
                    # Last scan of this ois, write name and position
                    # vis.text(text_nudge(scan.pos), f"{i}:{scan.name}\n{scan.pos}")
                    vis.text(text_nudge(scan.pos), f"{t.tick}:{scan.name}")

    # Final location of ship
    max_pos = ship.history[ship.history.last]['pos']
    vis.text(text_nudge(max_pos), f"{ship.history.last.tick}:{ship.name}\n{max_pos.as_tuple}")


def report_round(ships: dict, game_dir: str, round_nr: int):
    """Generate HTML and PDF reports with the results, status and history of each ship in the round."""
    start_tick = Tick(round_nr, 0)
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(ROUND_TEMPLATE)

    # Set up round directory
    round_name = f"round-{round_nr}"
    round_dir = os.path.join(game_dir, round_name)
    if not os.path.exists(round_dir):
        os.mkdir(round_dir)

    for ship in [s for s in ships.values() if isinstance(s, Ship) or isinstance(s, Starbase)]:
        boundaries = find_boundaries(ship, start_tick, padding=50)
        vis = Visualizer(boundaries, scale=2)
        events_per_tick, scans_per_tick, scores_per_tick = report_events(ship, vis, start_tick)
        draw_round(ship, vis, start_tick)
        image_file_name = f'{ship.name}-{round_name}.png'
        vis.save(os.path.join(round_dir, image_file_name))

        template_data = {
            "image_file_name": image_file_name,
            "ship": ship,
            "events": events_per_tick,
            "scans": scans_per_tick,
            "scores": scores_per_tick,
            "final_scans": scans_per_tick.get(start_tick.round_end, list()),
            "round": round_nr,
            "start_tick": start_tick
        }

        html_out = template.render(template_data)
        report_file_name = f'{round_dir}/{ship.name}-{round_name}'
        with open(f'{report_file_name}.html', 'w') as fj:
            fj.write(html_out)

        print_html = HTML(string=html_out, base_url=f'{game_dir}/{round_name}')
        print_html.write_pdf(f'{report_file_name}.pdf')


def report_round_zero(game_dir: str, ships: list):
    start_tick = TICK_ZERO
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(ROUND_ZERO_TEMPLATE)

    # Set up round directory
    round_dir = os.path.join(game_dir, ROUND_ZERO_NAME)
    if not os.path.exists(round_dir):
        os.mkdir(round_dir)

    for ship in ships:
        boundaries = find_boundaries(ship, start_tick, padding=50)
        vis = Visualizer(boundaries, scale=2)
        draw_round(ship, vis, start_tick)
        image_file_name = f'{ship.name}-{ROUND_ZERO_NAME}.png'
        vis.save(os.path.join(round_dir, image_file_name))

        template_data = {
            "image_file_name": image_file_name,
            "ship": ship,
            "scans": ship.history[start_tick].scans,
            "ships": ships
        }

        html_out = template.render(template_data)
        report_file_name = os.path.join(round_dir, f'{ship.name}-{ROUND_ZERO_NAME}')
        with open(f'{report_file_name}.html', 'w') as fj:
            fj.write(html_out)

        print_html = HTML(string=html_out, base_url=f'{game_dir}/{ROUND_ZERO_NAME}')
        print_html.write_pdf(f'{report_file_name}.pdf')
