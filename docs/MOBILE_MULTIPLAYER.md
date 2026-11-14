# Shipping on mobile, with real-time 1v1 online

How to take Shardfall from a Mac build to the App Store and Google Play, and add ranked
real-time one-on-one games. Store and platform facts were checked in November 2026.

## Where we start from

These already work in our favour:
- **Mobile renderer.** The game runs on Godot 4.7's Mobile renderer, landscape, with touch controls.
- **Self-contained simulation.** `World.step(dt)` advances the whole game at a fixed step. Nothing in it reads frame rate, real time or rendering, which is why the balance harness can run thousands of games headless. Online play needs exactly this.
- **Profile and leaderboard.** `scripts/profile.gd` handles rating, best scores and history behind two small seams, `submit()` and `ladder()`, so an online backend can replace them.
- **Small download.** Audio is about 11 MB of Ogg, and textures import as ETC2/ASTC.

These are the gaps:
- **The simulation is not yet bit-exact across devices.** It calls `randf()` in seven places (`world.gd` misses, damage rolls and nudges, `unit.gd` acquisition timers, `bot_ai.gd`). It uses 32-bit `Vector2` maths and `sin`/`cos`, which can differ in the last bit between the iOS and Android maths libraries. It also relies on the engine's `AStarGrid2D`.
- **Orders are not serialised.** `commander.gd` calls `unit.cmd_move()`, `cmd_attack()`, `cmd_build()` and the rest directly. Online play needs every order to be a small serialisable command applied on a known simulation tick.
- **Projectiles live in the simulation.** Shots in flight are stepped inside `fx.step()`, so they count as game state, not decoration. They must be deterministic too.

## Recommendation: lockstep over a Nakama relay, with a fallback ready

An RTS has hundreds of units but only a handful of player actions per second. The standard answer, used by StarCraft, Age of Empires and most mobile RTS games, is **deterministic lockstep**:
- Both phones run the same simulation.
- They exchange only commands ("tick 812: units 41, 42 attack-move to 63,90"), a few hundred bytes per second.
- The server never runs the game. It only orders the commands and passes them on.

| | Lockstep through a Nakama match (recommended) | Server-authoritative (fallback) |
|---|---|---|
| What the server does | Orders, stamps and relays commands; compares state hashes | Runs the real simulation in headless Godot and streams state to both phones |
| Bandwidth | Tiny (commands only), fine on poor 4G | High: snapshots of every visible unit, needs delta compression |
| Server cost | One small VM handles thousands of matches | One headless Godot per match. Edgegap is about $0.00115 per vCPU-minute, roughly $0.03 per 20-minute match |
| Hard part | Cross-device determinism (fixed-point maths, seeded RNG) | Interpolation, prediction and bandwidth for hundreds of units |
| Cheating | Both clients hold the whole state, so a hacked client could reveal the map | Server only sends what each player can see, so no map hacks |
| Latency feel | Input delay of 100 to 200 ms, which is normal for RTS | Similar delay, plus snapshot jitter |

Do lockstep first, because it is cheaper, lighter on the network and suits an RTS. Keep the fallback realistic by keeping the simulation headless-clean (it already is). If the determinism spike below fails on real devices, run the same `World` on a server instead.

Two more paths were considered:
- **Godot's high-level multiplayer** (MultiplayerSynchronizer). It is too chatty for hundreds of units.
- **Hosted relays.** Hathora shut down in May 2026. Rivet pivoted away from game hosting. Photon's Godot SDK is still a preview.

Nakama is open source (Apache-2.0) and has an official Godot 4 client (3.4.0, with `NakamaMultiplayerPeer`). It covers:
- authentication: device, Apple, Google, email;
- matchmaking;
- authoritative match handlers in TypeScript, Lua or Go;
- leaderboards, friends, parties, storage and notifications.

It can be self-hosted on one VM or run on Heroic Labs' managed cloud.

## Phase 0: mobile builds (1 to 2 weeks)

**Android**
1. Install the Android build template and enable the **Gradle build** in the export preset. Google Play wants an AAB, and only the Gradle build makes one.
2. Godot 4.7 targets API 36 by default (minimum SDK 24), which meets Play's current target-level rule.
3. Sign with a Play App Signing upload key. Keep the keystore out of git. AGENTS.md already says so; add `*.keystore` and `*.jks` to `.gitignore`.
4. New personal Play developer accounts must run a **closed test with at least 12 testers for 14 days in a row** before production access. Start this clock early.

**iOS**
1. Export to an Xcode project. App Store uploads need **Xcode 26 and the iOS 26 SDK**. Godot 4.7 supports iOS 14 and later.
2. You need an Apple Developer account, a bundle id, signing in Xcode, and TestFlight for testers.

**Both stores**
- **Performance.** Target 60 fps on an iPhone 12 / Pixel 6a class phone and never below 30 in a 150-supply battle. Profile on device:
  - pool the FX nodes;
  - cap weather particles (`Weather.setup(low_detail=true)` already halves them);
  - turn shadows down on low-end GPUs.
- **Phone behaviour:**
  - respect safe areas (notches, home bar) with `DisplayServer.get_display_safe_area()`;
  - pause on app background;
  - keep the screen awake during matches;
  - add haptics on key events.
- **Privacy.** Fill in the privacy labels (App Store) and the Data safety form (Play). With analytics and crash reporting off and the profile local, this is close to "no data collected".
- **Accounts.** Once accounts exist, both stores require **in-app account deletion**. Apple requires **Sign in with Apple** (guideline 4.8) if you offer Google or other social logins.
- **Player interaction.** If players can see each other's names or chat, the stores expect report and block tools. Commander names count as user-generated content.

## Phase 1: determinism (2 to 3 weeks, the risky part)

1. **Seeded randomness.**
   - Give `World` its own `RandomNumberGenerator`, seeded from the match seed.
   - Route every `randf()`/`randi()` call in `world.gd`, `unit.gd`, `bot_ai.gd` and `fx.gd` through it.
   - Keep effects-only randomness (spark directions, sound pitch) on the global RNG so it can't desync the simulation.
2. **Fixed tick.** Run the simulation at exactly 20 Hz (`dt = 0.05`, which the harness already uses) and decouple it from rendering. The renderer interpolates between ticks (`_sync_visuals` already exists).
3. **Command layer.**
   - Add a `Command` (player, tick, kind, unit ids, target point or id, building id).
   - `commander.gd` and `bot_ai.gd` emit commands instead of calling `cmd_*` directly.
   - `World` applies each command at the start of its tick.

   This also gives replays and bug-report recordings for free.
4. **Bit-exact maths.**
   - Quantise positions and velocities to fixed point (for example, integers in 1/256 m) inside the simulation, or at least snap them after each step.
   - Replace `sin`/`cos`/`atan2` in simulation code with lookup tables.
   - Keep pathing on our own integer A* or flow fields rather than relying on `AStarGrid2D` internals.
   - Iterate units in id order, never by dictionary hash.
5. **Desync detection.** Every 10 ticks, hash the state (positions, health, resources, orders) and compare.
   - **The spike:** run the same recorded command stream on a Mac, an iPhone and an Android phone, and compare hashes for a full 20-minute game.
   - **Exit criterion:** identical hashes on all three. If they never match, switch to the server-authoritative fallback.

## Phase 2: online 1v1 (2 to 3 weeks)

1. **Nakama server.**
   - Use Docker Compose with CockroachDB or Postgres on a small VM (about $20 to $40 a month to start), or Heroic Cloud.
   - Put TLS in front and keep the server key and console password in environment variables, never in git.
2. **Authentication.** Silent device ID first. Then link Sign in with Apple and Google, so a player keeps their profile across phones.
3. **Matchmaking.**
   - Nakama's matchmaker queries on rating, for example `+properties.rating:>=900 +properties.rating:<=1300`.
   - Widen the window every few seconds of waiting.
   - Offer a bot match if nobody is found within about 60 seconds.
4. **Match handler (server TypeScript).**
   - Pick the map and seed.
   - Assign seats.
   - Run a 20 Hz tick that collects each player's commands, stamps them for tick `now + delay` and broadcasts the bundle. Adapt the delay to the measured ping, between 100 and 250 ms.
   - Validate commands: ownership, cost, tech and range. This stops trivial cheating.
   - Collect state hashes and end the match on a desync.
   - Handle a disconnect with a 60-second reconnect window, then a forfeit.
   - Enforce surrender and a maximum game length.
5. **Ranking.**
   - Nakama has no built-in Elo, so compute it in the match handler when the match ends. `Profile.elo_delta` is the reference; use K 40 for new players, then 24.
   - Write the result to a Nakama leaderboard (operator "set", sorted descending) and to the player's storage.
   - `Profile.ladder()` then reads the real leaderboard instead of the AI rivals.
6. **Client.**
   - A "Ranked 1v1" button.
   - A searching screen with a cancel button.
   - A loading screen that shows both commanders and ratings.
   - A ping indicator.
   - A reconnect banner.
   - The results screen already exists.

## Phase 3: live-service basics

- **Friends and challenges.** Rematch, private room codes, and friend invites through Nakama friends and parties.
- **Replays and spectating.** These come from the recorded command stream.
- **Safety.** Report and block, name filtering, and account deletion (also a store requirement).
- **Telemetry.** Crash reporting (for example the Sentry Godot SDK) and privacy-respecting match telemetry: game length, win rate by race and map, desync rate. Use them to balance the game from real games.
- **Platform features.** Game Center (GameCenterKit plugin) and Play Games Services (godot-play-game-services) for achievements and platform leaderboards. Play Games' own real-time multiplayer was shut down in 2020, so it can't carry the matches.

## Rough cost to run

| Item | Cost |
|---|---|
| Apple Developer Program | $99 a year |
| Google Play developer account | $25 once |
| Nakama VM and database for launch traffic | $20 to $40 a month |
| Fallback: server-authoritative matches on Edgegap | about $0.03 per 20-minute match |
