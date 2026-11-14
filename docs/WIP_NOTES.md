# Work in progress: maps, elevation and polish (2026-11-14)

## Done on this branch
- `scripts/terrain.gd`: levels 0–2, 2.6 m apart. Cliff bands are two cells wide and blocked in the PathGrid. Ramps are walkable slopes with walls along their sides. Heights live at cell corners and are read back bilinearly.
- High-ground rules:
  - Ground units can't see up cliffs in the fog of war.
  - A ground shot fired uphill misses 30% of the time.
- `scripts/maps.gd`, with `map_gen.gd` now data-driven. Three mirrored maps:
  - Shatterfield (alien);
  - Frostspire Pass (frost, 3 tiers, ice lakes);
  - Ember Rift (lava river, 3 crossings).
  The theme drives ground colours, sky, sun, minimap and weather (`scripts/weather.gd`).
- Units, buildings, effects, overlay, commander, camera picking and focus, and the fog plane all use the terrain height.
- Autotest:
  - `--only=maps` passes 15/0: mirror symmetry, 8+2 resources at every base, every base reachable.
  - `--only=terrain` passes 8/0.

## Open bug (fix first)
The ground mesh still renders flat. The simulation heights are right (the tests pass), but `ground.gdshader` doesn't appear to lift vertices by `hmap`, so units on plateaus float. Next steps:
- Check that `hmap` reaches the material (print it in the `_terrain` autotest section; `-s` scripts can't see autoloads).
- Check that `textureLod` on an RH texture works in the vertex stage.
- Fallback: bake the heights straight into an ArrayMesh in GDScript instead of displacing in the shader.

## Still to do
- Map select on the title screen.
- Sound overhaul.
- Leaderboard (local Elo vs bot ratings: easy 800 / normal 1200 / hard 1600) with a results screen.
- Settings (music and effects volume).
- Docs.
- Full test run, balance run, merge.

## Free assets shortlist (CC0 unless marked)
All of these were checked to resolve with HEAD requests. OGA files live at `https://opengameart.org/sites/default/files/` (shown as OF below).
- **UI:** Kenney Interface Sounds (OF `kenney_interfaceSounds.zip`).
- **Announcer:** Kenney Voiceover Pack (OF `Voiceover%20Pack.zip`).
- **Void race:**
  - rubberduck creature packs (OF `80-CC0-creature-SFX_0.zip`, `80-CC0-creature-sfx-2.zip`);
  - slime pack (OF `water-splash-slime-sfx.zip`);
  - bone breaks (OF `wet_breaks.zip`, `deep_breaks.zip`).
- **Zap:** BMacZero (OF `spark.wav`).
- **Win and lose stings:**
  - cynicmusic Victory Fanfare (OF `Heavy_ConceptB.mp3`);
  - Icy Game Over (OF `Icy%20Game%20Over.mp3`).
- **Ambience:**
  - wind loop (OF `wind%20woosh%20loop.ogg`);
  - deep_rumble (OF `deep_rumble.ogg`);
  - Space Winds (OF `space-wind.mp3`).
- **Music:**
  - menu: Brandon Morris loading loop (OF `b423b42.wav`);
  - alien: Hunter-class Lifeform (OF `hunter-class_lifeform_0.mp3`);
  - frost: Icy Heights (OF `theme-loop.ogg`);
  - ember: Juhani Junkala Epic Boss Battle loop (OF `Juhani%20Junkala%20-%20Epic%20Boss%20Battle%20%5BSeamlessly%20Looping%5D.wav`).
- **Particles:** Kenney Particle Pack (github.com/Calinou/kenney-particle-pack).
- **CC-BY options:** Kevin MacLeod "Ice Demon" and "Corruption" (incompetech, CC BY 4.0, needs credit).

## Mobile and multiplayer (research brief, verified Nov 2026)
- **Netcode:** input-only lockstep through a self-hosted Nakama authoritative match. The match sequences commands, logs them and compares state checksums. Start with a determinism spike:
  - replace `randf`, Vector2 float maths and the built-in A* in the sim;
  - compare state hashes across Mac, iPhone and Android.

  If that fails, run a server-authoritative headless Godot per match on Edgegap (about $0.03 per 20-minute match).
- **Hathora:** shut down May 2026.
- **Nakama:**
  - Apache-2.0, with an official Godot 4 client;
  - leaderboards, matchmaker and device/Apple auth;
  - no built-in Elo, so write it in the server runtime.
- **Stores:**
  - Android: target API 36 (Godot 4.7 default), AAB via a custom Gradle build, and new Play accounts need a 12-tester closed test for 14 days.
  - iOS: Xcode 26 and the iOS 26 SDK.
  - Both: in-app account deletion, privacy labels, and report/block if players can interact.
