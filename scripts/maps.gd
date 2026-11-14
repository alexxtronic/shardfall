class_name Maps
extends RefCounted
## The three skirmish maps and their looks. Every map is 144 x 144 m with 180-degree
## symmetry: only player 1's half is written here and MapGen adds the mirror image of each
## shape, so both sides get exactly the same ground. Screen up is -y. Player 1 starts
## bottom-left (site 0), player 2 top-right (site 1).
##
## Shapes, all in player 1's half:
##   sites     [centre, direction to its resources]; site 0 is the main base
##   plateaus  ["disc", centre, radius, level] or ["poly", [points], level]
##   ramps     [low end, high end, width]
##   rocks     rock blobs [centre, radius]
##   hazards   ["lava" (blocks) or "ice" (looks only), "disc", centre, radius] or
##             [type, "river", [points], half width, [[gap centre, gap radius]...]]

const LIST := ["shatterfield", "frostspire", "ember_rift"]

const DEFS := {
	"shatterfield": {
		"name": "Shatterfield",
		"tag": "High-ground mains · central ridge",
		"accent": Color(0.78, 0.55, 1.0),
		"blurb": "Basalt flats under a violet sky. Mains sit on high ground with one ramp; a central ridge overlooks the middle bases.",
		"theme": "alien",
		"seed": 7,
		"sites": [
			[Vector2(22.5, 121.5), Vector2(-1, 1)],
			[Vector2(22.5, 80.5), Vector2(-1, 0)],
			[Vector2(63.5, 122.5), Vector2(0, 1)],
			[Vector2(24.5, 26.5), Vector2(-1, -1)],
			[Vector2(56.5, 68.5), Vector2(-1, 0)],
		],
		"plateaus": [
			["disc", Vector2(21.0, 123.0), 21.5, 1],
			["disc", Vector2(72.0, 72.0), 8.5, 1],
		],
		"ramps": [
			[Vector2(26.0, 95.0), Vector2(26.0, 104.5), 5.0],
			[Vector2(62.8, 81.2), Vector2(67.4, 76.6), 4.5],
		],
		"rocks": [
			[Vector2(72, 72), 3.0],
			[Vector2(45, 100), 3.5],
			[Vector2(52, 48), 3.0],
			[Vector2(38, 58), 2.5],
			[Vector2(84, 104), 3.0],
			[Vector2(104, 98), 3.5],
			[Vector2(64, 98), 2.0],
			[Vector2(70, 50), 2.5],
		],
		"hazards": [],
	},
	"frostspire": {
		"name": "Frostspire Pass",
		"tag": "Three tiers · frozen lakes",
		"accent": Color(0.55, 0.85, 1.0),
		"blurb": "A frozen glacier in three tiers. Mains on the high shelf, naturals one step down, frozen lakes in the low passes.",
		"theme": "frost",
		"seed": 19,
		"sites": [
			[Vector2(21.5, 121.5), Vector2(-1, 1)],
			[Vector2(56.5, 125.5), Vector2(0, 1)],
			[Vector2(21.5, 74.5), Vector2(-1, 0)],
			[Vector2(60.5, 88.5), Vector2(-1, 0)],
			[Vector2(23.5, 23.5), Vector2(-1, -1)],
		],
		"plateaus": [
			["poly", [Vector2(0, 103), Vector2(84, 103), Vector2(88, 144), Vector2(0, 144)], 1],
			["disc", Vector2(19.0, 124.0), 19.5, 2],
			["disc", Vector2(18.0, 20.0), 16.0, 1],
			["disc", Vector2(72.0, 72.0), 7.5, 1],
		],
		"ramps": [
			[Vector2(45.0, 118.0), Vector2(35.0, 118.0), 5.0],
			[Vector2(70.0, 94.5), Vector2(70.0, 105.0), 5.0],
			[Vector2(37.5, 27.8), Vector2(31.0, 25.2), 5.0],
			[Vector2(63.5, 80.5), Vector2(68.1, 75.9), 4.5],
		],
		"rocks": [
			[Vector2(44, 88), 3.0],
			[Vector2(40, 44), 3.5],
			[Vector2(86, 112), 3.0],
			[Vector2(100, 96), 3.0],
			[Vector2(54, 58), 2.5],
			[Vector2(72, 72), 2.5],
		],
		"hazards": [
			["ice", "disc", Vector2(38.0, 60.0), 8.0],
			["ice", "disc", Vector2(84.0, 94.0), 6.0],
		],
	},
	"ember_rift": {
		"name": "Ember Rift",
		"tag": "Lava river · three crossings",
		"accent": Color(1.0, 0.58, 0.22),
		"blurb": "A lava river splits the map. Three crossings: a wide middle bridge and two side fords watched from basalt mesas.",
		"theme": "ember",
		"seed": 31,
		"sites": [
			[Vector2(22.5, 121.5), Vector2(-1, 1)],
			[Vector2(22.5, 82.5), Vector2(-1, 0)],
			[Vector2(62.5, 123.5), Vector2(0, 1)],
			[Vector2(60.5, 94.5), Vector2(0, 1)],
			[Vector2(21.5, 47.5), Vector2(-1, 0)],
		],
		"plateaus": [
			["disc", Vector2(21.0, 123.0), 21.0, 1],
			["disc", Vector2(48.0, 62.0), 7.0, 1],
		],
		"ramps": [
			[Vector2(42.8, 107.0), Vector2(36.3, 111.8), 5.0],
			[Vector2(55.8, 70.4), Vector2(51.4, 65.7), 4.5],
		],
		"rocks": [
			[Vector2(42, 92), 3.0],
			[Vector2(84, 110), 3.0],
			[Vector2(36, 66), 2.5],
			[Vector2(100, 122), 2.5],
		],
		"hazards": [
			["lava", "river", [Vector2(-2, -2), Vector2(16, 22), Vector2(32, 38), Vector2(50, 50), Vector2(72, 72)], 3.6, [[Vector2(72, 72), 7.0], [Vector2(44, 46), 4.5]]],
			["lava", "disc", Vector2(96.0, 132.0), 4.5],
		],
	},
}

## Looks per theme: ground colours, sky, sun, weather and audio.
const THEMES := {
	"alien": {
		"dust": Color(0.33, 0.29, 0.33), "rust": Color(0.47, 0.35, 0.29), "basalt": Color(0.13, 0.12, 0.16),
		"vein": Color(0.45, 0.22, 0.6), "plate": Color(0.40, 0.40, 0.45),
		"cliff_a": Color(0.11, 0.09, 0.15), "cliff_b": Color(0.32, 0.25, 0.37), "snow": 0.0,
		"hazard": Color(0.4, 1.0, 0.25), "hazard_glow": 0.0, "vein_glow": 0.0,
		"sky_top": Color(0.09, 0.07, 0.16), "sky_horizon": Color(0.36, 0.3, 0.42),
		"ground_bottom": Color(0.05, 0.04, 0.07), "ground_horizon": Color(0.3, 0.26, 0.34),
		"sun": Color(1.0, 0.92, 0.82), "sun_energy": 1.5, "sun_rot": Vector3(-52, -38, 0),
		"fill": Color(0.55, 0.6, 1.0), "fill_energy": 0.35, "ambient": 0.9, "exposure": 1.05,
		"rock_tint": Color(1, 1, 1), "weather": "motes", "music": "theme_alien", "battle": "battle_a", "ambience": "amb_alien",
		"minimap_low": Color(0.22, 0.21, 0.26), "minimap_step": Color(0.07, 0.065, 0.08),
	},
	"frost": {
		"dust": Color(0.5, 0.56, 0.64), "rust": Color(0.4, 0.47, 0.57), "basalt": Color(0.16, 0.2, 0.28),
		"vein": Color(0.55, 0.8, 1.0), "plate": Color(0.62, 0.67, 0.74),
		"cliff_a": Color(0.3, 0.38, 0.5), "cliff_b": Color(0.62, 0.74, 0.86), "snow": 1.0,
		"hazard": Color(0.45, 0.72, 0.92), "hazard_glow": 0.0, "vein_glow": 0.0,
		"sky_top": Color(0.18, 0.28, 0.45), "sky_horizon": Color(0.68, 0.78, 0.9),
		"ground_bottom": Color(0.1, 0.13, 0.18), "ground_horizon": Color(0.6, 0.68, 0.78),
		"sun": Color(0.92, 0.96, 1.0), "sun_energy": 1.1, "sun_rot": Vector3(-46, -32, 0),
		"fill": Color(0.6, 0.75, 1.0), "fill_energy": 0.4, "ambient": 0.65, "exposure": 0.82,
		"rock_tint": Color(0.75, 0.85, 1.0), "weather": "snow", "music": "theme_frost", "battle": "battle_a", "ambience": "amb_frost",
		"minimap_low": Color(0.6, 0.66, 0.74), "minimap_step": Color(0.1, 0.11, 0.13),
	},
	"ember": {
		"dust": Color(0.2, 0.16, 0.15), "rust": Color(0.34, 0.2, 0.14), "basalt": Color(0.07, 0.06, 0.06),
		"vein": Color(0.62, 0.15, 0.04), "plate": Color(0.3, 0.27, 0.26),
		"cliff_a": Color(0.08, 0.07, 0.07), "cliff_b": Color(0.26, 0.18, 0.15), "snow": 0.0,
		"hazard": Color(1.0, 0.42, 0.08), "hazard_glow": 3.0, "vein_glow": 0.3, "vein_w": 0.004, "vein_mix": 0.3,
		"sky_top": Color(0.12, 0.05, 0.04), "sky_horizon": Color(0.5, 0.2, 0.1),
		"ground_bottom": Color(0.05, 0.02, 0.02), "ground_horizon": Color(0.36, 0.14, 0.07),
		"sun": Color(1.0, 0.72, 0.5), "sun_energy": 1.35, "sun_rot": Vector3(-58, -44, 0),
		"fill": Color(1.0, 0.45, 0.25), "fill_energy": 0.4, "ambient": 0.7, "exposure": 1.0,
		"rock_tint": Color(0.55, 0.47, 0.45), "weather": "embers", "music": "theme_ember", "battle": "battle_ember", "ambience": "amb_ember",
		"minimap_low": Color(0.2, 0.15, 0.14), "minimap_step": Color(0.08, 0.06, 0.06),
	},
}


static func resolve(id: String) -> String:
	if id == "standard" or id == "" or not DEFS.has(id):
		return "shatterfield"
	return id


static func get_def(id: String) -> Dictionary:
	return DEFS[resolve(id)]


static func theme_of(id: String) -> Dictionary:
	return THEMES[String(get_def(id)["theme"])]
