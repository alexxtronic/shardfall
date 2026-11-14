# Shardfall

A mobile, landscape, real-time strategy game in full 3D, built in Godot 4.7 (Mobile renderer). It follows the StarCraft II format (gather, build, expand, out-produce, out-fight) with controls made for a touchscreen. You play one race against a bot in a 1v1 on one of three themed maps with high ground, ramps and hazards, and climb a rated leaderboard.

- **Ambron**: precision robots of cream and gold.
- **Void**: a living swarm of chitin, bone and acid.

Both races have the same power for the resources spent. Every unit fills a shared slot with the same cost, supply and build time. Void units have 15% more health and fire 15% slower, so damage per second times health comes out equal. The headless balance harness checks this in thousands of simulated battles (see [docs/BALANCE.md](docs/BALANCE.md)).

## Play

On a Mac with Godot 4.7 in `/Applications`, double-click `Play.command`, or run:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path . --resolution 1280x720
```

To skip the title screen and play Ambron against a Void bot straight away (the map is optional):

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path . -- --play=ambron,void,frostspire
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
- **High ground.** Plateaus sit 2.6 m above the ground below, edged by cliffs that nothing walks over. Ramps are the only way up. A ground unit can't see up a cliff until it climbs, and a ground shot fired uphill misses 30% of the time. Flyers ignore both.
- **Winning.** Destroy every enemy building.

## Maps

All three are exact 180-degree mirrors with five bases per side (8 crystals and 2 slime piles each). Each has its own sky, light, ground, weather, music and ambience.

| Map | Theme | Shape |
|---|---|---|
| Shatterfield | Violet basalt, drifting spores | Mains on high ground with one ramp; a central ridge overlooks the middle bases |
| Frostspire Pass | Glacier, snowfall | Three tiers: mains on the top shelf, naturals one step down, frozen lakes in the low passes |
| Ember Rift | Volcanic, embers and ash | A lava river splits the map, with three crossings watched from basalt mesas |

## Leaderboard

Your commander profile (`user://profile.json`) keeps the following:
- **Rating.** An Elo rating against the bot's difficulty (easy 800, normal 1200, hard 1600). It starts at 1000.
- **Tier.** Bronze to Master.
- **Score.** A best score per map, and the last 40 games.

The ladder ranks you among 13 AI rival commanders with fixed ratings. The end screen shows your score, rating change and rank. Rename your commander in the leaderboard. Settings (volumes and screen shake) live in `user://settings.cfg`.

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
  - **Simulation:** `world.gd`, `unit.gd`, `building.gd`, `path_grid.gd`, `fog.gd` and `terrain.gd` (levels, cliffs, ramps). It steps on its own, so it runs headless at any speed.
  - **Maps:**
    - `maps.gd` holds each map as data (bases, plateaus, ramps, rocks, hazards) and its theme;
    - `map_gen.gd` builds it, authoring player 1's half and mirroring it;
    - `weather.gd` adds the particles.
  - **Interface:**
    - `commander.gd` (touch input and orders), `hud.gd`, `minimap.gd`, `overlay.gd`, `camera_rig.gd`;
    - `title.gd` and the overlays `settings_panel.gd`, `leaderboard_panel.gd` and `credits_panel.gd`;
    - `prefs.gd` (settings) and `profile.gd` (rating, scores, history), both autoloads.
  - **Opponent:** `bot_ai.gd`, the bot, which plays by the same rules (easy, normal, hard).
  - **Look and sound:**
    - `models.gd` loads GLBs and animates them; `fx.gd` makes the effects.
    - `sfx.gd` plays the effects in `assets/sfx/`. It also runs the music in `assets/music/` (a calm track per map, crossfading to a battle track during fights), the ambience in `assets/ambience/` and the announcer in `assets/voice/`.
    - All the audio is CC0; see [assets/CREDITS.md](assets/CREDITS.md).
  - **Data:** `defs.gd` holds every number in the game.
- `assets/models/<id>.glb` and `assets/icons/<id>.png` are the art. `docs/ART_SPEC.md` is the contract every model follows.
- `art/<group>/build.py` are the Blender scripts that build each art group, with a production log per asset and the final review renders.

## Tests

- **Autotest.** It plays the game in a real window and saves screenshots. It covers the touch controls, building, training, combat, expanding, both races, the UI flow, and a whole bot-vs-bot game to the end screen:

  ```bash
  /Applications/Godot.app/Contents/MacOS/Godot --path . --resolution 1280x720 -- --autotest=/tmp/shardfall_shots
  ```

  Add `--only=touch,ui` to run selected sections:
  - `title`, `economy`, `touch`, `build`, `army`, `combat`, `expand`, `void`, `ui`, `models`, `fx` and `full`;
  - `maps`: each map is an exact mirror, every base is reachable and fully stocked;
  - `terrain`: ramps, cliffs, uphill misses, picking on plateaus;
  - `profile`: rating, scores and the results screen;
  - `seats`: neither seat starts ahead (mirrored grid, equal harvest, equal march to the enemy).

  `--only=previews` is not a test. It re-bakes the map previews (`assets/ui/maps/`), the app icon and the boot splash after a map or art change.
- **Balance.** It runs headless and rewrites `docs/BALANCE.md`:

  ```bash
  /Applications/Godot.app/Contents/MacOS/Godot --headless --path . -- --balance
  ```

  Add `--quick` for fewer trials or `--nogames` to skip the full games. `-- --balance --game --seed=N` prints a timeline of one bot-vs-bot game (`--map=ID`, `--races=a,b` and `--swap` pick the map, the races and the seats).
- **Script check.** It loads every script, so all parse errors show at once:

  ```bash
  /Applications/Godot.app/Contents/MacOS/Godot --headless --path . res://tools/check.tscn
  ```

## Status

The game is playable end to end:
- race, map and bot selection, then a full 1v1 against a bot;
- three themed maps with elevation, plus music, ambience and an announcer;
- a rated leaderboard, settings, credits, an app icon and a boot splash;
- both resources, with workers that harvest and build;
- every building and unit of both races, plus a defence tower each;
- an icon-based interface in Orbitron and Chakra Petch (both OFL, in `assets/fonts`);
- a rocky alien ground with cracked plates, craters and mounds under the rock walls;
- expansions, fog of war and a victory screen.

The core units come from Tripo: ChatGPT concept art goes to a Tripo model, then `art/tripo/build.py` decimates it, splits the team and glow materials, rigs it and animates it in Blender (see [art/tripo/README.md](art/tripo/README.md)). The Ambron Harvester is Alex's own Tripo "robot crystal harvester". All 16 buildings (8 per race, towers included) are Kiln models: each starts from a ChatGPT concept in `art/<race>_buildings/concepts/`, is built in Kiln JavaScript to match it (`art/kiln/<id>.kiln.js`, review sheet in `art/kiln/review/`), then `art/kiln/finish.py` merges it in Blender into one `body` mesh plus any `float_*` or `turret` node, and `art/kiln/icons.py` renders its build-menu icon. Resources and the rest of the art are built procedurally in Blender.

iOS export needs Godot's export templates installed. Until then the game runs on the Mac in a landscape window. Two plans cover what comes next:
- [docs/MOBILE_MULTIPLAYER.md](docs/MOBILE_MULTIPLAYER.md): shipping to the stores, and ranked real-time 1v1 online;
- [docs/ROADMAP.md](docs/ROADMAP.md): what to build next.
