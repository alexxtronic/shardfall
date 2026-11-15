class_name PlayerState
extends RefCounted
## One side of the match: resources, supply and what they've built.

var id: int = 0
var race: String = "ambron"
var is_ai: bool = false
var name: String = "Player"
var color: Color = Color(0.25, 0.65, 1.0)
var minerals: int = 0
var slime: int = 0
var supply_cap: int = 0
var alive: bool = true
var start_site: int = 0
var upgrades: Dictionary = {}     # Defs.UPGRADES key -> level researched (1 once done)

# match stats
var gathered_m: int = 0
var gathered_s: int = 0
var units_made: int = 0
var units_lost: int = 0
var kills: int = 0
var value_killed: float = 0.0
var value_lost: float = 0.0


## +1 per finished upgrade of `stat` ("attack" or "armor") for a unit that flies or walks.
func bonus(stat: String, air: bool) -> float:
	return float(upgrades.get(("air_" if air else "ground_") + stat, 0))


func can_afford(cost: Array) -> bool:
	return minerals >= int(cost[0]) and slime >= int(cost[1])


func pay(cost: Array) -> void:
	minerals -= int(cost[0])
	slime -= int(cost[1])


func refund(cost: Array, frac: float = 1.0) -> void:
	minerals += int(round(int(cost[0]) * frac))
	slime += int(round(int(cost[1]) * frac))
