class_name Title
extends CanvasLayer
## Title screen: pick your race, the map, the bot's race and difficulty, then play. The
## chosen map's overhead view fills the background. Choices are remembered (Prefs).

signal play(cfg: Dictionary)
signal bench

var race: String = "ambron"
var enemy: String = "random"
var difficulty: String = "normal"
var map_id: String = "shatterfield"
var race_btns: Dictionary = {}
var enemy_btns: Dictionary = {}
var diff_btns: Dictionary = {}
var map_btns: Dictionary = {}
var help: Control
var root: Control
var backdrop: TextureRect
var extra_buttons: HBoxContainer
var chip: Button


func _ready() -> void:
	root = Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.theme = UiKit.make_theme()
	add_child(root)
	var base := ColorRect.new()
	base.color = Color(0.03, 0.03, 0.06)
	base.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(base)
	backdrop = TextureRect.new()
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	backdrop.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	backdrop.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	backdrop.modulate = Color(0.42, 0.42, 0.48)
	root.add_child(backdrop)
	var bg := TextureRect.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var grad := Gradient.new()
	grad.set_color(0, Color(0.1, 0.06, 0.16, 0.35))
	grad.set_color(1, Color(0.02, 0.02, 0.04, 0.97))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.42)
	gt.fill_to = Vector2(1.15, 1.15)
	bg.texture = gt
	bg.stretch_mode = TextureRect.STRETCH_SCALE
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	root.add_child(bg)
	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_CENTER)
	v.offset_left = -600
	v.offset_right = 600
	v.offset_top = -340
	v.offset_bottom = 340
	v.add_theme_constant_override("separation", 12)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	root.add_child(v)
	var t := UiKit.head("SHARDFALL", 60, UiKit.GOLD)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.add_theme_constant_override("outline_size", 10)
	v.add_child(t)
	var sub := UiKit.label("Gather golden crystals and Void Slime. Take the high ground. Break the enemy.", 17, UiKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	v.add_child(_race_cards())
	v.add_child(_map_cards())
	var opts := HBoxContainer.new()
	opts.alignment = BoxContainer.ALIGNMENT_CENTER
	opts.add_theme_constant_override("separation", 36)
	opts.add_child(_row("Opponent", ["random", "ambron", "void"], enemy_btns, func(x): _set_enemy(x)))
	opts.add_child(_row("Bot", ["easy", "normal", "hard", "extreme"], diff_btns, func(x): _set_diff(x)))
	v.add_child(opts)
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 18)
	v.add_child(h)
	var tb := _button("Tutorial", Vector2(160, 64), _tutorial)
	tb.name = "TutorialButton"
	if not bool(Prefs.get_v("tutorial_done")):
		tb.add_theme_color_override("font_color", UiKit.GOOD)
	h.add_child(tb)
	h.add_child(_button("How to play", Vector2(180, 64), func(): help.visible = true; Sfx.play("click")))
	h.add_child(_button("Settings", Vector2(160, 64), _open_settings))
	var pb := _button("PLAY", Vector2(280, 64), _go)
	pb.name = "PlayButton"
	pb.add_theme_font_size_override("font_size", 30)
	pb.add_theme_color_override("font_color", UiKit.GOLD)
	h.add_child(pb)
	h.add_child(_button("Leaderboard", Vector2(200, 64), _open_leaderboard))
	extra_buttons = h
	chip = Button.new()
	chip.name = "ProfileChip"
	chip.focus_mode = Control.FOCUS_NONE
	chip.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	chip.offset_left = -360
	chip.offset_right = -16
	chip.offset_top = 14
	chip.offset_bottom = 62
	chip.alignment = HORIZONTAL_ALIGNMENT_RIGHT
	chip.add_theme_font_size_override("font_size", 17)
	chip.pressed.connect(_open_leaderboard)
	root.add_child(chip)
	Profile.changed.connect(_refresh_profile)
	_refresh_profile()
	var foot := HBoxContainer.new()
	foot.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	foot.offset_left = 16
	foot.offset_top = -52
	foot.offset_bottom = -12
	foot.offset_right = 420
	foot.add_theme_constant_override("separation", 14)
	root.add_child(foot)
	var cr := Button.new()
	cr.text = "Credits"
	cr.flat = true
	cr.focus_mode = Control.FOCUS_NONE
	cr.add_theme_font_size_override("font_size", 16)
	cr.add_theme_color_override("font_color", UiKit.DIM)
	cr.pressed.connect(func():
		Sfx.play("open")
		var c := CreditsPanel.new()
		c.name = "Credits"
		root.add_child(c))
	foot.add_child(cr)
	var ver := UiKit.label("v%s" % ProjectSettings.get_setting("application/config/version", "1.0"), 14, Color(UiKit.DIM, 0.6))
	ver.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	foot.add_child(ver)
	_drift()
	_help(root)
	Sfx.music("menu")
	Sfx.ambience("")
	_set_race(String(Prefs.get_v("race")), false)
	_set_enemy(String(Prefs.get_v("enemy")), false)
	_set_diff(String(Prefs.get_v("difficulty")), false)
	_set_map(Maps.resolve(String(Prefs.get_v("map"))), false)


func _button(text: String, sz: Vector2, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = sz
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(cb)
	return b


func _race_cards() -> HBoxContainer:
	var cards := HBoxContainer.new()
	cards.alignment = BoxContainer.ALIGNMENT_CENTER
	cards.add_theme_constant_override("separation", 22)
	for r in ["ambron", "void"]:
		var info: Dictionary = Defs.RACE_INFO[r]
		var b := Button.new()
		b.custom_minimum_size = Vector2(440, 176)
		b.focus_mode = Control.FOCUS_NONE
		b.toggle_mode = true
		var inner := VBoxContainer.new()
		inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		inner.offset_left = 12
		inner.offset_right = -12
		inner.offset_top = 8
		inner.offset_bottom = -8
		inner.add_theme_constant_override("separation", 2)
		b.add_child(inner)
		var icons := HBoxContainer.new()
		icons.alignment = BoxContainer.ALIGNMENT_CENTER
		icons.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.add_child(icons)
		for slot in ["worker", "infantry", "vehicle_flame", "air_light", "special"]:
			var tex := UiKit.icon(Defs.unit_id(r, slot))
			if tex == null:
				continue
			var tr := TextureRect.new()
			tr.custom_minimum_size = Vector2(72, 72)
			tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
			tr.texture = tex
			icons.add_child(tr)
		var nm := UiKit.head(String(info["name"]).to_upper(), 28, info["accent"])
		nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		inner.add_child(nm)
		var bl := UiKit.label(info["blurb"], 14, UiKit.TEXT)
		bl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		bl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		inner.add_child(bl)
		var rr: String = r
		b.pressed.connect(func(): _set_race(rr))
		cards.add_child(b)
		race_btns[r] = b
	return cards


func _map_cards() -> HBoxContainer:
	var cards := HBoxContainer.new()
	cards.alignment = BoxContainer.ALIGNMENT_CENTER
	cards.add_theme_constant_override("separation", 16)
	for id in Maps.LIST:
		var d: Dictionary = Maps.DEFS[id]
		var b := Button.new()
		b.name = "map_" + id
		b.custom_minimum_size = Vector2(350, 112)
		b.focus_mode = Control.FOCUS_NONE
		b.toggle_mode = true
		var row := HBoxContainer.new()
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		row.offset_left = 8
		row.offset_right = -8
		row.offset_top = 8
		row.offset_bottom = -8
		row.add_theme_constant_override("separation", 12)
		b.add_child(row)
		var pv := TextureRect.new()
		pv.custom_minimum_size = Vector2(96, 96)
		pv.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		pv.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		pv.mouse_filter = Control.MOUSE_FILTER_IGNORE
		pv.texture = _preview(id)
		row.add_child(pv)
		var col := VBoxContainer.new()
		col.mouse_filter = Control.MOUSE_FILTER_IGNORE
		col.alignment = BoxContainer.ALIGNMENT_CENTER
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		col.add_theme_constant_override("separation", 4)
		row.add_child(col)
		var nm := UiKit.head(String(d["name"]).to_upper(), 18, d.get("accent", UiKit.TEXT))
		col.add_child(nm)
		var tg := UiKit.label(String(d.get("tag", "")), 15, UiKit.TEXT)
		tg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		col.add_child(tg)
		var best := UiKit.label("", 13, UiKit.DIM)
		best.name = "best"
		col.add_child(best)
		var mid: String = id
		b.pressed.connect(func(): _set_map(mid))
		cards.add_child(b)
		map_btns[id] = b
	return cards


## The backdrop map drifts and breathes slowly behind the menu.
func _drift() -> void:
	var vs := get_viewport().get_visible_rect().size
	backdrop.pivot_offset = vs * 0.5
	backdrop.scale = Vector2(1.06, 1.06)
	var tw := create_tween().set_loops()
	tw.tween_property(backdrop, "scale", Vector2(1.16, 1.16), 26.0).set_trans(Tween.TRANS_SINE)
	tw.parallel().tween_property(backdrop, "position", Vector2(-30, 18), 26.0).set_trans(Tween.TRANS_SINE)
	tw.tween_property(backdrop, "scale", Vector2(1.06, 1.06), 26.0).set_trans(Tween.TRANS_SINE)
	tw.parallel().tween_property(backdrop, "position", Vector2(24, -12), 26.0).set_trans(Tween.TRANS_SINE)


static func _preview(id: String) -> Texture2D:
	var path := "res://assets/ui/maps/%s.png" % id
	return load(path) if ResourceLoader.exists(path) else null


func _row(label_text: String, opts: Array, store: Dictionary, cb: Callable) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 8)
	var l := UiKit.label(label_text, 19, UiKit.DIM)
	l.custom_minimum_size = Vector2(0, 0)
	h.add_child(l)
	for o in opts:
		var b := Button.new()
		b.text = String(o).capitalize()
		b.custom_minimum_size = Vector2(122, 52)
		b.focus_mode = Control.FOCUS_NONE
		b.toggle_mode = true
		var oo: String = o
		b.pressed.connect(func(): cb.call(oo))
		h.add_child(b)
		store[o] = b
	return h


func _mark(store: Dictionary, key: String) -> void:
	for k in store:
		(store[k] as Button).button_pressed = k == key


func _set_race(r: String, sound: bool = true) -> void:
	race = r if race_btns.has(r) else "ambron"
	_mark(race_btns, race)
	Prefs.set_v("race", race)
	if sound:
		Sfx.play("click")


func _set_enemy(r: String, sound: bool = true) -> void:
	enemy = r if enemy_btns.has(r) else "random"
	_mark(enemy_btns, enemy)
	Prefs.set_v("enemy", enemy)
	if sound:
		Sfx.play("click")


func _set_diff(d: String, sound: bool = true) -> void:
	difficulty = d if diff_btns.has(d) else "normal"
	_mark(diff_btns, difficulty)
	Prefs.set_v("difficulty", difficulty)
	if sound:
		Sfx.play("click")


func _set_map(id: String, sound: bool = true) -> void:
	map_id = id if map_btns.has(id) else Maps.LIST[0]
	_mark(map_btns, map_id)
	backdrop.texture = _preview(map_id)
	Prefs.set_v("map", map_id)
	if sound:
		Sfx.play("click")


func _refresh_profile() -> void:
	if not is_instance_valid(chip):
		return
	var r := Profile.rating()
	var tr: Array = Profile.tier(r)
	chip.text = "%s   %d · %s · #%d" % [Profile.player_name(), r, tr[0], Profile.rank()]
	chip.add_theme_color_override("font_color", tr[1])
	for id in map_btns:
		var best: Label = (map_btns[id] as Button).find_child("best", true, false)
		var b := Profile.best(id)
		best.text = "Best %s" % UiKit.fmt_int(b) if b > 0 else "No score yet"


func _open_leaderboard() -> void:
	Sfx.play("open")
	var lb := LeaderboardPanel.new()
	lb.name = "Leaderboard"
	root.add_child(lb)


func _open_settings() -> void:
	Sfx.play("click")
	var s := SettingsPanel.new()
	s.name = "Settings"
	s.bench_cb = func() -> void: bench.emit()
	root.add_child(s)


func _go() -> void:
	var e := enemy
	if e == "random":
		e = ["ambron", "void"][randi() % 2]
	Sfx.play("complete")
	play.emit({"races": [race, e], "ai": [false, true], "difficulty": difficulty, "human": 0, "map": map_id})


## A guided first match: your race against an easy bot of the other race on Shatterfield.
func _tutorial() -> void:
	Sfx.play("complete")
	var e := "void" if race == "ambron" else "ambron"
	play.emit({"races": [race, e], "ai": [false, true], "difficulty": "easy", "human": 0, "map": "shatterfield", "tutorial": true})


func _help(parent: Control) -> void:
	help = ColorRect.new()
	(help as ColorRect).color = Color(0, 0, 0, 0.78)
	help.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	help.visible = false
	parent.add_child(help)
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -480
	p.offset_right = 480
	p.offset_top = -330
	p.offset_bottom = 330
	help.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 3)
	p.add_child(v)
	var lines := [
		["How to play", 26, UiKit.GOLD],
		["Win by destroying every enemy building.", 16, UiKit.TEXT],
		["• Drag one finger to look around, pinch to zoom. Tap the minimap to jump.", 15, UiKit.TEXT],
		["• Tap a unit or building to select it. Double-tap a unit (or hold on it) to select all of that type on screen. Double-tap a building to select every building of that type.", 15, UiKit.TEXT],
		["• Hold on the ground, then slide, to draw a box: everything of yours inside is selected. ARMY selects every fighter; hold ARMY and slide to pick ground, air, workers, idle workers or one unit type.", 15, UiKit.TEXT],
		["• With units selected, tap the ground to move there: they don't stop to fight on the way. Tap an enemy to focus it (a red circle marks it). Hold on the ground and slide to the green MOVE or the red ATTACK target to choose.", 15, UiKit.TEXT],
		["• Workers harvest on their own. Tap crystals (or your Void Machine / Void Maw) to send selected workers.", 15, UiKit.TEXT],
		["• BUILDINGS (or a worker's Build button) opens the structures. Tap to place, tap again or ✓ to confirm. Hold BUILDINGS and slide to select every building of one type; BASE taps go through your bases.", 15, UiKit.TEXT],
		["• Void Slime needs an extractor built on a black slime pile first.", 15, UiKit.TEXT],
		["• Supply limits your army: build Power Relays (Ambron) or Brood Pods (Void).", 15, UiKit.TEXT],
		["• Ambron structures must stand inside a Power Relay's field (the blue circle shown while placing).", 15, UiKit.TEXT],
		["• Towers defend your base: the Ambron Arc Tower throws lightning, the Void Slime Spire spits slime.", 15, UiKit.TEXT],
		["• Upgrades: the Armory / Evolution Pit gives ground units +1 weapons and +1 armour; the Aero Lab / Sky Chrysalis does the same for flyers. Striders and Rippers are fast, cheap raiders for hitting worker lines.", 15, UiKit.TEXT],
		["• High ground: units can't see up a cliff until they climb a ramp, and shots fired uphill miss 30% of the time.", 15, UiKit.TEXT],
		["• Expand: build a new main base at another crystal field to grow your economy.", 15, UiKit.TEXT],
		["• Settings: Customize buttons adds quick buttons (ground, air, one unit or building type) and lets you drag them anywhere. A lower Graphics level keeps your phone cooler.", 15, UiKit.TEXT],
		["Tech: main base → infantry → vehicles/beasts → air → special.", 14, UiKit.DIM],
	]
	for l in lines:
		var lab := UiKit.label(l[0], l[1], l[2])
		lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lab.custom_minimum_size = Vector2(900, 0)
		v.add_child(lab)
	var b := _button("Got it", Vector2(200, 56), func(): help.visible = false; Sfx.play("click"))
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(b)
