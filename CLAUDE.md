# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Starship Arena is a recreation of a 1991 Play-By-Mail space combat game. Players command starships in turn-based rounds consisting of 10 ticks each. The game supports multiple interfaces: a CLI, a Flask admin/director web app, and a FastAPI JSON API. An interactive Svelte game UI is being built on top of the API.

## Architecture

The codebase follows a component-based architecture with these core packages:

- **arena/engine/**: Core game engine with game logic, rounds, and commands
- **arena/engine/objects/**: Game objects (ships, missiles, mines) built using a component system
- **arena/engine/objects/registry/**: Ship type definitions and object creation factory
- **arena/admin_ui/**: Flask admin/director web app (was `arena/web`)
- **arena/api/**: FastAPI JSON API, split into game and admin surfaces
- **arena/app/**: UI-agnostic application-services layer shared by the interfaces (hides storage)
- **arena/cli/**: Command-line interface
- **test/**: Test suite with game scenarios and unit tests

### Key Architectural Patterns

- **Component System**: Game objects are composed of reusable components (weapons, scanners, defense, etc.)
- **Command Pattern**: Player actions implemented as command objects with validation
- **Type Objects**: Ship types defined as separate objects that configure ship instances
- **History/Memory System**: Objects maintain history for reporting and visualization
- **Pickle Persistence**: Game state stored as pickle files for rounds and object status

## Development Commands

### Running the Application

```bash
# Install / sync the environment (uv manages the venv and Python 3.14)
uv sync

# CLI interface
uv run python arena/cli/main.py [setup|generate|manual|send] <game_name>

# Flask admin/director web app
uv run flask --app arena.admin_ui.app:app run --host=0.0.0.0 -p 8080

# FastAPI JSON API (hot reload)
bash arena-api.sh           # -> http://localhost:8000

# Svelte game UI dev server (hot module reload; proxies /api to the API above)
bash arena-game-ui.sh       # -> http://localhost:5173

# Alternative web runners
bash arena-web.sh           # Flask
bash arena-dev-web.sh       # Development Flask
```

### Testing

```bash
# Run specific test files (the test group provides httpx2 for the API TestClient)
uv run --group test python -m unittest test.engine.test_game_one
uv run --group test python -m unittest test.api.test_fastapimain

# Run test scenarios
uv run python test/engine/test.py
uv run python test/engine/test_run_test_games.py
```

### Game Management

```bash
# Set up a new game
uv run python arena/cli/main.py setup <game_name>

# Generate/process rounds
uv run python arena/cli/main.py generate <game_name>

# Generate manual PDF
uv run python arena/cli/main.py manual

# Send results via email
uv run python arena/cli/main.py send <game_name> -s manual zero last
```

## Configuration

- **GAME_DATA_DIR**: Environment variable or `secret.GAME_DATA_DIR` for game data location
- **Game Structure**: Each game has `ships.txt`, `commands/`, `round-X/` directories, and pickle files
- **Persistence**: Game state stored in `status_round_X.pickle` files, graveyard in `graveyard.pickle`

## Key Files and Patterns

- **arena/engine/objects/registry/builder.py**: Factory for creating ships using `create()` function
- **arena/admin_ui/appfacade.py**: Semantic facade for the Flask admin UI (each UI has its own; shared logic lives in arena/app)  
- **arena/cfg.py**: Central configuration with file templates and game constants
- **test/test-games/**: Example game scenarios for testing and development

## Component System Usage

When creating new ship types or objects:
1. Define components in `arena/engine/objects/components/`
2. Create ship type classes in `arena/engine/objects/registry/`
3. Use the builder pattern: `create(name, type_name, position)`
4. Components are automatically discovered and attached via metaclass system

## Interface Architecture

The engine is wrapped by a UI-agnostic application-services layer (`arena/app/`) that hides
storage (currently pickle files) behind domain operations. Each user interface has its own
semantic facade on top of that layer:

- **Flask admin/director UI** (`arena/admin_ui/app.py`): game setup, turn processing, command
  management, and archive views. May reach lower-level concepts.
- **FastAPI JSON API** (`arena/api/`): split into a **game** surface (player-facing, restricted:
  ship state, time-travel, move planning) and an **admin** surface (lower-level operations).
- **Svelte game UI** (`game-ui/`, in progress): the interactive player experience, consuming the
  game API.

Do not expose storage details (e.g. `GameDirectory`, pickle paths) above the services layer.

## Code Style Philosophy

This codebase is hand-crafted with intention. When making changes:
- **Keep it simple** - No layers of defensive programming or over-engineering
- **Sparse, readable code** - Prefer clarity over cleverness
- **Minimal dependencies** - Avoid adding complex libraries unless absolutely necessary
- **Direct approach** - Don't create abstractions unless they solve a real problem

The existing code is deliberately straightforward. Maintain this philosophy in all modifications.