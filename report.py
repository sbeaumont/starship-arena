from history import DrawableEvent
from ship import Ship
from visualize import Visualizer, COLORS
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict
from weasyprint import HTML


def text_nudge(pos):
    """Give text positions a nudge to clear them from the path lines."""
    return pos[0] + 2, pos[1] - 2


def report_events(ship: Ship, vis: Visualizer):
    events_per_tick = defaultdict(list)
    for i in range(1, 11):
        if i in ship.history:
            for event in ship.history[i].events:
                events_per_tick[i].append(str(event))
                if isinstance(event, DrawableEvent):
                    match event.event_type:
                        case 'Laser':
                            vis.draw_line(event.position_or_line, color=COLORS[3])
                        case 'Explosion':
                            vis.draw_circle(event.position_or_line, color=COLORS[3], size=20)
    return events_per_tick


def find_boundaries(ship, padding=50):
    min_x = max_x = round(ship.history[0].pos[0])
    min_y = max_y = round(ship.history[0].pos[1])

    def stretch(xy):
        nonlocal min_x, min_y, max_x, max_y
        x, y = xy
        if x < min_x:
            min_x = x
        elif x > max_x:
            max_x = x
        if y < min_y:
            min_y = y
        elif y > max_y:
            max_y = y

    for i in range(11):
        if i in ship.history:
            stretch(ship.history[i].pos)
            for scan in ship.history[i].scans.values():
                stretch(scan.pos)

    return min_x-padding, min_y-padding, max_x+padding, max_y+padding


def draw_round(ship: Ship, vis: Visualizer):
    # Initial location of ship
    vis.text(text_nudge(ship.history[0].pos), f"{ship.history[0].pos}")

    max_history = max(ship.history.keys())
    for i in range(1, 11):
        if i in ship.history:
            # Draw ship's path of this tick
            vis.draw_line((ship.history[i - 1].pos, ship.history[i].pos), color=COLORS[0])
            vis.draw_point(ship.history[i].pos, color=COLORS[0], size=2)

            # Draw scans of this tick
            for scan in ship.history[i].scans.values():
                if scan.name in ship.history[i - 1].scans:
                    # Draw line if there was an earlier scan
                    vis.draw_line((scan.ois.history[i - 1].pos, scan.pos))
                    vis.draw_point(scan.pos, size=2)
                if (i == max_history) or (i + 1 in ship.history) and (scan.name not in ship.history[i + 1].scans):
                    # Last scan of this ois, write name and position
                    vis.text(text_nudge(scan.pos), f"{i}:{scan.name}\n{scan.pos}")

    # Final location of ship
    max_history = max(ship.history.keys())
    vis.text(text_nudge(ship.history[max_history].pos), f"{max_history}:{ship.name}\n{ship.history[max_history].pos}")


def report_round(ships: dict, game_dir: str, round_nr: int):
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template('round-template.html')

    for ship in [s for s in ships.values() if isinstance(s, Ship)]:
        boundaries = find_boundaries(ship, padding=50)
        vis = Visualizer(boundaries, scale=2)
        events_per_tick = report_events(ship, vis)
        draw_round(ship, vis)
        image_file_name = f'{ship.name}-round-{round_nr}.png'
        vis.save(f"{game_dir}/{image_file_name}")

        template_data = {
            "image_file_name": image_file_name,
            "ship": ship,
            "events": events_per_tick,
            "round": round_nr
        }

        html_out = template.render(template_data)
        report_file_name = f'{game_dir}/{ship.name}-round-{round_nr}'
        with open(f'{report_file_name}.html', 'w') as fj:
            fj.write(html_out)

        print_html = HTML(string=html_out, base_url=f'{game_dir}')
        print_html.write_pdf(f'{report_file_name}.pdf')


