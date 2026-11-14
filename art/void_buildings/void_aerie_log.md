# void_aerie — Production Log

## Config
- Type: building (static), Void structure for Shardfall (Godot 4.7): Aerie (air production), 3x3 footprint
- Target: `assets/models/void_aerie.glb` (no Draco, JPEG textures packed) and `assets/icons/void_aerie.png` (256 px, transparent)
- Tier: balanced (4-12k triangles, one 1024 px atlas, 1-4 materials)
- Style: Void, grown not built (docs/ART_SPEC.md)
- Mode: auto (subagent brief of 2026-11-14)

## Reference
- Reference: `art/ref/void_style_reference.png` (glossy purple chitin plates with serrated bone rims, bone hooks, crimson flesh in the gaps, acid-green sacs) and the palette and contract in `docs/ART_SPEC.md`.
- Brief: 3x3, ~3.6 m: twisted chitin spire, bone hooks and perches near the top, membrane flaps, glowing sacs.
- Assumptions: footprint 3 m square, body inset ~0.15 m per side, creep mat within footprint + 0.3 m; target height 3.6 m; front is -Y.

## Intent
- Palette (from ART_SPEC): chitin #4A2A63 to #6B3C8A, highlight #8E5BB0; bone #D8C8A8 fading to #9C8A6A at the base; flesh #5E1A2A to #8A2C3C; glow #8CFF3A; creep #120A17 to #3A2350 with #4E1630 veins; `team` flat #C8C8C8.
- Silhouette: the thin, tall one: a three-lobed spire twisting up from a rooted base, four bone perch hooks near the top with crimson bat-wing flaps under them, green sacs on the spire.
- From the game camera: a narrow spire with hooks and the green sac cluster.

## Inventory
- flesh base mass with 9 chitin plates and 4 root legs
- twisted three-lobed chitin spire with bone ridges, 18 spiral plates
- 4 bone perch hooks with flesh membrane flaps (bat-wing patches), a crest horn
- 5 spire sacs and 2 base sacs (glow)
- team: 7 nodules round the spire
- creep mat 3.4 m square

## Pipeline
- Source: scripted, `art/void_buildings/build.py` (one script for all seven; run line in its docstring).
- Shapes: metaball or lathe flesh masses (noise-displaced, boolean-carved cavities, cut flat at z = 0, decimated to budget); solid curved chitin plates with hooked tips, draped onto the mass by a BVH pass so they never sink in; swept tapering bone horns, teeth and claws; ribbed flesh tubes; a flat creep mat (2.5 cm) with raised veins.
- Texturing: procedural Cycles shaders per part kind (chitin, flesh, bone, creep, glow, membrane), baked on a Smart UV unwrap to one 1024 px colour, roughness and normal atlas, packed in the GLB as JPEG (quality 90).
- Export: GLB, +Y up, Apply Modifiers, no cameras, lights or animations; body clamped to z >= 0; front -Y, origin at the ground centre. Review renders reimport the GLB into a clean scene (EEVEE).
- Result: 8703 triangles, 1.09 MB, 3.27 x 3.28 x 3.59 m (incl. creep); materials ['glow_aerie', 'team', 'void_aerie_skin']; objects ['void_aerie']; creep inside footprint + 0.3 m: True.

## Review rounds
- Renders per round in `art/void_buildings/review/<round>/`: three-quarter (512 px), game camera (55 degrees down, 25 m, 512 x 288), front, icon, and a sheet of all four; the lineup of all seven from the game camera at 40 m and 25 m. Reviewer: my own reading each round.
- Fast passes (review/fast, flat colours, no bake): shape iterations before r1 (plate draping, maw and tunnel carving, fit to footprint, triangle budget) and a check of the r2 shape changes.
- r1: silhouette and height on target (3.59 m); flap and base banding read as stripes.
- r2: softer, warped flesh bands (flaps and base); flaps still read as flat banners.
- r3: flaps reshaped into bat wings tapering from the hook tip to the spire, with a scalloped trailing edge (the first try folded the sheet and Solidify spiked it out to 2.6 m, which squeezed the fit; the scallop is now a fraction of each column, so it cannot fold).
- Lineup (r2, r3): all seven read as distinct silhouettes and as one family with the reference (purple plates, bone hooks, crimson flesh, green glow).

## Checkpoint
- Step: EXPORT done, icon written; waiting for Alex's review (2026-11-14). Not committed: the brief said not to run git.
