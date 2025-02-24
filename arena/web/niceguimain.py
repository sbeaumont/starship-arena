from contextlib import contextmanager
from nicegui import ui, app

@contextmanager
def frame():
    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between'):
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
        ui.label('HEADER')
        # ui.button(on_click=lambda: right_drawer.toggle(), icon='menu').props('flat color=white')
    # with ui.left_drawer(top_corner=True, bottom_corner=True).style('background-color: #d7e3f4'):
    #     ui.label('LEFT DRAWER')
    # with ui.right_drawer(fixed=False).style('background-color: #ebf1fa').props('bordered') as right_drawer:
    #     ui.label('RIGHT DRAWER')
    with ui.left_drawer(fixed=False).style('background-color: #ebf1fa').props('bordered') as left_drawer:
        ui.label('RIGHT DRAWER')
    # with ui.footer().style('background-color: #3874c8'):
    #     ui.label('FOOTER')
    ui.query('body').style('background-image: /static/gfx/starfield.jpg')
    yield

@ui.page('/other_page')
def other_page():
    ui.page_title('Other Page')
    with frame() as ctx:
        with ui.row():
            with ui.column():
                ui.label("Column 1")
            with ui.column():
                ui.label("Column 2")

        with ui.row():
            ui.label("Row 2")
            ui.label('Welcome to the other side')

@ui.page('/dark_page', dark=True)
def dark_page():
    with frame():
        with ui.interactive_image('/static/gfx/starfield.jpg'):
            ui.label('Dark Page Content')

ui.link('Visit other page', other_page)
ui.link('Visit dark page', dark_page)

app.add_static_files('/static', 'static')
ui.run()