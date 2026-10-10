# The Ashen Circuit — Current Architecture UML

This document describes the current GitHub project architecture at the application,
gameplay, asset, and verification levels. It reflects the checked-in Python/Pygame
modules and the current character-animation pipeline.

## System context

```mermaid
flowchart TD
    User[Player input] --> Game[game.py\nGame loop]
    Game --> Frontend[TitleScreen\nfront-end states]
    Game --> World[WorldCombat\nexploration + encounters]
    Game --> Progression[ProgressionMixin\ntomes, stats, links]
    Game --> Persistence[SaveMenu + JSON\nslots and settings]
    Game --> Audio[pygame.mixer.music\nmenu, battle, defeat tracks]
    Game --> Render[Seamless renderer\nworld, HUD, sprites]
    Assets[assets/\nart, audio, maps] --> Render
    Assets --> Audio
    Tools[tools/\noffline builders and validators] --> Assets
    Tests[tests/\nunit and regression checks] -. verifies .-> Game
    Tests -. verifies .-> Tools
    Package[AppImage + GitHub Actions] --> Game
```

## Top-level application state machine

```mermaid
stateDiagram-v2
    [*] --> TITLE
    TITLE --> GAMEPLAY: New Game
    TITLE --> SAVE_MENU: Load Game
    TITLE --> OPTIONS: Options
    TITLE --> BESTIARY: Bestiary
    TITLE --> EXIT: Exit
    SAVE_MENU --> GAMEPLAY: Load slot
    SAVE_MENU --> TITLE: Cancel
    OPTIONS --> TITLE: Back / Cancel
    BESTIARY --> TITLE: Cancel
    GAMEPLAY --> TITLE: Return to title
    EXIT --> [*]: fade audio, quit pygame, sys.exit
```

## Runtime module UML

```mermaid
classDiagram
    class Game {
        +state: str
        +run()
        +handle_events()
        +update(dt)
        +draw(screen)
        +save_game(slot)
        +load_game(slot)
    }
    class TitleScreen {
        +state: str
        +handle_input(event)
        +update(dt)
        +draw(screen)
        +set_state(state)
        +play_music()
    }
    class SaveMenu {
        +slots: list
        +handle_input(event)
        +draw(screen)
        +load_selected()
    }
    class OptionsMenu {
        +settings: dict
        +handle_input(event)
        +draw(screen)
        +save_settings()
    }
    class BestiaryMenu {
        +entries: list
        +handle_input(event)
        +draw(screen)
    }
    class WorldCombat {
        +phase: str
        +pawns: list
        +patrols: list
        +arrive()
        +update(dt)
        +draw(screen)
        +begin_encounter()
        +resolve_action()
    }
    class Pawn {
        +x: float
        +y: float
        +direction: int
        +animation_state: str
        +step(goal, amount)
    }
    class ProgressionMixin {
        +flags: set
        +tomes: dict
        +apply_tome()
        +make_treasure()
    }
    class CombatSpriteRig {
        +draw_body()
        +draw_layers()
    }
    class BattleAnimationAtlas {
        +frame_rect(frame)
        +draw(target, frame, x, y, facing)
    }
    class DefeatScreen {
        +draw_defeat_screen()
    }
    class ExitUtils {
        +graceful_exit()
    }

    Game *-- TitleScreen
    Game *-- WorldCombat
    Game *-- ProgressionMixin
    Game *-- SaveMenu
    Game *-- OptionsMenu
    Game *-- BestiaryMenu
    Game *-- DefeatScreen
    Game --> ExitUtils
    WorldCombat *-- Pawn
    WorldCombat *-- CombatSpriteRig
    WorldCombat *-- BattleAnimationAtlas
    TitleScreen ..> SaveMenu
    TitleScreen ..> OptionsMenu
    TitleScreen ..> BestiaryMenu
```

## Gameplay and encounter flow

```mermaid
sequenceDiagram
    participant Input as Player input
    participant G as Game
    participant W as WorldCombat
    participant P as Pawn/party
    participant R as Renderer

    Input->>G: movement / menu / action
    G->>W: update(dt, command)
    W->>P: move, face, select animation
    W-->>G: field, forming, battle, returning
    G->>R: draw world + actors + HUD
    R-->>Input: updated frame
```

World encounters preserve room coordinates: exploration transitions into combat
without a separate battle arena or a sprite-size change. Combat actions select
data-driven clips (`battle_idle`, `battle_dash`, `sword_basic`, `sword_skill`,
`hurt`, and `defeated`) and return to the shared field renderer.

## Character asset pipeline

```mermaid
flowchart LR
    Reference[Approved reference art\nSNES-style poses] --> Source[tools/reference\nsource strips / atlases]
    Source --> Cleanup[Transparency cleanup\nnear-magenta + edge matte]
    Cleanup --> Normalize[Uniform scale +\nground alignment]
    Normalize --> Runtime[assets/characters/battle\ntransparent runtime strips]
    Runtime --> Loader[game.py loader\n1:1 blit, no runtime resize]
    Loader --> Combat[WorldCombat + CombatSpriteRig]
    Overworld[party overworld atlases\n64x64 cells] --> Loader
    Stances[character stance sheets\nRian / Tess / Merek / Brann] --> Combat
```

The current convention is 64×64 authored cells and 96×96 runtime battle cells
for the expanded action strips. Frames retain transparency, independent motion,
consistent ground anchoring, and uniform X/Y scaling. Rian's back/up guard strip
is sourced from the approved four-frame replacement and is excluded from any
older top-row sheet import.

## Offline tooling and verification

```mermaid
classDiagram
    class BuildTools {
        build_character_sheets_v2.py
        build_motion_sheet.py
        build_combat_layers.py
        build_battle_animation_atlas.py
        build_authored_stance_atlases.py
    }
    class RianTools {
        fix_rian_battle_transparency.py
        normalize_rian_battle_proportions.py
        replace_rian_back_guard.py
        audit_rian_battle_proportions.py
    }
    class Tests {
        test_title_screen.py
        test_save_menu.py
        test_options_menu.py
        test_bestiary_menu.py
        test_battle_animations.py
        test_rian_transparency.py
        test_seamless.py
        test_progression.py
        test_defeat_screen.py
        test_exit_utils.py
    }
    class Packaging {
        AppImageBuilder.yml
        AppRun
        ashen-circuit.spec
        .github/workflows/publish-release.yml
    }
    BuildTools --> Assets
    RianTools --> Assets
    Tests -. regression coverage .-> Assets
    Tests -. runtime coverage .-> Modules
    Packaging --> Modules
    class Assets
    class Modules
```

## Repository responsibilities

| Area | Main files/directories | Responsibility |
|---|---|---|
| Application | `game.py`, `title_screen.py` | Main loop, top-level states, resource loading |
| Exploration/combat | `seamless.py`, `battle_animations.py`, `combat_poses.py` | Shared field, encounters, actions, actor rendering |
| Menus | `save_menu.py`, `options_menu.py`, `bestiary_menu.py`, `pixel_ui.py` | Front-end UI and persistence-facing controls |
| Progression | `progression.py` | Tomes, stat changes, links, treasure and objective logic |
| Presentation | `render_config.py`, `defeat_screen.py`, `exit_utils.py` | Pixel dimensions, defeat overlay, graceful shutdown |
| Character art | `assets/characters/` | Overworld, battle-ready, combat layers, stance sheets |
| Audio | `assets/audio/` | Menu, battle, and game-over music |
| Build/release | `AppRun`, `AppImageBuilder.yml`, `.github/workflows/` | Executable launch and Linux release packaging |
| Verification | `tests/` | Menu, combat, sprite, transparency, progression, and shutdown checks |
