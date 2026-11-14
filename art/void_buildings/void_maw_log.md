# void_maw — Production Log

## Config
- Type: building (static), Void structure for Shardfall (Godot 4.7): Maw (extractor), 3x3 footprint
- Target: `assets/models/void_maw.glb` (no Draco, JPEG textures packed) and `assets/icons/void_maw.png` (256 px, transparent)
- Tier: balanced (4-12k triangles, one 1024 px atlas, 1-4 materials)
- Style: Void, grown not built (docs/ART_SPEC.md)
- Mode: auto (subagent brief of 2026-11-14)

## Reference
- Reference: `art/ref/void_style_reference.png` (glossy purple chitin plates with serrated bone rims, bone hooks, crimson flesh in the gaps, acid-green sacs) and the palette and contract in `docs/ART_SPEC.md`.
- Brief: 3x3, ~2.5 m: lamprey ring mouth of bone teeth on a chitin collar, tendrils, green throat; must cover a 3x3 slime pile.
- Assumptions: footprint 3 m square, body inset ~0.15 m per side, creep mat within footprint + 0.3 m; target height 2.5 m; front is -Y.

## Intent
- Palette (from ART_SPEC): chitin #4A2A63 to #6B3C8A, highlight #8E5BB0; bone #D8C8A8 fading to #9C8A6A at the base; flesh #5E1A2A to #8A2C3C; glow #8CFF3A; creep #120A17 to #3A2350 with #4E1630 veins; `team` flat #C8C8C8.
- Silhouette: a squat armoured collar (squared at the base to cover the pile) opening upward into a lamprey mouth: three rings of inward teeth, tall hooks curling over the lip, a green throat deep inside.
- From above the camera looks straight into the ring of teeth and the green throat.

## Inventory
- flesh collar (lathe, squared base, slight backward lean) with three tiers of chitin plates; the body fills +-1.37 m and the tendrils and creep mat (+-1.72 m) cover the rest of a 3x3 pile
- 3 rings of bone teeth (16 / 12 / 9) and 7 tall bone hooks over the lip
- green throat glow and 3 sacs on the collar
- 4 corner feeding tendrils sprawling over the pile's corners, 4 shorter side feelers
- team: 7 nodules round the lip
- creep mat 3.4 m square

## Pipeline
- Source: scripted, `art/void_buildings/build.py` (one script for all seven; run line in its docstring).
- Shapes: metaball or lathe flesh masses (noise-displaced, boolean-carved cavities, cut flat at z = 0, decimated to budget); solid curved chitin plates with hooked tips, draped onto the mass by a BVH pass so they never sink in; swept tapering bone horns, teeth and claws; ribbed flesh tubes; a flat creep mat (2.5 cm) with raised veins.
- Texturing: procedural Cycles shaders per part kind (chitin, flesh, bone, creep, glow, membrane), baked on a Smart UV unwrap to one 1024 px colour, roughness and normal atlas, packed in the GLB as JPEG (quality 90).
- Export: GLB, +Y up, Apply Modifiers, no cameras, lights or animations; body clamped to z >= 0; front -Y, origin at the ground centre. Review renders reimport the GLB into a clean scene (EEVEE).
- Result: 10422 triangles, 1.19 MB, 3.30 x 3.30 x 2.46 m (incl. creep); materials ['glow_maw', 'team', 'void_maw_skin']; objects ['void_maw']; creep inside footprint + 0.3 m: True.

## Review rounds
- Renders per round in `art/void_buildings/review/<round>/`: three-quarter (512 px), game camera (55 degrees down, 25 m, 512 x 288), front, icon, and a sheet of all four; the lineup of all seven from the game camera at 40 m and 25 m. Reviewer: my own reading each round.
- Fast passes (review/fast, flat colours, no bake): shape iterations before r1 (plate draping, maw and tunnel carving, fit to footprint, triangle budget) and a check of the r2 shape changes.
- r1: reads as a mouth from the game camera; 2.1 m tall (short), tendrils hung down like straps.
- r2: collar 16 % taller, hooks longer and less curled (now ~2.5 m); tendrils taper and sprawl out over the corners, tips curling; softer flesh bands.
- Lineup (r2, r3): all seven read as distinct silhouettes and as one family with the reference (purple plates, bone hooks, crimson flesh, green glow).

## Checkpoint
- Step: EXPORT done, icon written; waiting for Alex's review (2026-11-14). Not committed: the brief said not to run git.
