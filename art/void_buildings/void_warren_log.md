# void_warren — Production Log

## Config
- Type: building (static), Void structure for Shardfall (Godot 4.7): Beast Warren (factory), 3x3 footprint
- Target: `assets/models/void_warren.glb` (no Draco, JPEG textures packed) and `assets/icons/void_warren.png` (256 px, transparent)
- Tier: balanced (4-12k triangles, one 1024 px atlas, 1-4 materials)
- Style: Void, grown not built (docs/ART_SPEC.md)
- Mode: auto (subagent brief of 2026-11-14)

## Reference
- Reference: `art/ref/void_style_reference.png` (glossy purple chitin plates with serrated bone rims, bone hooks, crimson flesh in the gaps, acid-green sacs) and the palette and contract in `docs/ART_SPEC.md`.
- Brief: 3x3, ~3 m: low armoured burrow, ribbed tunnel mouth at the front, plated ridges with spines.
- Assumptions: footprint 3 m square, body inset ~0.15 m per side, creep mat within footprint + 0.3 m; target height 3.0 m; front is -Y.

## Intent
- Palette (from ART_SPEC): chitin #4A2A63 to #6B3C8A, highlight #8E5BB0; bone #D8C8A8 fading to #9C8A6A at the base; flesh #5E1A2A to #8A2C3C; glow #8CFF3A; creep #120A17 to #3A2350 with #4E1630 veins; `team` flat #C8C8C8.
- Silhouette: an armadillo-like mound, long front to back, a dark arched tunnel at the front ringed by four ribbed bone arches, a crest of tall spines down the ridge.
- From the game camera: the arched mouth and the spine crest.

## Inventory
- flesh mound (metaballs, carved tunnel), den glow inside the tunnel
- 4 ribbed bone arches round the tunnel mouth, 5 arch spikes
- 6 dorsal band plates, two flank rows of 5 plates per side, 5 rump plates
- 6 dorsal spines, 6 flank spines, 4 sacs, 4 claws
- team: 5 nodules over the tunnel
- creep mat 3.4 m square

## Pipeline
- Source: scripted, `art/void_buildings/build.py` (one script for all seven; run line in its docstring).
- Shapes: metaball or lathe flesh masses (noise-displaced, boolean-carved cavities, cut flat at z = 0, decimated to budget); solid curved chitin plates with hooked tips, draped onto the mass by a BVH pass so they never sink in; swept tapering bone horns, teeth and claws; ribbed flesh tubes; a flat creep mat (2.5 cm) with raised veins.
- Texturing: procedural Cycles shaders per part kind (chitin, flesh, bone, creep, glow, membrane), baked on a Smart UV unwrap to one 1024 px colour, roughness and normal atlas, packed in the GLB as JPEG (quality 90).
- Export: GLB, +Y up, Apply Modifiers, no cameras, lights or animations; body clamped to z >= 0; front -Y, origin at the ground centre. Review renders reimport the GLB into a clean scene (EEVEE).
- Result: 9498 triangles, 1.15 MB, 3.29 x 3.28 x 3.06 m (incl. creep); materials ['glow_warren', 'team', 'void_warren_skin']; objects ['void_warren']; creep inside footprint + 0.3 m: True.

## Review rounds
- Renders per round in `art/void_buildings/review/<round>/`: three-quarter (512 px), game camera (55 degrees down, 25 m, 512 x 288), front, icon, and a sheet of all four; the lineup of all seven from the game camera at 40 m and 25 m. Reviewer: my own reading each round.
- Fast passes (review/fast, flat colours, no bake): shape iterations before r1 (plate draping, maw and tunnel carving, fit to footprint, triangle budget) and a check of the r2 shape changes.
- r1: crashed on missing ray hits (guarded); squeezed in y by long rear spines (fixed); 2.68 m tall.
- r2: mound taller and shorter front to back (no fit squeeze), spines longer and more upright (~3 m); softer flesh bands.
- Lineup (r2, r3): all seven read as distinct silhouettes and as one family with the reference (purple plates, bone hooks, crimson flesh, green glow).

## Checkpoint
- Step: EXPORT done, icon written; waiting for Alex's review (2026-11-14). Not committed: the brief said not to run git.
