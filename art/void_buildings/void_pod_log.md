# void_pod — Production Log

## Config
- Type: building (static), Void structure for Shardfall (Godot 4.7): Brood Pod (supply), 2x2 footprint
- Target: `assets/models/void_pod.glb` (no Draco, JPEG textures packed) and `assets/icons/void_pod.png` (256 px, transparent)
- Tier: balanced (4-12k triangles, one 1024 px atlas, 1-4 materials)
- Style: Void, grown not built (docs/ART_SPEC.md)
- Mode: auto (subagent brief of 2026-11-14)

## Reference
- Reference: `art/ref/void_style_reference.png` (glossy purple chitin plates with serrated bone rims, bone hooks, crimson flesh in the gaps, acid-green sacs) and the palette and contract in `docs/ART_SPEC.md`.
- Brief: 2x2, ~2.2 m: translucent egg cluster, glowing core as a separate object named `glow_core`, bone ribs cradling it.
- Assumptions: footprint 2 m square, body inset ~0.15 m per side, creep mat within footprint + 0.3 m; target height 2.2 m; front is -Y.

## Intent
- Palette (from ART_SPEC): chitin #4A2A63 to #6B3C8A, highlight #8E5BB0; bone #D8C8A8 fading to #9C8A6A at the base; flesh #5E1A2A to #8A2C3C; glow #8CFF3A; creep #120A17 to #3A2350 with #4E1630 veins; `team` flat #C8C8C8.
- Silhouette: one tall egg in a cage of five bone ribs, four small eggs round its foot, in a cup of chitin petals; the smallest Void building.
- The egg shells are alpha-blended (0.6) so the green cores show through; the cores are one separate object so the game can pulse or scale them.

## Inventory
- flesh base mass with 8 chitin petal plates
- 5 eggs (material `void_pod_membrane`, alpha blend), each with a glowing core inside
- ribbed flesh cup ring round the big egg's foot
- 5 bone cage ribs curling over the top
- team: 6 nodules on the cup
- creep mat 2.6 m square
- separate object `glow_core` (all 5 cores, material `glow_core`), parented to `void_pod`, origin at the big core's centre

## Pipeline
- Source: scripted, `art/void_buildings/build.py` (one script for all seven; run line in its docstring).
- Shapes: metaball or lathe flesh masses (noise-displaced, boolean-carved cavities, cut flat at z = 0, decimated to budget); solid curved chitin plates with hooked tips, draped onto the mass by a BVH pass so they never sink in; swept tapering bone horns, teeth and claws; ribbed flesh tubes; a flat creep mat (2.5 cm) with raised veins.
- Texturing: procedural Cycles shaders per part kind (chitin, flesh, bone, creep, glow, membrane), baked on a Smart UV unwrap to one 1024 px colour, roughness and normal atlas, packed in the GLB as JPEG (quality 90).
- Export: GLB, +Y up, Apply Modifiers, no cameras, lights or animations; body clamped to z >= 0; front -Y, origin at the ground centre. Review renders reimport the GLB into a clean scene (EEVEE).
- Result: 5586 triangles, 0.82 MB, 2.32 x 2.32 x 2.20 m (incl. creep); materials ['glow_core', 'team', 'void_pod_membrane', 'void_pod_skin']; objects ['void_pod', 'glow_core']; creep inside footprint + 0.3 m: True.

## Review rounds
- Renders per round in `art/void_buildings/review/<round>/`: three-quarter (512 px), game camera (55 degrees down, 25 m, 512 x 288), front, icon, and a sheet of all four; the lineup of all seven from the game camera at 40 m and 25 m. Reviewer: my own reading each round.
- Fast passes (review/fast, flat colours, no bake): shape iterations before r1 (plate draping, maw and tunnel carving, fit to footprint, triangle budget) and a check of the r2 shape changes.
- r0: pipeline test on this building only (bake, export, reimport, icon).
- r1: full build; read well, a little short (2.06 m).
- r2: big egg and cage ribs raised to ~2.2 m; core pivot follows the big core; softer flesh bands.
- r3: egg membrane no longer emissive (only `glow*` materials emit, per the spec); eggs still read pale and translucent with the cores showing through.
- Lineup (r2, r3): all seven read as distinct silhouettes and as one family with the reference (purple plates, bone hooks, crimson flesh, green glow).

## Checkpoint
- Step: EXPORT done, icon written; waiting for Alex's review (2026-11-14). Not committed: the brief said not to run git.
