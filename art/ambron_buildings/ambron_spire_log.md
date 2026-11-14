# ambron_spire (Apex Spire) — Production Log

## Config
- Type: building (static), Ambron special late-game building (builds the Sovereign), for Shardfall (Godot 4.7, Mobile renderer)
- Target: `assets/models/ambron_spire.glb` (uncompressed GLB, +Y up, modifiers applied, no cameras, lights or animations) and `assets/icons/ambron_spire.png` (256 px, transparent)
- Size: 4 x 4 m footprint, built to 3.70 x 3.70 m, 5.00 m tall (spec 4-5 m); budget 4-12k triangles
- Style: Ambron (docs/ART_SPEC.md): chunky toy-like sci-fi, cream / gold / graphite, cyan glow, big soft bevels
- Mode: auto (built by an agent, scripted), reviewed by my own reading each round

## Reference
- Image: `art/ref/ambron_style_reference.png` (the Harvester drone turnaround)
- Brief: "A tall elegant spire with stacked rings, a floating gold halo ring and a bright cyan core: it should look expensive."
- Borrowed from the drone: lens pods on the drum, the cyan crystal and lens language, gold over cream; the halo floats like the Relay crystal
- Visual comparison: by eye against the reference sheet and against the other six in a lineup, each round

## Intent
- Palette (ART_SPEC): cream #EDE3CF (tiers #DDD0B6), gold #E0A33A (hazard/braces #B9771E), graphite #2B2F36 (slats #3E444E), cyan glow #5FE3FF; team accents light grey #C8CCD2 (recoloured in game)
- Materials: ambron_body, glow, team. `ambron_body` = one baked colour texture (1024 px) + one metallic-roughness texture (cream rough 0.45, gold rough 0.36 metal 0.25, graphite rough 0.52 metal 0.12); glow materials are emissive (strength 1.4-1.5, dark base colour so the hue holds); `team` is flat light grey
- Finishes: bevels on every block and rim (1-4 segments) with weighted normals; ambient occlusion baked into the colour for panel seams and ground contact (the Mobile renderer has no SSAO); no grime

## Inventory
- graphite octagon plinth (3.7 m), gold lip, cream tier, cyan corner studs
- cream drum with gold trim and a cyan light ring round its top
- cream lower spire with four gilded strips; graphite collars with gold trims
- bright cyan faceted core in a cage of four gold ribs (2.0-3.3 m)
- three stacked cream segments with gold rings between, gold tip, cyan point at 5.0 m
- front door (-Y) with gold jambs and a cyan strip
- four thick cream buttress fins on the diagonals: gold edge tubes, team stripes along the edges, cyan lights at their feet
- three small lens pods on the drum (sides and back)
- floating gold halo (separate object `ambron_spire_halo`, 1.8 m across) with a cyan inner ring and four gold nubs, centred at 4.18 m round the upper spire

## Source
- Method: scripted (Blender 5.2, `art/ambron_buildings/build.py`, function `build_spire`; shared kit: `base`, `lens_pod`, `ear_fin`, `joint`, `stud`)

## Pipeline
- Scene (headless, `-- ambron_spire`): 69 parts, each with bevel + weighted-normal modifiers, joined; hidden faces culled (faces on the ground and faces buried inside other parts, found by ray casts).
- Build: 10,830 triangles; 3.70 x 3.70 x 5.00 m; front -Y, origin at the centre of the footprint on the ground (lowest point z = 0).
- Texturing: Smart UV on the cream / gold / graphite faces; Cycles bake of flat colour (1 sample) and AO (160 samples, 1.1 m, with a ground plane); combined as colour x (0.48 + 0.52 AO^0.9); metallic-roughness from the nearest palette colour per texel. Both PNGs packed in the GLB (copies in `cache/`, gitignored).
- Export: `assets/models/ambron_spire.glb`, 1.27 MB; objects: `ambron_spire` (9,694 triangles, origin (0.0, 0.0, 0.0) in Blender Z-up, materials ambron_body, glow, team); `ambron_spire_halo` (1,136 triangles, origin (0.0, 0.0, 4.18) in Blender Z-up, materials ambron_body, glow).
- Materials are single-sided (backface culling on).
- Floating part: `ambron_spire_halo` is its own node beside `ambron_spire`, origin at its own centre so the game can bob and spin it in place; it has no animation in the GLB.
- Icon: EEVEE, 256 px, transparent film, three-quarter from the front-left and above, warm key + cool rim.
- Review renders: EEVEE 512 px, a three-quarter view and the game camera (55 degrees down, 25 m, 40 degree vertical FOV) on a ground plane with the footprint marked; `lineup_*.png` re-imports all seven GLBs.

## Review rounds
- Round 1 (review/round1/sheet_*.png, flat colours): the halo and core read, but the base was thin and plain (0.2 m fins vanish from above) and it did not yet look expensive. 18.4k triangles.
- Round 2 (review/round2, flat): fins 0.2 -> 0.3 m with thicker gold edges, gilded strips up the lower spire, bigger core and cage, cyan ring on the drum; segments cut -> 11.2k.
- Round 3 (review/round3, baked, first export, lineup): the team inlay on each fin was an irregular quad that looked like a glitch.
- Round 4 (review/round4, final): team inlay replaced by a band running parallel to the gold edge; lighter AO, warmer gold. Nothing blocking.
- Reviewers: my own reading each round (no separate reviewer).

## Licences
All geometry and textures generated by the script. No third-party assets.

## Checkpoint
- Step: EXPORT done (2026-11-14). Not yet imported or checked in Godot; waiting for Alex's review.
