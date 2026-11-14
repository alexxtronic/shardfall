class_name CreditsPanel
extends ColorRect
## Who made what. Mirrors assets/CREDITS.md (which has the links); keep the two in step.

signal closed

const LINES := [
	["SHARDFALL", "h"],
	["Design, code and 3D: made for this project with Godot 4, Kiln, Tripo and Blender.", ""],
	["MUSIC", "h"],
	["Loading screen loop — Brandon Morris (menu)", ""],
	["Hunter-class Lifeform — vitalezzz (Shatterfield)", ""],
	["Icy Realm 7 and 8 — cynicmusic (Frostspire Pass)", ""],
	["Entering the Volcano — Umplix (Ember Rift)", ""],
	["Battle Theme A — cynicmusic", ""],
	["Epic Boss Battle — Juhani Junkala", ""],
	["Victory Fanfare Short — cynicmusic  ·  Icy Game Over — Sudocolon", ""],
	["SOUND", "h"],
	["Sci-Fi Sounds, Interface Sounds and Voiceover Pack — Kenney", ""],
	["Creature, water, slime and mud packs — rubberduck", ""],
	["Fleshy Bone Breaks — Zane Little Music  ·  Electricity — BMacZero", ""],
	["Insect or alien scream — qubodup", ""],
	["Space Winds — aquinn  ·  Wind whoosh loop — SketchMan3  ·  Deep rumble — gmason", ""],
	["All audio is CC0 (public domain), found on OpenGameArt.org and kenney.nl. Thank you!", "d"],
	["FONTS", "h"],
	["Chakra Petch — Cadson Demak  ·  Orbitron — Matt McInerney (SIL Open Font License)", ""],
]


func _ready() -> void:
	color = Color(0, 0, 0, 0.78)
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	theme = UiKit.make_theme()
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -470
	p.offset_right = 470
	p.offset_top = -330
	p.offset_bottom = 330
	p.add_theme_stylebox_override("panel", UiKit.solid_panel())
	add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 5)
	p.add_child(v)
	for l in LINES:
		var kind: String = l[1]
		var lab := UiKit.head(l[0], 18, UiKit.GOLD) if kind == "h" else UiKit.label(l[0], 16, UiKit.DIM if kind == "d" else UiKit.TEXT)
		lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lab.custom_minimum_size = Vector2(900, 0)
		if kind == "h":
			lab.custom_minimum_size.y = 34
			lab.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
		v.add_child(lab)
	var b := Button.new()
	b.text = "Close"
	b.custom_minimum_size = Vector2(220, 56)
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(close)
	v.add_child(b)


func close() -> void:
	Sfx.play("close")
	closed.emit()
	queue_free()
