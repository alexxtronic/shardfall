# ambron_scorcher — Production Log

## Config
- Type: ground vehicle (flame tank), Ambron, game asset for Shardfall (Godot 4.7, Mobile renderer)
- Target: assets/models/ambron_scorcher.glb (uncompressed), assets/icons/ambron_scorcher.png
- Budget: 4-8k triangles, radius 0.9, about 2.1 m long and 1.3 m tall (docs/ART_SPEC.md)
- Style: Ambron, chunky toy-like sci-fi in the family of the harvester drone
- Mode: auto (brief delegated 2026-11-14); scripted build, review renders by EEVEE in Blender 5.2

## Reference
- art/ref/ambron_style_reference.png (Alex's Tripo harvester drone turnaround) and docs/ART_SPEC.md
- Brief: "flame tank: low hover-tank or short tracks, rounded hull, a squat turret with twin flamer nozzles glowing orange-hot at the tips, fuel tanks on the back"
- Read from the drone: rounded cream shell plates over graphite mechanics, gold trim and fins, cyan lenses
  set in graphite bezels, no grime, soft bevels; the camera looks down at 55 degrees from 18-45 m, so
  colour blocking and silhouette matter more than detail.

## Intent
- Palette (ART_SPEC Ambron look): cream #EDE3CF (shade #D6C9AE), gold #E0A33A (dark #B9771E), graphite
  #2B2F36 (light #474D57), near-black #17191E for track and tube interiors; `team` light grey #C9CDD3;
  `glow_cyan` #5FE3FF with emission 2.2; `glow_fire` base #FF6A1F, emission #FF4A0C at 2.2 (orange-hot metal)
- Materials: `ambron_body` (a 64 px palette texture, one 16 px cell per colour, UVs at the cell centres,
  nearest filtering, plus a matching metallic/roughness texture: roughness 0.38-0.5, metallic 0-0.3 on
  gold and graphite), `team`, `glow_cyan`, `glow_fire`. Principled BSDF only; all single-sided.
- Family cues from the drone: the graphite face plate with a cyan pill lens, the big side discs (cream rim,
  graphite bezel, domed cyan lens), the two gold "ear" fins, big soft bevels (3 segments) everywhere.

## Inventory
- Two hover sponsons: graphite pods, cream armour plates on top, a gold nose cap, a gold trim line, a cyan
  vent strip on the outer side, a drone side disc toward the rear, two hover pads underneath (graphite ring,
  cyan glow disc; the pads are the lowest point)
- Centre hull: cream prism with a sloped glacis carrying the drone face (graphite plate, cyan pill), gold
  edge strips on the glacis, a graphite belly, two cyan exhaust lenses at the back
- Rear deck: two gold capsule fuel tanks on a graphite saddle, graphite straps, a glowing orange fuel window
  on each tank's upper back
- Turret (separate object): graphite ring, squat cream body with gold cheek plates, two `team` racing stripes
  front to back, the drone face on its front slope, a gold hatch ring with a cream dome, the two gold ear fins
- Twin flamer nozzles: graphite barrels, gold collars and rings, flared graphite nozzles ending in
  `glow_fire` tips
- `team`: a band across each sponson's armour, the two turret stripes

## Pipeline
- Build (art/ambron_vehicles/build.py, scripted bmesh): rounded boxes (bevelled, 2-3 segments), YZ-profile
  prisms for hulls and turrets, lathed parts for nozzles, wheels, lenses, ducts and barrels; each part UV'd
  onto its palette cell, parts joined per object, smooth shading with edges over 42 degrees kept sharp, a
  weighted-normal (face area) pass applied.
- Settle: lowest point to z = 0 and the bounding box centred in X and Y (baked into the hull mesh, so its
  origin is the ground centre).
- Result: 7,544 triangles (hull 5,044, turret 2,500); 1.666 x 2.096 x 1.281 m (X x Y x Z); front -Y.
- Objects: `hull` (origin 0, 0, 0); `turret` (origin on its turning axis, at (0, -0.007, 0.62)); Empty `muzzle`, a child of `turret`, local (0, -1, 0.16) = world (0, -1.007, 0.78).
- Export: GLB, selection only, modifiers applied, +Y up, no cameras, lights or animations; glow materials
  carry KHR_materials_emissive_strength; 240 KB.
- Icon: assets/icons/ambron_scorcher.png, 256 px, transparent, EEVEE, three-quarter from the front-left (camera at
  -X, -Y) 24 degrees up, warm key, cool rim, framed tight.

## Review rounds
- Renders per round in art/ambron_vehicles/review/round<N>/: front three-quarter, back three-quarter, the
  game camera (55 degrees down from 25 m, 45 degree vertical field of view, 512 px, on a ground plane),
  and (final round only) a sheet of all four with the icon.
- Round 1 (review/round1): reads at once as the drone's family (cream, gold ears, cyan lenses, graphite).
  Problems: the nozzle tips read yellow-gold, the same as the trim; the fuel windows sat buried in the tank
  tops; 7,688 triangles, close to the cap.
- Round 2 (review/round2): fire colour pushed to a deeper orange at lower strength, so the tips read
  orange-hot; fuel windows moved to the tanks' upper back at 45 degrees, where the game camera sees them;
  hover-pad segments trimmed (7,544). Rim and fill lights stopped casting shadows in the review rig.
- Round 3 (review/round3): no change needed in my reading.
- Round 4 (review/round4): materials made single-sided (backface culling); checked front and back for holes,
  none.
- Reviewer: my own reading of every render each round, against the drone reference and the brief.

## Licences
All geometry and textures generated by the script. No third-party assets.

## Checkpoint
- Step: EXPORT done (2026-11-14); final renders review/round4. Not yet imported or checked in Godot; waiting for
  Alex's review.
