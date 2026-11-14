# Roadmap: what would make Shardfall better

Ordered by the value each step adds for the effort it takes. The mobile launch and online
1v1 plan has its own page: [MOBILE_MULTIPLAYER.md](MOBILE_MULTIPLAYER.md).

## Next five

1. **A guided first match.**
   - A short tutorial on Shatterfield that teaches one thing at a time: select, harvest, build a supply structure, train infantry, attack-move, take the high ground.
   - New players of a touch RTS drop out in the first five minutes, so nothing else pays back more.
   - Reuse the existing hint banner and `world.message`, and gate each step on a world event.
2. **One active ability per unit.** Shared slots keep the races balanced, so each race needs a mirrored ability in each slot. Some ideas:
   - Lancer overcharge or Spitter frenzy (attack speed for health);
   - Bulwark siege mode or Mauler burrow;
   - Scorcher napalm patch or Acidback acid pool;
   - Sovereign or Leviathan ultimate.

   Abilities give fights decisions and highlight moments. Add a round ability button to the selection panel. The balance harness can test each pair.
3. **Upgrades.**
   - Weapons, armour and air research levels 1 to 3 at the infantry, vehicle and air buildings.
   - Upgrades give mid-game goals and a reason to keep a bank, and they slot into the shared `Defs` costs.
4. **A smarter, livelier bot.**
   - **Personalities:** turtle, rush, air, expand.
   - **Scouting:** the bot reacts to what it sees.
   - **Harassment:** it raids workers with light air.
   - **A Brutal difficulty:** better micro and target fire on the same economy (no cheating).

   Replays from the command layer (MOBILE_MULTIPLAYER Phase 1) make tuning the bot much easier.
5. **Mobile build on real phones.**
   - Get Android and iOS builds running, then profile a 150-supply battle on a mid-range phone.
   - Pool effects, add an auto low-detail mode and respect the notch safe areas.
   - Start Google Play's 14-day closed test early.

## Gameplay

- **High-ground extras.** Watchtowers on ridges grant vision when a unit stands next to them. Some ramps could be destructible (rocks), opening late-game paths.
- **More maps.** A 2v2 map and a map rotation for ranked play.
  - The data format in `scripts/maps.gd` takes a new map in under a hundred lines.
  - A simple in-game editor could paint plateaus, ramps and hazards for player 1's half and mirror them.
- **Hazard rules.**
  - Lava already blocks movement.
  - Ice could speed up ground units and stop them turning sharply.
  - Embers could slowly damage units standing near lava.
- **Comeback tools.** A last-stand bonus for the base under attack, or a costly emergency recall.
- **Modes.**
  - 2v2 against bots.
  - Survival waves.
  - Daily challenge seeds with a fixed race, map and bot (these suit the existing leaderboard).

## Feel and presentation

- **Unit voice barks.** Short acknowledgements on select and order ("Ready", a Void hiss), with the race voice already chosen for the announcer. Duck the music under voice lines.
- **Construction and destruction.**
  - Buildings rise from scaffolding and slime.
  - Wrecks and scorch decals stay on the ground for a while.
  - Big Void units get a death animation.
- **Weather events.** A snow squall that cuts vision, or an ember storm, both purely visual or with mild effects.
- **Control groups for touch.** A bottom bar with 1 to 4 group buttons (long-press to save, tap to recall). A production-queue strip for every building.
- **Accessibility.** Colour-blind team colours, larger UI scale, subtitles for the announcer, and a separate volume slider for voice lines.

## Meta and retention

- **Seasons.** The ladder resets every season, with tier rewards: cosmetic team colours, unit skins, a profile badge.
- **Achievements.** Through Game Center and Play Games Services. Cloud save through Nakama storage.
- **Commander profile.** Favourite race, win rate by map and matchup, recent games with replays.

## Tech

- **Performance.** Flow-field pathing for big armies, multithreaded fog updates, LOD on unit models, and a GPU particle budget.
- **Save and resume.** Saving a single-player match mid-game (the simulation's state is plain data).
- **Crash reporting and analytics.** Opt-in, privacy-respecting. Feed real matchup win rates back into `docs/BALANCE.md`.
- **CI.** Run the autotest and the quick balance harness on every push (headless Godot in GitHub Actions). Fail on parse errors, broken tests, or a mirror slot drifting past ±10%.

## Business options

- **Premium.** One price, no ads. This is the simplest store review and fits a strategy audience.
- **Free with cosmetics.** Skins, team colours and announcer packs only; never gameplay power, which the balance rule forbids anyway.
- **Either way,** ranked online play needs accounts. That brings in account deletion, Sign in with Apple and report/block (see MOBILE_MULTIPLAYER.md).
