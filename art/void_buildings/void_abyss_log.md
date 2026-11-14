# void_abyss — Production Log

## Config
- Type: building (static), Void structure for Shardfall (Godot 4.7): Abyssal Lair (tech/elite), 4x4 footprint
- Target: `assets/models/void_abyss.glb` (no Draco, JPEG textures packed) and `assets/icons/void_abyss.png` (256 px, transparent)
- Tier: balanced (4-12k triangles, one 1024 px atlas, 1-4 materials)
- Style: Void, grown not built (docs/ART_SPEC.md)
- Mode: auto (subagent brief of 2026-11-14)

## Reference
- Reference: `art/ref/void_style_reference.png` (glossy purple chitin plates with serrated bone rims, bone hooks, crimson flesh in the gaps, acid-green sacs) and the palette and contract in `docs/ART_SPEC.md`.
- Brief: 4x4, ~5 m: dark monolith of plates, giant tusks, deep glowing green rift; ominous.
- Assumptions: footprint 4 m square, body inset ~0.15 m per side, creep mat within footprint + 0.3 m; target height 5.0 m; front is -Y.

## Intent
- Palette (from ART_SPEC): chitin #4A2A63 to #6B3C8A, highlight #8E5BB0; bone #D8C8A8 fading to #9C8A6A at the base; flesh #5E1A2A to #8A2C3C; glow #8CFF3A; creep #120A17 to #3A2350 with #4E1630 veins; `team` flat #C8C8C8.
- Silhouette: the tallest and darkest Void shape: twin plated columns split front to back by a narrow glowing rift, a split crown of horns, two huge front tusks and two back tusks.
- Darker chitin than the rest of the family (#2E1A40 to #4A2A63, highlight #734398) so it reads as the ominous one.

## Inventory
- flesh mass (two metaball columns, rift and crown split carved by booleans)
- rift glow (two thin slabs set deep in the slot) and 3 rift sacs at its foot
- five tiers of hooked chitin plates per side and a skirt of 5 per side
- 3 crown horns per side, 2 front tusks (3 m), 2 back tusks (2.2 m)
- 3 flesh strands across the rift
- team: 12 nodules round the foot (6 front, 6 back)
- creep mat 4.4 m square

## Pipeline
- Source: scripted, `art/void_buildings/build.py` (one script for all seven; run line in its docstring).
- Shapes: metaball or lathe flesh masses (noise-displaced, boolean-carved cavities, cut flat at z = 0, decimated to budget); solid curved chitin plates with hooked tips, draped onto the mass by a BVH pass so they never sink in; swept tapering bone horns, teeth and claws; ribbed flesh tubes; a flat creep mat (2.5 cm) with raised veins.
- Texturing: procedural Cycles shaders per part kind (chitin, flesh, bone, creep, glow, membrane), baked on a Smart UV unwrap to one 1024 px colour, roughness and normal atlas, packed in the GLB as JPEG (quality 90).
- Export: GLB, +Y up, Apply Modifiers, no cameras, lights or animations; body clamped to z >= 0; front -Y, origin at the ground centre. Review renders reimport the GLB into a clean scene (EEVEE).
- Result: 11497 triangles, 1.26 MB, 4.27 x 4.28 x 4.88 m (incl. creep); materials ['glow_abyss', 'team', 'void_abyss_skin']; objects ['void_abyss']; creep inside footprint + 0.3 m: True.

## Review rounds
- Renders per round in `art/void_buildings/review/<round>/`: three-quarter (512 px), game camera (55 degrees down, 25 m, 512 x 288), front, icon, and a sheet of all four; the lineup of all seven from the game camera at 40 m and 25 m. Reviewer: my own reading each round.
- Fast passes (review/fast, flat colours, no bake): shape iterations before r1 (plate draping, maw and tunnel carving, fit to footprint, triangle budget) and a check of the r2 shape changes.
- r1: reads as the ominous one; rift glow wide from the three-quarter view.
- r2: rift glow slabs narrower and set deeper in the slot; softer flesh bands.
- Lineup (r2, r3): all seven read as distinct silhouettes and as one family with the reference (purple plates, bone hooks, crimson flesh, green glow).

## Checkpoint
- Step: EXPORT done, icon written; waiting for Alex's review (2026-11-14). Not committed: the brief said not to run git.
