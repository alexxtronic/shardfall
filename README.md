# Shardfall

A mobile, landscape, real-time strategy game in full 3D, built in Godot 4.7 (Mobile renderer). It follows the StarCraft II format (gather, build, expand, out-produce, out-fight) with controls made for a touchscreen. You play one race against a bot in a 1v1 on the map Shatterfield.

- **Ambron**: precision robots of cream and gold.
- **Void**: a living swarm of chitin, bone and acid.

Both races have the same power for the resources spent. Every unit fills a shared slot with the same cost, supply and build time. Void units have 15% more health and fire 15% slower, so damage per second times health comes out equal. The headless balance harness checks this in thousands of simulated battles (see [docs/BALANCE.md](docs/BALANCE.md)).

## Play

On a Mac with Godot 4.7 in `/Applications`, double-click `Play.command`, or run:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path . --resolution 1280x720
```

To skip the title screen and play Ambron against a Void bot straight away:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path . -- --play=ambron,void
```

The mouse stands in for a finger (one press is one touch). You can also use these desktop extras:

- right-click for a smart command;
- the mouse wheel to zoom;
- WASD or the arrow keys to pan;
- Q for attack, X to stop, H to hold;
- Tab to jump to your base;
- Ctrl plus 1–5 to save a control group.

## How to play

- **Start.** Each side begins with a main base and 6 workers.
- **Economy.** Workers harvest golden crystals on their own (5 per trip). A worker carries a crystal only while it is bringing one back. Void Slime, the second resource, needs an extractor built on a black slime pile first: the Void Machine for Ambron, the Void Maw for Void. Three workers per extractor saturate it.
- **Base and production.** Every main base trains workers and is a drop-off. Supply structures raise the supply cap, which tops out at 200. The tech tree runs:
  - main base;
  - infantry building (ranged and heavy infantry);
  - vehicle building, or beast building for Void (flame and missile units);
  - air building (light and heavy flyers);
  - special building (one huge late-game unit).
- **Ambron power.** Every Ambron structure except the main base, Power Relays and the Void Machine must stand inside a finished Power Relay's field, which shows as a cyan circle while you place a building. An unpowered building stops training and an unpowered tower stops firing until a relay covers it again. Void can build anywhere.
- **Defence towers.** Once you have an infantry building you can build a tower: the Ambron Arc Tower throws lightning, the Void Slime Spire lobs slime. Both hit ground and air, with the same numbers apart from the usual Void health and fire-rate difference.
- **Expanding.** Build another main base on any of the 8 open sites. Every site has 8 crystal nodes and 2 slime piles.
- **Touch controls:**
  - Tap to select. Double-tap or hold a unit to select every unit of that type on screen. Hold, then drag, to draw a selection box.
  - With an army selected, tap the ground to attack-move or tap an enemy to attack it. With workers selected, tapping the ground moves them and tapping crystals or an extractor sends them to harvest.
  - Drag to pan, pinch to zoom, and tap the minimap to jump the camera.
  - ARMY selects every fighter, IDLE selects idle workers, and BASE jumps to your main. BUILD opens the structures; the nearest worker builds them.
- **Winning.** Destroy every enemy building.

## Units

| Slot | Ambron | Void | Cost (crystals/slime) | Supply | Role |
|---|---|---|---|---|---|
| Worker | Harvester | Drudge | 50/0 | 1 | Harvests and builds |
| Infantry | Lancer | Spitter | 50/0 | 1 | Ranged, hits air and ground |
| Heavy | Bulwark | Mauler | 100/25 | 2 | Armoured, small splash, beats light units |
| Flame | Scorcher | Acidback | 125/25 | 2 | Short-range splash, burns light units |
| Missile | Hailfire | Spinefiend | 125/75 | 3 | Long-range artillery, shreds armour |
| Light air | Dart | Skitter | 100/50 | 2 | Fast, hunts air |
| Heavy air | Monolith | Gorgon | 250/150 | 4 | Gunship, pounds armoured ground |
| Special | Sovereign | Leviathan | 400/300 | 8 | Colossal splash beam, hits air and ground |

The counters form a web, measured in [docs/BALANCE.md](docs/BALANCE.md):
- Infantry beat both kinds of air and lose to heavies, flamers and specials.
- Missiles beat heavies and flamers.
- Air beats everything on the ground except infantry and specials.
- Missiles and gunships are the answer to a special.

## Project layout

- `scripts/` holds the game code, in GDScript:
  - **Simulation:** `world.gd`, `unit.gd`, `building.gd`, `map_gen.gd`, `path_grid.gd`, `fog.gd`. It is deterministic and steps on its own, so it runs headless at any speed.
  - **Interface:** `commander.gd` (touch input and orders), `hud.gd`, `minimap.gd`, `overlay.gd`, `camera_rig.gd`.
  - **Opponent:** `bot_ai.gd`, the bot, which plays by the same rules (easy, normal, hard).
  - **Look and sound:** `models.gd` loads GLBs and animates them; `fx.gd` and `sfx.gd` make the effects and synthesised sound.
  - **Data:** `defs.gd` holds every number in the game.
- `assets/models/<id>.glb` and `assets/icons/<id>.png` are the art. `docs/ART_SPEC.md` is the contract every model follows.
- `art/<group>/build.py` are the Blender scripts that build each art group, with a production log per asset and the final review renders.

## Tests

- **Autotest.** It plays the game in a real window and saves screenshots. It covers the touch controls, building, training, combat, expanding, both races, the UI flow, and a whole bot-vs-bot game to the end screen:

  ```bash
  /Applications/Godot.app/Contents/MacOS/Godot --path . --resolution 1280x720 -- --autotest=/tmp/shardfall_shots
  ```

  Add `--only=touch,ui` to run selected sections. The sections are `title`, `economy`, `touch`, `build`, `army`, `combat`, `expand`, `void`, `ui`, `models`, `fx` and `full`. `economy` also checks that the map is an exact 180-degree mirror, so neither seat starts ahead.
- **Balance.** It runs headless and rewrites `docs/BALANCE.md`:

  ```bash
  /Applications/Godot.app/Contents/MacOS/Godot --headless --path . -- --balance
  ```

  Add `--quick` for fewer trials or `--nogames` to skip the full games. `-- --balance --game --seed=N` prints a timeline of one bot-vs-bot game.
- **Script check.** It loads every script, so all parse errors show at once:

  ```bash
  /Applications/Godot.app/Contents/MacOS/Godot --headless --path . res://tools/check.tscn
  ```

## Status

The MVP is playable end to end:
- race selection, then a full 1v1 against a bot;
- both resources, with workers that harvest and build;
- every building and unit of both races, plus a defence tower each;
- an icon-based interface in Orbitron and Chakra Petch (both OFL, in `assets/fonts`);
- a rocky alien ground with cracked plates, craters and mounds under the rock walls;
- expansions, fog of war and a victory screen.

The core units come from Tripo: ChatGPT concept art goes to a Tripo model, then `art/tripo/build.py` decimates it, splits the team and glow materials, rigs it and animates it in Blender (see [art/tripo/README.md](art/tripo/README.md)). The Ambron Harvester is Alex's own Tripo "robot crystal harvester". The buildings, resources and the rest of the art are built procedurally in Blender.

iOS export needs Godot's export templates installed. Until then the game runs on the Mac in a landscape window.
