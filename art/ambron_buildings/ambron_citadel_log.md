# ambron_citadel (Citadel) — Production Log

## Config
- Type: building (static), Ambron main base (drop-off, trains Harvesters), for Shardfall (Godot 4.7, Mobile renderer)
- Target: `assets/models/ambron_citadel.glb` (uncompressed GLB, +Y up, modifiers applied, no cameras, lights or animations) and `assets/icons/ambron_citadel.png` (256 px, transparent)
- Size: 5 x 5 m footprint, built to 4.70 x 4.70 m, 4.54 m tall (spec 4-5 m); budget 4-12k triangles
- Style: Ambron (docs/ART_SPEC.md): chunky toy-like sci-fi, cream / gold / graphite, cyan glow, big soft bevels
- Mode: auto (built by an agent, scripted), reviewed by my own reading each round

## Reference
- Image: `art/ref/ambron_style_reference.png` (the Harvester drone turnaround)
- Brief: "A grand rounded command hub: domed cream core on a graphite octagonal plinth, gold trim rings, a ring of cyan light, a docking bay mouth facing -Y where harvester drones drop crystals, antenna fins like the drone's ear fins. Must read as the most important building."
- Borrowed from the drone: the drone's two tall gold ear fins with cyan inner strips (on top, either side of the beacon), its round ear discs as two big lens pods on the flanks, gold plates on a cream shell (the dome petals), cyan lens dome (the beacon, like the drone's under-lens)
- Visual comparison: by eye against the reference sheet and against the other six in a lineup, each round

## Intent
- Palette (ART_SPEC): cream #EDE3CF (tiers #DDD0B6), gold #E0A33A (hazard/braces #B9771E), graphite #2B2F36 (slats #3E444E), cyan glow #5FE3FF; team accents light grey #C8CCD2 (recoloured in game)
- Materials: ambron_body, glow, team. `ambron_body` = one baked colour texture (1024 px) + one metallic-roughness texture (cream rough 0.45, gold rough 0.36 metal 0.25, graphite rough 0.52 metal 0.12); glow materials are emissive (strength 1.4-1.5, dark base colour so the hue holds); `team` is flat light grey
- Finishes: bevels on every block and rim (1-4 segments) with weighted normals; ambient occlusion baked into the colour for panel seams and ground contact (the Mobile renderer has no SSAO); no grime

## Inventory
- graphite octagon plinth (4.7 m), gold lip, cream tier; cyan studs on the four chamfered corners
- round core: graphite foot ring (open at the bay), cream wall, graphite channel holding the cyan light ring between two gold trim rings
- cream dome with four gold petals on the diagonals; beacon on top: graphite collar, gold trim, cyan lens dome
- two gold ear fins with cyan inner strips on graphite sockets, rising to 4.54 m
- two large lens pods on the flanks (cream shell, gold rim, graphite ring, cyan lens)
- docking bay at -Y: cream hood (two jambs and a lintel), graphite-lined mouth 1.4 m wide with a cyan intake strip and a gold hopper at the back, gold frame, cyan strip over the mouth, team stripes on the jambs; a graphite ramp with gold rails runs down the plinth into it
- rear module (+Y) with a gold band and graphite louvres
- four corner pylons: graphite post, team band, gold band, cream cap, cyan lens

## Source
- Method: scripted (Blender 5.2, `art/ambron_buildings/build.py`, function `build_citadel`; shared kit: `base`, `lens_pod`, `ear_fin`, `joint`, `stud`)

## Pipeline
- Scene (headless, `-- ambron_citadel`): 80 parts, each with bevel + weighted-normal modifiers, joined; hidden faces culled (faces on the ground and faces buried inside other parts, found by ray casts).
- Build: 11,092 triangles; 4.70 x 4.70 x 4.54 m; front -Y, origin at the centre of the footprint on the ground (lowest point z = 0).
- Texturing: Smart UV on the cream / gold / graphite faces; Cycles bake of flat colour (1 sample) and AO (160 samples, 1.1 m, with a ground plane); combined as colour x (0.48 + 0.52 AO^0.9); metallic-roughness from the nearest palette colour per texel. Both PNGs packed in the GLB (copies in `cache/`, gitignored).
- Export: `assets/models/ambron_citadel.glb`, 1.26 MB; objects: `ambron_citadel` (11,092 triangles, origin (0.0, 0.0, 0.0) in Blender Z-up, materials ambron_body, glow, team).
- Materials are single-sided (backface culling on).
- Icon: EEVEE, 256 px, transparent film, three-quarter from the front-left and above, warm key + cool rim.
- Review renders: EEVEE 512 px, a three-quarter view and the game camera (55 degrees down, 25 m, 40 degree vertical FOV) on a ground plane with the footprint marked; `lineup_*.png` re-imports all seven GLBs.

## Review rounds
- Before the first render: the bay mouth was only 0.36 m deep with the core's foot ring crossing its floor, so the foot ring and its trim became open sectors at the bay and a graphite back wall sits just in front of the core wall.
- Round 1 (review/round1/sheet_*.png, flat colours): reads as the main base and as the drone's family (fins, ear pods, beacon). Glow clipped to a pale cyan (emission 3.0 too strong under the Standard view). 23.5k triangles, double the budget.
- Round 2 (review/round2, flat): glow at 1.4 with a dark base colour, now saturated cyan. Cut segments on lens pods, toruses, petals, pylons and bevels (default box bevel 3 -> 2 segments, kept 3 on the hood and rear) -> 11.8k.
- Round 3 (review/round3, baked, first export, lineup): hidden-face cull added (faces on the ground and faces buried inside other parts) -> 11.1k. Baked AO gives soft seams and contact shading; gold slightly brown from AO stacked on render shading.
- Round 4 (review/round4, final): lighter AO curve (0.48 + 0.52 AO), gold metallic 0.3 -> 0.25. Largest and tallest in the lineup, the cyan beacon and ring read from the game camera; nothing blocking in my reading.
- Reviewers: my own reading each round (no separate reviewer).

## Licences
All geometry and textures generated by the script. No third-party assets.

## Checkpoint
- Step: EXPORT done (2026-11-14). Not yet imported or checked in Godot; waiting for Alex's review.
