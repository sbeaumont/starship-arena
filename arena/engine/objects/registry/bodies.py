from arena.engine.objects.body import Body, BodyType


class Asteroid(BodyType):
    """A rock big enough to matter at the scale ships fly at."""
    base_type = Body
    radius = 40