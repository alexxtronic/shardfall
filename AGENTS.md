# Notes for agents working on Shardfall

Read README.md first. This file holds the rules that aren't obvious from the code.

## Balance rule (Alex, 2026-11-14)

Both races must have identical power per resource spent. Never give one race a unit the other lacks.
- **Shared numbers:** change cost, supply, time, range, speed or damage in `Defs.UNIT_SLOTS`, which both races share.
- **Race differences:** the only difference is `VOID_HP_MULT` and `VOID_CD_MULT`, which must stay equal so DPS x HP is unchanged.
- **After a stat change,** run the balance harness:
  - each mirror slot's margin should stay within about ±10%;
  - the overall Ambron win rate should stay near 50%;
  - every unit should keep both a counter and a target it beats.

## Simulation

- **Stepping:** `World.step(dt)` steps everything. Nothing in the sim may depend on rendering, frame rate or real time. That is what lets the balance harness and the bot games run headless and fast.
- **Positions:** units live on the ground plane as `p: Vector2`, and `x, y` of `p` map to Godot `x, z`. Air units add `fly` height.
- **Pathing:** `PathGrid` is a 1 m grid. Buildings, rocks and resources mark cells solid.
  - Main bases may only go on the hand-placed site cells.
  - Other buildings use `World.suggest_spot` to keep a one-cell lane and stay off crystal lines.
- **The bot:** `BotAI` uses the same costs and rules as the player, with no extra income. Run `-- --balance --game --seed=N` to read its game timeline when tuning it.

## Art contract

`docs/ART_SPEC.md` is the contract for every model:
- metres, base at z = 0, front facing Blender -Y;
- a `team` material, which the game recolours;
- `glow*` materials for emission;
- triangle budgets.

Animated units carry an armature with `idle_loop`, `walk_loop` (or `fly_loop` for flyers) and `attack`. `Models` matches these by name and loops idle, walk and fly. A node named `turret` turns toward the unit's target.

## Tests

Run the autotest after gameplay changes, and the balance harness after stat or bot changes. Asset-only changes need just a re-import (`Godot --headless --path . --import`) and a look at the `models` section.
