# ambron_relay (Power Relay) — Production Log

## Config
- Type: building (static), Ambron supply structure, for Shardfall (Godot 4.7, Mobile renderer)
- Target: `assets/models/ambron_relay.glb` (uncompressed GLB, +Y up, modifiers applied, no cameras, lights or animations) and `assets/icons/ambron_relay.png` (256 px, transparent)
- Size: 2 x 2 m footprint, built to 1.70 x 1.70 m, 2.50 m tall (spec 2-2.5 m); budget 4-12k triangles
- Style: Ambron (docs/ART_SPEC.md): chunky toy-like sci-fi, cream / gold / graphite, cyan glow, big soft bevels
- Mode: auto (built by an agent, scripted), reviewed by my own reading each round

## Reference
- Image: `art/ref/ambron_style_reference.png` (the Harvester drone turnaround)
- Brief: "A slim cream/gold obelisk on a graphite base with a floating cyan energy crystal at the top (separate object, so it can bob) and glowing seams."
- Borrowed from the drone: cyan lenses as small light studs, gold claws like the drone's gold arm plates, the shared plinth
- Visual comparison: by eye against the reference sheet and against the other six in a lineup, each round

## Intent
- Palette (ART_SPEC): cream #EDE3CF (tiers #DDD0B6), gold #E0A33A (hazard/braces #B9771E), graphite #2B2F36 (slats #3E444E), cyan glow #5FE3FF; team accents light grey #C8CCD2 (recoloured in game)
- Materials: ambron_body, glow, team. `ambron_body` = one baked colour texture (512 px) + one metallic-roughness texture (cream rough 0.45, gold rough 0.36 metal 0.25, graphite rough 0.52 metal 0.12); glow materials are emissive (strength 1.4-1.5, dark base colour so the hue holds); `team` is flat light grey
- Finishes: bevels on every block and rim (1-4 segments) with weighted normals; ambient occlusion baked into the colour for panel seams and ground contact (the Mobile renderer has no SSAO); no grime

## Inventory
- graphite plinth (1.7 m), gold lip, cream tier; cyan studs on the chamfered corners
- four small graphite posts with cyan tips on the tier corners
- cream tapered square obelisk (0.60 -> 0.38 m), heavily bevelled; gold collar at the foot, flared gold collar at the top, team band at mid height
- eight cyan seams, two down the middle of each face, tilted with the taper
- graphite cap and four gold claws reaching up round the crystal
- floating cyan hexagonal crystal (separate object `ambron_relay_crystal`, faceted, 0.42 m wide, 0.51 m tall, 6 cm above the cap, tip at 2.50 m)

## Source
- Method: scripted (Blender 5.2, `art/ambron_buildings/build.py`, function `build_relay`; shared kit: `base`, `lens_pod`, `ear_fin`, `joint`, `stud`)

## Pipeline
- Scene (headless, `-- ambron_relay`): 33 parts, each with bevel + weighted-normal modifiers, joined; hidden faces culled (faces on the ground and faces buried inside other parts, found by ray casts).
- Build: 2,934 triangles; 1.70 x 1.70 x 2.50 m; front -Y, origin at the centre of the footprint on the ground (lowest point z = 0).
- Texturing: Smart UV on the cream / gold / graphite faces; Cycles bake of flat colour (1 sample) and AO (160 samples, 1.1 m, with a ground plane); combined as colour x (0.48 + 0.52 AO^0.9); metallic-roughness from the nearest palette colour per texel. Both PNGs packed in the GLB (copies in `cache/`, gitignored).
- Export: `assets/models/ambron_relay.glb`, 286 KB; objects: `ambron_relay` (2,910 triangles, origin (0.0, 0.0, 0.0) in Blender Z-up, materials ambron_body, glow, team); `ambron_relay_crystal` (24 triangles, origin (0.0, 0.0, 2.245) in Blender Z-up, materials glow).
- Materials are single-sided (backface culling on).
- Floating part: `ambron_relay_crystal` is its own node beside `ambron_relay`, origin at its own centre so the game can bob and spin it in place; it has no animation in the GLB.
- Icon: EEVEE, 256 px, transparent film, three-quarter from the front-left and above, warm key + cool rim.
- Review renders: EEVEE 512 px, a three-quarter view and the game camera (55 degrees down, 25 m, 40 degree vertical FOV) on a ground plane with the footprint marked; `lineup_*.png` re-imports all seven GLBs.

## Review rounds
- Round 1 (review/round1/sheet_*.png, flat colours): reads as a supply pylon; the crystal was too small to pick out from the game camera.
- Round 2 (review/round2, flat): crystal enlarged (radius 0.17 -> 0.21 m, 0.42 -> 0.51 m tall), claws widened to match; glow saturated (emission 1.4, dark base).
- Round 3 (review/round3, baked, first export): an intermediate pass of the hidden-face cull deleted the shaft's flat faces (a selection flush also took faces whose corners were shared with culled faces); fixed by deleting the culled faces directly, checked in the flat and baked renders.
- Round 4 (review/round4, final): lighter AO, warmer gold. The crystal's tip was at 2.56 m, over the spec's 2-2.5 m: obelisk shortened 6 cm and the cap, claws and crystal moved down (tip 2.50 m), rebuilt and re-rendered. Nothing blocking.
- Reviewers: my own reading each round (no separate reviewer).

## Licences
All geometry and textures generated by the script. No third-party assets.

## Checkpoint
- Step: EXPORT done (2026-11-14). Not yet imported or checked in Godot; waiting for Alex's review.
