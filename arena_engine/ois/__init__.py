"""
This package is part of the simulation engine. It holds all the different objects that may be in space
like spaceships, mines and rockets.

- ObjectInSpace is the base class for all space objects.
- MachineInSpace adds features that all man-made objects share and introduces the component system.
- Ship is a MachineInSpace that adds features to be player-controllable.

This package also has the Event class hierarchy that is used to model events in the game like scans,
explosions, hits, basically anything that would show up in a user's tick log.
"""