# Tripo unit pipeline

The core units are generated in Tripo from concept art. `build.py` turns each one into a game-ready GLB that follows `docs/ART_SPEC.md`.

## Steps

1. **Concept.** ChatGPT makes one image per unit, using `art/ref/*_style_reference.png` and an earlier concept as style references. Each image shows a three-quarter front view on a flat grey background, with the legs clearly separated. The images are saved to `concepts/shardfall_<id>.png`.
2. **Tripo.** Generate with H3.1 Best Quality, 2K PBR textures, triangle topology and a 10,000 polycount. Export as GLB with the file name `<id>`, then move it to `raw/<id>.glb`. The raw files are large, so they stay out of git.
3. **Check facing.** This renders four views (from −Y, +X, +Y and above) to `review/inspect/`. Set `yaw` in `UNITS` so the unit's front faces −Y.

   ```bash
   Blender --background --factory-startup --python-exit-code 1 --python art/tripo/build.py -- <id> --inspect
   ```

4. **Build.**

   ```bash
   Blender --background --factory-startup --python-exit-code 1 --python art/tripo/build.py -- <id,id,...> --round N
   ```

   The build does the following:
   - Imports the model. It clears glTF custom normals and welds UV-seam splits, which fixes faceted shading and makes decimation work.
   - Scales the model to the height `h` and decimates it to `tris`.
   - Splits it into `body`, `team` and `glow_*` by texture colour:
     - Ambron's cyan lights become the flat `team` material.
     - Void's pale bone becomes a textured `team` material. `bone_sat` widens this for peach-toned bone.
     - Void's acid green becomes `glow_acid`.
   - Rigs it (`hover`, `biped`, `legs` or `wings`) and keys `idle_loop`, `walk_loop` or `fly_loop`, and `attack`.
   - Bipeds with arms get an arm bone each from the `arms` capsules in `UNITS` (shoulder, hand, radius, in metres). The arms swing opposite the legs in `walk_loop`: Bulwark (its shield arm swings less), Spitter and Mauler. The Lancer holds its rifle in both hands, so its arms and rifle share one `carry` bone that bobs with each step. Hailfire and the walkers have no arms.
   - Exports `assets/models/<id>.glb` and `assets/icons/<id>.png`, plus a review sheet in `review/roundN/`.
5. **Reimport.** Run `Godot --headless --path . --import`, then check the `models` autotest section.

## Team colour in game

`Models.tint_team` multiplies the `team` albedo by the player colour and adds a little emission:
- Flat Ambron lights glow strongly.
- Textured Void bone keeps its detail and takes a faint glow.
