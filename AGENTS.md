# Notes for agents working on Shardfall

Read README.md first. This file holds the rules that aren't obvious from the code.

## Balance rule (Alex, 2026-11-14)

Both races must have identical power per resource spent. Never give one race a unit the other lacks.
- **Shared numbers:** change cost, supply, time, range, speed or damage in `Defs.UNIT_SLOTS`, which both races share.
- **Race differences:** the only difference is `VOID_HP_MULT` and `VOID_CD_MULT`, which must stay equal so DPS x HP is unchanged.
- **After a stat change,** run the balance harness:
  - each mirror slot's margin should stay within about ±10%;
  - the overall Ambron win rate should stay near 50%;
  - every unit should keep both a counter and a target it beats.

## Simulation

- **Stepping:** `World.step(dt)` steps everything. Nothing in the sim may depend on rendering, frame rate or real time. That is what lets the balance harness and the bot games run headless and fast.
- **Positions:** units live on the ground plane as `p: Vector2`, and `x, y` of `p` map to Godot `x, z`. Air units add `fly` height.
- **Pathing:** `PathGrid` is a 1 m grid. Buildings, rocks and resources mark cells solid.
  - Main bases may only go on the hand-placed site cells.
  - Other buildings use `World.suggest_spot` to keep a one-cell lane and stay off crystal lines.
- **The bot:** `BotAI` uses the same costs and rules as the player, with no extra income.
  - Four levels in `BotAI.LEVELS`: easy, normal, hard, extreme. Alex found the old Normal far too hard (2026-11-15), so it became Hard, the old Hard became Extreme, and Normal is a much gentler bot that holds its first attack until minute 7 (Easy: minute 9) and caps its army near one wave's size (`hoard`), since a delayed bot otherwise arrives with a 50-supply first wave. Bot-vs-bot runs (the harness, the `full` autotest, the Bench) use hard, which is what the balance numbers were measured on. Run `-- --balance --game --seed=N` to read its game timeline when tuning it.
  - Add `--map=ID --races=a,b` to choose the matchup, and `--swap` to start each player on the other main. A swapped game should come out as the mirror image of the unswapped one.
  - Each bot rolls a little variety at the start (first wave size, wave growth, expansion timing, think phase), from the same range for both seats. Keep it: without it, both bots launch on the same second and the map's tiniest asymmetry decides every game.
- **Mirror fairness (2026-11-14):** both seats must face exactly the same game.
  - Never break an equal-distance tie by scan order, because a fixed order favours one corner and the mirrored seat resolves it differently.
  - Break ties toward a reference point that mirrors with the seat: the requester, or the map centre. `PathGrid.nearest_walkable` and `World.suggest_spot` do this.
  - The `seats` autotest checks that the grid is an exact mirror, that both seats harvest alike, and that the march to the enemy main is within 2%.

## Art pipeline (Alex, 2026-11-14)

1. **Reference first.** Every new model starts with a ChatGPT reference image in the game's style, made before any modelling.
   - Attach `art/ref/<race>_style_reference.png` and a finished concept from `art/tripo/concepts/` as style references.
   - Show one asset only, in a three-quarter front view from slightly above, on a flat light-grey background.
   - Save the image as `art/<group>/concepts/shardfall_<id>.png`.
2. **Pick the tool for what it does best.**
   - **Kiln:** hard-surface, architectural and modular art, such as buildings, extractors, supply structures, resource nodes, rocks, map props, and projectile or effect meshes. Use the `kiln-author-asset`, `kiln-refine-asset` and `kiln-qa-asset` skills and the `kiln_workspace` MCP server (`.kiln/AGENTS.md`).
     - Build the model in Kiln JavaScript from the reference, and compare Kiln's renders against the reference before exporting the GLB.
     - Export the source to `art/kiln/<id>.kiln.js` and commit it. `.kiln/programs` is a local store and stays out of git.
   - **Tripo:** organic creatures and character units (`art/tripo/README.md`).
   - **Blender:** fitting, rigging and animating Tripo models, plus any finishing pass on a Kiln GLB (splitting team and glow materials, applying the triangle budget).
3. **Kiln models follow the art contract below.** Kiln is Y-up like glTF, so a Kiln model stands on y = 0 and faces +Z. That is the same as Blender's −Y front.
4. **Buildings (Alex, 2026-11-14).** Every building of both races gets its own ChatGPT inspiration image, made in Alex's Chrome. Kiln then builds it to match that image as closely as possible: silhouette, proportions, colours and details. Compare the Kiln renders side by side with the image before exporting.

## Gameplay rules (Alex, 2026-11-14)

- **Start:** each player begins with 6 workers (`Defs.START_WORKERS`).
- **Ambron power:** every Ambron structure except the main base, relays and extractors must stand inside a finished Power Relay's field (`Defs.POWER_RADIUS`, like a Protoss pylon).
  - An unpowered building stops training, and an unpowered tower stops firing.
  - Void has no placement limit.
- **Towers:** both races get a defence tower in the shared `tower` slot: the Ambron Arc Tower (lightning) and the Void Slime Spire (slime). Their numbers are identical apart from the usual Void HP and cooldown multipliers.
- **Rocks:** the map generator places every rock model first and marks the cells under it solid, so what you see is what blocks. Ground units also keep their body clear of rock cells.

## Maps and elevation (Alex, 2026-11-14)

- **Maps are data.** Each map is one entry in `Maps.DEFS` with a theme in `Maps.THEMES`. Author player 1's half only:
  - plateaus and hazards are painted for player 1, then copied cell for cell onto the other half (`Terrain.symmetrize()`);
  - ramps and rocks are added together with their mirror;
  - bases are listed in pairs, and sites 0 and 1 are the two mains.

  Never paint both halves by hand, because lumpy edges won't match.
- **Elevation.** There are three levels (0, 1, 2), `Terrain.LEVEL_H` apart.
  - Cliff bands are two cells wide and block movement.
  - Ramps are the only way up.
  - Ground units can't see up a cliff, and ground shots fired uphill miss `Terrain.UPHILL_MISS` of the time.
  - Anything that draws at a ground position must add `world.height_at(p)`.
- **After a map change:**
  - run `--only=maps,terrain`, which checks mirror symmetry, 8 crystals and 2 slime piles per base, and that every base is reachable;
  - re-bake the previews with `--only=previews`;
  - run the balance harness's full games, so the bot can still play the map.

## Audio (Alex, 2026-11-14)

- **Licences.** Only CC0 audio, or CC-BY with the credit added. Alex's own tracks (made with Suno, like the match music `theme_pulse`) are allowed and credited to him. Every new file goes in `assets/CREDITS.md` and in `scripts/credits_panel.gd`.
- **Conversion.** Source packs are downloaded into their own folders outside the repo and converted with ffmpeg:
  - effects: mono 44.1 kHz Ogg, trimmed, loudness-matched, `<name>_N.ogg` for variants;
  - music: loudness-normalised stereo Ogg;
  - ambience: crossfaded loops.
- **Buses.** Effects play on the `Effects` bus and music on the `Music` bus. `Prefs` drives both from the Settings sliders.
- **Test runs are silent.** `--autotest` and `--balance` mute the master bus, and `Prefs` and `Profile` never write to `user://` during them.

## Art contract

`docs/ART_SPEC.md` is the contract for every model:
- metres, base at z = 0, front facing Blender -Y;
- a `team` material, which the game recolours;
- `glow*` materials for emission;
- triangle budgets.

Animated units carry an armature with `idle_loop`, `walk_loop` (or `fly_loop` for flyers) and `attack`. `Models` matches these by name and loops idle, walk and fly. A node named `turret` turns toward the unit's target.

## Controls (Alex, 2026-11-15)

- **Layout:** the minimap sits in the top-right corner. The quick buttons start in the bottom-left corner (BASE, BUILDINGS, ARMY, with ARMY at the bottom), where the left thumb rests.
- **Quick buttons are the player's:** Settings > Customize buttons adds, removes and moves them, saved in Prefs `quick_buttons` (`QuickButtons.layout()`). Never hard-code their position; `QuickButtonsEditor.zones()` must keep matching the HUD's fixed panels.
- **Box select:** hold on the ground, then slide. It selects every unit of yours inside, workers included.
- **Resting thumb (2026-11-15):** players hold the phone, so a thumb rests on the screen. `Commander._drop_resting` forgets a finger that has sat still for `LONG_PRESS` when another lands, and touches outside the safe area or in the quick buttons' gaps are ignored. Without this a resting thumb turned every slide into a pinch zoom and swallowed every tap, rally points included. The `grip` autotest guards it; keep it passing after any touch change.
- **Graphics:** the Settings slider's levels live in `Graphics.LEVELS`. Phones default to Balanced (60 fps cap). Keep a frame cap on phones: uncapped, an iPhone runs at 120 fps and gets hot.

## Tests

Run the autotest after gameplay changes, and the balance harness after stat or bot changes. Asset-only changes need just a re-import (`Godot --headless --path . --import`) and a look at the `models` section.

Prefs don't save during tests, but they do change for the rest of the run, so a test that changes one (graphics, quick buttons) must put it back.
