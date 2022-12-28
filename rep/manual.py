import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from cfg import MANUAL_TEMPLATE, MANUAL_FILENAME
from ois.starbase import all_starbase_types
from ois.ship import all_ship_types


def generate_manual():
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(MANUAL_TEMPLATE)

    template_data = {
        "starbase_types": all_starbase_types.values(),
        "ship_types": all_ship_types.values(),
        "date": datetime.date.today().strftime('%d %b %Y'),
    }

    html_out = template.render(template_data)
    print_html = HTML(string=html_out, base_url=f'.')
    print_html.write_pdf(MANUAL_FILENAME)
