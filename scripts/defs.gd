extends Node
## Every number in the game: races, units, buildings, economy.
##
## Balance rule (Alex, 2026-11-14): both races get the same power per resource.
## Each unit belongs to a SLOT that both races share. The slot fixes cost, supply,
## build time, speed, range, radius, sight and tags for both races. A race only
## changes the *shape* of the power: Void units have VOID_HP_MULT more hit points
## and attack VOID_CD_MULT slower, so damage-per-second x hit-points (Lanchester
## strength) is identical. tools/balance (run with --balance) checks it in battle.

const MAP_SIZE := 144
const START_MINERALS := 50
const START_WORKERS := 12
const SUPPLY_MAX := 200
const MINERAL_PER_TRIP := 5
const SLIME_PER_TRIP := 4
const MINE_TIME := 2.0
const SLIME_TIME := 1.4
const MINERAL_AMOUNT := 1500
const SLIME_AMOUNT := 2250
const SLIME_VALUE := 1.5  # one slime is worth this many minerals when valuing armies

const VOID_HP_MULT := 1.15
const VOID_CD_MULT := 1.15

const RACE_INFO := {
	"ambron": {
		"name": "Ambron",
		"blurb": "Precision machines of cream and gold. Long-range firepower, clean lines of fire.",
		"color": Color(0.93, 0.89, 0.81),
		"accent": Color(0.37, 0.89, 1.0),
	},
	"void": {
		"name": "Void",
		"blurb": "A living swarm of chitin, bone and acid. Tough hides, relentless bodies.",
		"color": Color(0.42, 0.24, 0.55),
		"accent": Color(0.55, 1.0, 0.23),
	},
}

## Shared unit slots (identical for both races before the race shape is applied).
const UNIT_SLOTS := {
	"worker": {
		"cost": [50, 0], "supply": 1, "time": 12.0, "hp": 40.0, "armor": 0.0,
		"speed": 3.9, "radius": 0.4, "air": false, "sight": 8.0,
		"tags": ["light", "worker"], "model_h": 0.95, "model_w": 0.95,
		"weapon": {"dmg": 5.0, "cd": 1.5, "range": 0.4, "ground": true, "air": false, "splash": 0.0, "bonus": {}, "proj": 0.0},
	},
	"infantry": {
		"cost": [50, 0], "supply": 1, "time": 18.0, "hp": 45.0, "armor": 0.0,
		"speed": 3.15, "radius": 0.4, "air": false, "sight": 9.0,
		"tags": ["light"], "model_h": 1.15, "model_w": 0.9,
		"weapon": {"dmg": 6.0, "cd": 0.61, "range": 5.0, "ground": true, "air": true, "splash": 0.0, "bonus": {}, "proj": 34.0},
	},
	"heavy": {
		"cost": [100, 25], "supply": 2, "time": 22.0, "hp": 160.0, "armor": 1.0,
		"speed": 2.8, "radius": 0.55, "air": false, "sight": 9.0,
		"tags": ["armored"], "model_h": 1.6, "model_w": 1.3,
		"weapon": {"dmg": 10.0, "cd": 0.9, "range": 4.5, "ground": true, "air": false, "splash": 0.8, "bonus": {"light": 8.0}, "proj": 24.0},
	},
	"vehicle_flame": {
		"cost": [125, 25], "supply": 2, "time": 22.0, "hp": 150.0, "armor": 1.0,
		"speed": 3.6, "radius": 0.8, "air": false, "sight": 10.0,
		"tags": ["armored", "mech"], "model_h": 1.35, "model_w": 1.9,
		"weapon": {"dmg": 12.0, "cd": 1.5, "range": 3.5, "ground": true, "air": false, "splash": 1.8, "bonus": {"light": 10.0}, "proj": 0.0},
	},
	"vehicle_missile": {
		"cost": [125, 75], "supply": 3, "time": 30.0, "hp": 170.0, "armor": 1.0,
		"speed": 2.6, "radius": 0.85, "air": false, "sight": 11.0,
		"tags": ["armored", "mech"], "model_h": 1.5, "model_w": 2.0,
		"weapon": {"dmg": 20.0, "cd": 2.2, "range": 9.0, "ground": true, "air": false, "splash": 0.7, "bonus": {"armored": 40.0}, "proj": 14.0},
	},
	"air_light": {
		"cost": [100, 50], "supply": 2, "time": 26.0, "hp": 100.0, "armor": 0.0,
		"speed": 5.2, "radius": 0.6, "air": true, "fly": 3.6, "sight": 10.0,
		"tags": ["light", "air"], "model_h": 0.8, "model_w": 1.4,
		"weapon": {"dmg": 8.0, "cd": 1.0, "range": 5.0, "ground": true, "air": true, "splash": 0.0, "bonus": {"air": 8.0}, "proj": 30.0},
	},
	"air_heavy": {
		"cost": [250, 150], "supply": 4, "time": 42.0, "hp": 320.0, "armor": 2.0,
		"speed": 2.4, "radius": 1.2, "air": true, "fly": 4.6, "sight": 10.0,
		"tags": ["armored", "air"], "model_h": 1.4, "model_w": 2.6,
		"weapon": {"dmg": 30.0, "cd": 1.6, "range": 6.0, "ground": true, "air": false, "splash": 0.0, "bonus": {"armored": 20.0}, "proj": 20.0},
	},
	"special": {
		"cost": [400, 300], "supply": 8, "time": 60.0, "hp": 900.0, "armor": 3.0,
		"speed": 2.0, "radius": 1.9, "air": false, "sight": 12.0,
		"tags": ["armored", "massive"], "model_h": 4.6, "model_w": 4.2,
		"weapon": {"dmg": 40.0, "cd": 1.4, "range": 8.0, "ground": true, "air": true, "splash": 1.5, "bonus": {}, "proj": 0.0},
	},
}

## Shared building slots.
const BUILDING_SLOTS := {
	"main": {"cost": [400, 0], "time": 71.0, "hp": 1500.0, "armor": 1.0, "size": 5, "supply": 15, "sight": 11.0, "produces": ["worker"], "requires": [], "model_h": 4.6},
	"supply": {"cost": [100, 0], "time": 18.0, "hp": 400.0, "armor": 1.0, "size": 2, "supply": 8, "sight": 7.0, "produces": [], "requires": [], "model_h": 2.4},
	"extractor": {"cost": [75, 0], "time": 21.0, "hp": 500.0, "armor": 1.0, "size": 3, "supply": 0, "sight": 7.0, "produces": [], "requires": [], "model_h": 2.6},
	"barracks": {"cost": [150, 0], "time": 46.0, "hp": 1000.0, "armor": 1.0, "size": 3, "supply": 0, "sight": 9.0, "produces": ["infantry", "heavy"], "requires": ["main"], "model_h": 3.0},
	"factory": {"cost": [150, 100], "time": 43.0, "hp": 1250.0, "armor": 1.0, "size": 3, "supply": 0, "sight": 9.0, "produces": ["vehicle_flame", "vehicle_missile"], "requires": ["barracks"], "model_h": 3.2},
	"airfield": {"cost": [150, 100], "time": 36.0, "hp": 1300.0, "armor": 1.0, "size": 3, "supply": 0, "sight": 9.0, "produces": ["air_light", "air_heavy"], "requires": ["factory"], "model_h": 3.4},
	"special": {"cost": [150, 150], "time": 50.0, "hp": 1000.0, "armor": 1.0, "size": 4, "supply": 0, "sight": 9.0, "produces": ["special"], "requires": ["airfield"], "model_h": 5.0},
}

const BUILD_ORDER := ["main", "supply", "extractor", "barracks", "factory", "airfield", "special"]

## Race-specific names and looks for each slot.
const RACE_UNITS := {
	"ambron": {
		"worker": {"id": "ambron_worker", "name": "Harvester", "fx": "zap", "desc": "Gathers crystals and slime, builds structures."},
		"infantry": {"id": "ambron_lancer", "name": "Lancer", "fx": "bolt", "desc": "Ranged infantry. Hits air and ground."},
		"heavy": {"id": "ambron_bulwark", "name": "Bulwark", "fx": "shell", "desc": "Armoured frontline trooper. Strong against light units."},
		"vehicle_flame": {"id": "ambron_scorcher", "name": "Scorcher", "fx": "flame", "desc": "Flame tank. Burns groups of light units."},
		"vehicle_missile": {"id": "ambron_hailfire", "name": "Hailfire", "fx": "missile", "desc": "Long-range missile artillery. Shreds armour."},
		"air_light": {"id": "ambron_dart", "name": "Dart", "fx": "bolt", "desc": "Fast interceptor. Hunts air units."},
		"air_heavy": {"id": "ambron_monolith", "name": "Monolith", "fx": "cannon", "desc": "Heavy gunship. Pounds ground targets."},
		"special": {"id": "ambron_sovereign", "name": "Sovereign", "fx": "beam", "desc": "Colossal walking titan. Splash beam hits air and ground."},
	},
	"void": {
		"worker": {"id": "void_drudge", "name": "Drudge", "fx": "bite", "desc": "Gathers crystals and slime, grows structures."},
		"infantry": {"id": "void_spitter", "name": "Spitter", "fx": "glob", "desc": "Acid-spitting infantry. Hits air and ground."},
		"heavy": {"id": "void_mauler", "name": "Mauler", "fx": "shard", "desc": "Armoured brute hurling bone shards. Strong against light units."},
		"vehicle_flame": {"id": "void_acidback", "name": "Acidback", "fx": "acid", "desc": "Armoured beetle spraying acid. Melts groups of light units."},
		"vehicle_missile": {"id": "void_spinefiend", "name": "Spinefiend", "fx": "spine", "desc": "Hurls bone spines from far away. Shreds armour."},
		"air_light": {"id": "void_skitter", "name": "Skitter", "fx": "glob", "desc": "Fast bat-winged flyer. Hunts air units."},
		"air_heavy": {"id": "void_gorgon", "name": "Gorgon", "fx": "bomb", "desc": "Floating bomber sac. Pounds ground targets."},
		"special": {"id": "void_leviathan", "name": "Leviathan", "fx": "bile", "desc": "Colossal behemoth. Splash bile hits air and ground."},
	},
}

const RACE_BUILDINGS := {
	"ambron": {
		"main": {"id": "ambron_citadel", "name": "Citadel", "desc": "Main base. Trains Harvesters, takes in resources."},
		"supply": {"id": "ambron_relay", "name": "Power Relay", "desc": "+8 supply."},
		"extractor": {"id": "ambron_void_machine", "name": "Void Machine", "desc": "Build on a slime pile to harvest Void Slime."},
		"barracks": {"id": "ambron_assembly", "name": "Assembly Bay", "desc": "Trains Lancers and Bulwarks."},
		"factory": {"id": "ambron_forge", "name": "Mech Forge", "desc": "Builds Scorchers and Hailfires."},
		"airfield": {"id": "ambron_skyport", "name": "Skyport", "desc": "Builds Darts and Monoliths."},
		"special": {"id": "ambron_spire", "name": "Apex Spire", "desc": "Builds the Sovereign."},
	},
	"void": {
		"main": {"id": "void_hive", "name": "Hive Heart", "desc": "Main base. Spawns Drudges, takes in resources."},
		"supply": {"id": "void_pod", "name": "Brood Pod", "desc": "+8 supply."},
		"extractor": {"id": "void_maw", "name": "Void Maw", "desc": "Grow on a slime pile to harvest Void Slime."},
		"barracks": {"id": "void_nest", "name": "Spawning Nest", "desc": "Spawns Spitters and Maulers."},
		"factory": {"id": "void_warren", "name": "Beast Warren", "desc": "Grows Acidbacks and Spinefiends."},
		"airfield": {"id": "void_aerie", "name": "Aerie", "desc": "Grows Skitters and Gorgons."},
		"special": {"id": "void_abyss", "name": "Abyssal Lair", "desc": "Grows the Leviathan."},
	},
}

var units: Dictionary = {}      # id -> full unit def
var buildings: Dictionary = {}  # id -> full building def


func _ready() -> void:
	_build()


func _build() -> void:
	units.clear()
	buildings.clear()
	for race in RACE_UNITS:
		var rmap: Dictionary = RACE_UNITS[race]
		for slot in rmap:
			var d: Dictionary = (UNIT_SLOTS[slot] as Dictionary).duplicate(true)
			var r: Dictionary = rmap[slot]
			d["id"] = r["id"]
			d["name"] = r["name"]
			d["fx"] = r["fx"]
			d["desc"] = r["desc"]
			d["race"] = race
			d["slot"] = slot
			d["kind"] = "unit"
			if race == "void":
				d["hp"] = roundf(float(d["hp"]) * VOID_HP_MULT)
				var w: Dictionary = d["weapon"]
				w["cd"] = snappedf(float(w["cd"]) * VOID_CD_MULT, 0.01)
			units[d["id"]] = d
	for race in RACE_BUILDINGS:
		var bmap: Dictionary = RACE_BUILDINGS[race]
		for slot in bmap:
			var d: Dictionary = (BUILDING_SLOTS[slot] as Dictionary).duplicate(true)
			var r: Dictionary = bmap[slot]
			d["id"] = r["id"]
			d["name"] = r["name"]
			d["desc"] = r["desc"]
			d["race"] = race
			d["slot"] = slot
			d["kind"] = "building"
			if race == "void":
				d["hp"] = roundf(float(d["hp"]) * VOID_HP_MULT)
			# resolve produced unit slots to this race's ids
			var prod: Array = []
			for s in d["produces"]:
				prod.append(RACE_UNITS[race][s]["id"])
			d["produces"] = prod
			var req: Array = []
			for s in d["requires"]:
				req.append(RACE_BUILDINGS[race][s]["id"])
			d["requires"] = req
			buildings[d["id"]] = d


func unit_id(race: String, slot: String) -> String:
	return RACE_UNITS[race][slot]["id"]


func building_id(race: String, slot: String) -> String:
	return RACE_BUILDINGS[race][slot]["id"]


func get_def(id: String) -> Dictionary:
	if units.has(id):
		return units[id]
	if buildings.has(id):
		return buildings[id]
	return {}


func value_of(id: String) -> float:
	var d := get_def(id)
	if d.is_empty():
		return 0.0
	var c: Array = d["cost"]
	return float(c[0]) + float(c[1]) * SLIME_VALUE


func race_building_list(race: String) -> Array:
	var out: Array = []
	for slot in BUILD_ORDER:
		out.append(RACE_BUILDINGS[race][slot]["id"])
	return out


func dps(id: String) -> float:
	var d: Dictionary = units[id]
	var w: Dictionary = d["weapon"]
	return float(w["dmg"]) / float(w["cd"])
