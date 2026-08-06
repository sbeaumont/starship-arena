"""
Generate the game manual, also using the code - like the ois.registry - to generate the correct ship stats.
"""

import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from arena.cfg import MANUAL_TEMPLATE, MANUAL_TEMPLATE_DIR, MANUAL_FILENAME, WEB_ROOT
from arena.engine.objects.registry.builder import all_ship_types, all_starbase_types


def generate_manual():
    env = Environment(loader=FileSystemLoader(MANUAL_TEMPLATE_DIR))
    template = env.get_template(MANUAL_TEMPLATE)

    template_data = {
        "starbase_types": list(all_starbase_types.values()),
        "ship_types": list(all_ship_types.values()),
        "date": datetime.date.today().strftime('%d %b %Y'),
    }

    html_out = template.render(template_data)
    print_html = HTML(string=html_out, base_url=WEB_ROOT)
    print_html.write_pdf(MANUAL_FILENAME)
    print("Manual written to {}".format(MANUAL_FILENAME))


if __name__ == '__main__':
    for st in all_ship_types:
        print(st)

    print('\nGenerating manual...')
    generate_manual()
