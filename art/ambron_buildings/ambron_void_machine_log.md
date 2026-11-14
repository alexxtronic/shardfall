# ambron_void_machine (Void Machine) — Production Log

## Config
- Type: building (static), Ambron extractor built over a 3 x 3 slime pile, for Shardfall (Godot 4.7, Mobile renderer)
- Target: `assets/models/ambron_void_machine.glb` (uncompressed GLB, +Y up, modifiers applied, no cameras, lights or animations) and `assets/icons/ambron_void_machine.png` (256 px, transparent)
- Size: 3 x 3 m footprint, built to 2.63 x 2.64 m, 2.52 m tall (spec 2.5 m); budget 4-12k triangles
- Style: Ambron (docs/ART_SPEC.md): chunky toy-like sci-fi, cream / gold / graphite, cyan glow, big soft bevels
- Mode: auto (built by an agent, scripted), reviewed by my own reading each round

## Reference
- Image: `art/ref/ambron_style_reference.png` (the Harvester drone turnaround)
- Brief: "Squat pump machine: graphite tank with cream armour plates, gold pipes, a translucent-looking tank window or glowing violet/cyan core showing slime being drawn up, four splayed stabiliser legs. It must cover a 3x3 pile."
- Borrowed from the drone: the drone's arm joints (graphite hinge with cyan caps) at the knees, its cream-over-graphite limb plating on the thighs, a small ear-disc lens pod as the front sensor
- Visual comparison: by eye against the reference sheet and against the other six in a lineup, each round

## Intent
- Palette (ART_SPEC): cream #EDE3CF (tiers #DDD0B6), gold #E0A33A (hazard/braces #B9771E), graphite #2B2F36 (slats #3E444E), cyan glow #5FE3FF, violet core glow #8A3CFF, black slime #17121F (gloss, rough 0.22); team accents light grey #C8CCD2 (recoloured in game)
- Materials: ambron_body, glow, glow_core (violet), team. `ambron_body` = one baked colour texture (1024 px) + one metallic-roughness texture (cream rough 0.45, gold rough 0.36 metal 0.25, graphite rough 0.52 metal 0.12); glow materials are emissive (strength 1.4-1.5, dark base colour so the hue holds); `team` is flat light grey
- Finishes: bevels on every block and rim (1-4 segments) with weighted normals; ambient occlusion baked into the colour for panel seams and ground contact (the Mobile renderer has no SSAO); no grime

## Inventory
- skirt over the pile: graphite lip (2.6 m across) and under-dome, four cream skirt plates with leg gaps on the diagonals, gold trim at the top
- tank: violet glowing core cylinder behind three cream armour plates, graphite rings top and bottom, gold seams between plates; the open front is the window, with two gold mullions and seven black slime blobs rising in the glow
- team bands on the two side plates
- pump head: cream dome, gold trim, graphite piston with a cyan ring, gold cap
- three gold pipes from the skirt up to the head (+X, +Y, -X), graphite collars where they leave the skirt
- four splayed legs on the diagonals: graphite hip, cream thigh with gold trim, graphite knee with cyan caps, graphite shin with a gold sleeve, graphite foot pad with a gold band
- front sensor: a small lens pod on the skirt facing -Y

## Source
- Method: scripted (Blender 5.2, `art/ambron_buildings/build.py`, function `build_void_machine`; shared kit: `base`, `lens_pod`, `ear_fin`, `joint`, `stud`)

## Pipeline
- Scene (headless, `-- ambron_void_machine`): 81 parts, each with bevel + weighted-normal modifiers, joined; hidden faces culled (faces on the ground and faces buried inside other parts, found by ray casts).
- Build: 9,409 triangles; 2.63 x 2.64 x 2.52 m; front -Y, origin at the centre of the footprint on the ground (lowest point z = 0).
- Texturing: Smart UV on the cream / gold / graphite faces; Cycles bake of flat colour (1 sample) and AO (160 samples, 1.1 m, with a ground plane); combined as colour x (0.48 + 0.52 AO^0.9); metallic-roughness from the nearest palette colour per texel. Both PNGs packed in the GLB (copies in `cache/`, gitignored).
- Export: `assets/models/ambron_void_machine.glb`, 1.20 MB; objects: `ambron_void_machine` (9,409 triangles, origin (0.0, 0.0, 0.0) in Blender Z-up, materials ambron_body, glow_core, team, glow).
- Materials are single-sided (backface culling on).
- Icon: EEVEE, 256 px, transparent film, three-quarter from the front-left and above, warm key + cool rim.
- Review renders: EEVEE 512 px, a three-quarter view and the game camera (55 degrees down, 25 m, 40 degree vertical FOV) on a ground plane with the footprint marked; `lineup_*.png` re-imports all seven GLBs.

## Review rounds
- Round 1 (review/round1/sheet_*.png, flat colours): squat pump on legs reads well and covers the pile's middle; the core clipped to pink (emission 3.0). 22k triangles.
- Round 2 (review/round2, flat): core #A25BFF -> #8A3CFF at emission 1.5 with a dark base, now violet. Joints, feet, slime blobs, skirt and armour plates simplified -> 10.6k. Foot trim ring reached 1.352 m (2 mm past the inset) -> replaced by a smaller gold band.
- Round 3 (review/round3, baked, first export): an intermediate cull pass removed the shins (fixed, see the Relay log); final cull -> 9.4k. The pile's corners stay visible between the feet, which shows it sits on a pile.
- Round 4 (review/round4, final): lighter AO, warmer gold. Nothing blocking.
- Reviewers: my own reading each round (no separate reviewer).

## Licences
All geometry and textures generated by the script. No third-party assets.

## Checkpoint
- Step: EXPORT done (2026-11-14). Not yet imported or checked in Godot; waiting for Alex's review.
