# Shardfall art spec (draft)

Working name: **Shardfall**. A mobile, landscape, real-time strategy game in Godot 4.7 (Mobile renderer). Two races: **Ambron** (precision robots) and **Void** (alien swarm). The camera looks down at about 55 degrees from 18 to 45 m away, so silhouettes and colour blocking matter far more than small detail.

## Style references

- `art/ref/ambron_style_reference.png`: Alex's existing Tripo "robot crystal harvester" turnaround. **Ambron look**: chunky, rounded, toy-like sci-fi. Ivory/cream plates (`#EDE3CF`), warm gold/orange trim (`#E0A33A`, darker `#B9771E`), graphite joints and housings (`#2B2F36`), glowing cyan lights and lenses (`#5FE3FF`, emissive). Big soft bevels everywhere, panel seams, no sharp grime. Think stylised PBR (roughness 0.35-0.55, metallic 0-0.3 on trim).
- `art/ref/void_style_reference.png`: **Void look**: organic, predatory, insectoid. Glossy purple chitin plates (`#4A2A63` to `#6B3C8A`, highlights `#8E5BB0`), bone/ivory spikes and blade edges (`#D8C8A8` fading to `#9C8A6A` at the base), crimson-maroon flesh in the gaps (`#5E1A2A` to `#8A2C3C`), acid-green glowing sacs and eyes (`#8CFF3A`, emissive). Curved hooks, layered armour plates, spines. Buildings look grown, not built.

Both races must read instantly at small size: Ambron = bright cream and gold with cyan glow; Void = dark purple with bone spikes and green glow.

## Technical contract for every model (GLB)

- One `.glb` per asset in `assets/models/<id>.glb`, exported from Blender with `+Y up` (Blender default glTF export), **Apply Modifiers on**, no cameras or lights, no animations unless stated.
- **Units are metres.** The model's base sits on the ground plane: lowest point at Blender `z = 0`, centred on the origin in X and Y.
- **Front faces Blender -Y** (this becomes +Z in Godot; the game turns units so +Z points where they move).
- Materials: Principled BSDF only, with base colour from a texture or flat value, roughness, metallic, and **emission** for glowing parts (Godot imports emission). Keep to 1-4 materials per asset; one shared 1024 px or smaller texture is fine. Glowing parts use a material whose name starts with `glow` so the game can pulse it.
- One material named exactly **`team`** on a few small accent areas (stripes, a light band, a banner): the game recolours it to the player colour (blue vs red). Give it a light grey base colour in Blender.
- Triangle budgets (mobile, many units on screen): worker and infantry 2-5k, vehicles and air 4-8k, special unit 10-16k, buildings 4-12k, resource nodes 0.5-2k each.
- No loose interior faces, normals facing out, smooth shading with auto-smooth/weighted normals where it helps.
- A 256 x 256 transparent PNG icon of each asset at `assets/icons/<id>.png`: three-quarter view from the front-left and slightly above, framed tight, lit warm key + cool rim, rendered in Blender (EEVEE or Cycles), transparent film.
- Build scripts live at `art/<group>/build.py` (run with `Blender --background --factory-startup --python-exit-code 1 --python art/<group>/build.py -- <id|all>`), review renders in `art/<group>/review/`, and a short production log per asset in `art/<group>/<id>_log.md` (kiln format: Config, Reference, Intent, Inventory, Pipeline, Review rounds, Checkpoint).

## Sizes (metres)

| Kind | Footprint / radius | Height |
|---|---|---|
| Worker | radius 0.4 | 0.9 |
| Ranged infantry | radius 0.4 | 1.1 |
| Heavy infantry | radius 0.6 | 1.6 |
| Ground vehicles / beasts | radius 0.9 (about 2 m long) | 1.3-1.6 |
| Light air | radius 0.6 | (flies at 3.5 m; model about 0.6 m thick) |
| Heavy air | radius 1.2 | about 1.2 thick |
| Special unit | radius 2.0 | 4-5 |
| Main base | 5 x 5 m footprint | 4-5 |
| Production buildings | 3 x 3 m | 3-3.5 |
| Special building | 4 x 4 m | 4-5 |
| Supply building | 2 x 2 m | 2-2.5 |
| Void Machine / Void Maw (extractor, sits on a slime pile) | 3 x 3 m | 2.5 |
| Golden crystal node | about 2 x 1 m | 1.4-2.2 |
| Slime pile | 3 x 3 m | 0.6-0.9 |

Buildings should fill their footprint (a little inset, about 0.15 m each side) so the grid reads clearly.

## Asset list and ids

### Ambron
| id | Name | What it is |
|---|---|---|
| `ambron_worker` | Harvester | Alex's Tripo drone (existing model) |
| `ambron_lancer` | Lancer | Ranged infantry robot with an energy rifle (Tripo) |
| `ambron_bulwark` | Bulwark | Heavy armoured mech-trooper with a shield arm and arm cannon (Tripo) |
| `ambron_scorcher` | Scorcher | Hover flame tank with a twin-nozzle flamer turret (Tripo) |
| `ambron_hailfire` | Hailfire | Two-legged missile walker with twin multi-tube pods (Tripo) |
| `ambron_dart` | Dart | Fast light interceptor, small swept wings, twin cannons (Tripo) |
| `ambron_monolith` | Monolith | Slow heavy gunship, four ducted fans, big underslung cannon (Tripo) |
| `ambron_sovereign` | Sovereign | Giant four-legged walking titan with a beam cannon (Tripo) |
| `ambron_citadel` | Citadel | Main base: drop-off, trains Harvesters |
| `ambron_relay` | Power Relay | Supply structure: obelisk with a floating crystal |
| `ambron_void_machine` | Void Machine | Extractor built over a slime pile |
| `ambron_assembly` | Assembly Bay | Trains Lancers and Bulwarks |
| `ambron_forge` | Mech Forge | Builds Scorchers and Hailfires |
| `ambron_skyport` | Skyport | Builds Darts and Monoliths, landing pad |
| `ambron_spire` | Apex Spire | Builds the Sovereign |

### Void
| id | Name | What it is |
|---|---|---|
| `void_drudge` | Drudge | Worker grub-beetle (Tripo) |
| `void_spitter` | Spitter | Ranged acid-spitting infantry creature (Tripo) |
| `void_mauler` | Mauler | Heavy brute with bone scythes (Tripo) |
| `void_acidback` | Acidback | Huge armoured beetle that sprays acid (Tripo) |
| `void_spinefiend` | Spinefiend | Artillery creature that hurls bone spines from a spined back (Tripo) |
| `void_skitter` | Skitter | Fast bat-winged flyer (Tripo) |
| `void_gorgon` | Gorgon | Bloated floating bomber creature with acid sacs (Tripo) |
| `void_leviathan` | Leviathan | Colossal crawling behemoth (Tripo) |
| `void_hive` | Hive Heart | Main base |
| `void_pod` | Brood Pod | Supply structure: pulsing egg sac |
| `void_maw` | Void Maw | Extractor over a slime pile |
| `void_nest` | Spawning Nest | Trains Spitters and Maulers |
| `void_warren` | Beast Warren | Grows Acidbacks and Spinefiends |
| `void_aerie` | Aerie | Grows Skitters and Gorgons |
| `void_abyss` | Abyssal Lair | Grows the Leviathan |

### Neutral
| id | What it is |
|---|---|
| `crystal_a` .. `crystal_d` | Golden spike crystal clusters (minerals), four variations |
| `slime_pile` | Black Void Slime pile (oily black with purple-green sheen) |
| `rock_a` .. `rock_c` | Alien rock formations that block paths |
