# void_hive — Production Log

## Config
- Type: building (static), Void structure for Shardfall (Godot 4.7): Hive (main base), 5x5 footprint
- Target: `assets/models/void_hive.glb` (no Draco, JPEG textures packed) and `assets/icons/void_hive.png` (256 px, transparent)
- Tier: balanced (4-12k triangles, one 1024 px atlas, 1-4 materials)
- Style: Void, grown not built (docs/ART_SPEC.md)
- Mode: auto (subagent brief of 2026-11-14)

## Reference
- Reference: `art/ref/void_style_reference.png` (glossy purple chitin plates with serrated bone rims, bone hooks, crimson flesh in the gaps, acid-green sacs) and the palette and contract in `docs/ART_SPEC.md`.
- Brief: 5x5, ~4.5 m: heart-mound with an open maw at the front, crown of bone spikes, green sacs, ribbed flesh between plates.
- Assumptions: footprint 5 m square, body inset ~0.15 m per side, creep mat within footprint + 0.3 m; target height 4.5 m; front is -Y.

## Intent
- Palette (from ART_SPEC): chitin #4A2A63 to #6B3C8A, highlight #8E5BB0; bone #D8C8A8 fading to #9C8A6A at the base; flesh #5E1A2A to #8A2C3C; glow #8CFF3A; creep #120A17 to #3A2350 with #4E1630 veins; `team` flat #C8C8C8.
- Silhouette: a tall lobed heart-mound, the biggest Void shape after the Abyss; a dark maw cut into the front, crown of curling bone spikes on top, four stubby chitin legs at the corners.
- Reads from the game camera as: the purple mound with the bone crown and the green-lit mouth.

## Inventory
- flesh mass (metaballs, carved maw cavity), five tiers of overlapping chitin plates (gaps left at the maw and the sacs)
- maw: rim teeth, brow plate, two cheek plates, two mandibles, green throat glow
- crown of 8 curling bone horns; three heart sacs and three sac clusters (glow)
- four corner legs with claws and knee spurs
- team: 9 crown nodules and 5 nodules round the maw
- creep mat 5.6 m square with veins

## Pipeline
- Source: scripted, `art/void_buildings/build.py` (one script for all seven; run line in its docstring).
- Shapes: metaball or lathe flesh masses (noise-displaced, boolean-carved cavities, cut flat at z = 0, decimated to budget); solid curved chitin plates with hooked tips, draped onto the mass by a BVH pass so they never sink in; swept tapering bone horns, teeth and claws; ribbed flesh tubes; a flat creep mat (2.5 cm) with raised veins.
- Texturing: procedural Cycles shaders per part kind (chitin, flesh, bone, creep, glow, membrane), baked on a Smart UV unwrap to one 1024 px colour, roughness and normal atlas, packed in the GLB as JPEG (quality 90).
- Export: GLB, +Y up, Apply Modifiers, no cameras, lights or animations; body clamped to z >= 0; front -Y, origin at the ground centre. Review renders reimport the GLB into a clean scene (EEVEE).
- Result: 11798 triangles, 1.25 MB, 5.20 x 5.17 x 4.52 m (incl. creep); materials ['glow_hive', 'team', 'void_hive_skin']; objects ['void_hive']; creep inside footprint + 0.3 m: True.

## Review rounds
- Renders per round in `art/void_buildings/review/<round>/`: three-quarter (512 px), game camera (55 degrees down, 25 m, 512 x 288), front, icon, and a sheet of all four; the lineup of all seven from the game camera at 40 m and 25 m. Reviewer: my own reading each round.
- Fast passes (review/fast, flat colours, no bake): shape iterations before r1 (plate draping, maw and tunnel carving, fit to footprint, triangle budget) and a check of the r2 shape changes.
- r1: plates now visible and draped (were sunk into the lobes), maw opens properly (negative metaballs only flattened the front, replaced with a boolean carve), mass recentred. Flesh texture banding read as woven stripes.
- r2: flesh bands made broad, warped and low-contrast; body clamped to z >= 0 (was -0.001).
- Lineup (r2, r3): all seven read as distinct silhouettes and as one family with the reference (purple plates, bone hooks, crimson flesh, green glow).

## Checkpoint
- Step: EXPORT done, icon written; waiting for Alex's review (2026-11-14). Not committed: the brief said not to run git.
