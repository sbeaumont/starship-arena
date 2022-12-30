import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from cfg import MANUAL_TEMPLATE, MANUAL_FILENAME
from ois.registry.builder import all_ship_types


def generate_manual():
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(MANUAL_TEMPLATE)

    template_data = {
        "starbase_types": [all_ship_types['SB2531'](), ],
        "ship_types": [st() for st in all_ship_types.values() if st.__name__ != 'SB2531'],
        "date": datetime.date.today().strftime('%d %b %Y'),
    }

    html_out = template.render(template_data)
    print_html = HTML(string=html_out, base_url=f'.')
    print_html.write_pdf(MANUAL_FILENAME)


if __name__ == '__main__':
    for st in all_ship_types:
        print(st)

    print('\nGenerating manual...')
    generate_manual()
    print('Done')
