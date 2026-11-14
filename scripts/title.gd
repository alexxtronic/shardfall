class_name Title
extends CanvasLayer
## Title screen: pick your race, the bot's race and difficulty, then play.

signal play(cfg: Dictionary)

var race: String = "ambron"
var enemy: String = "random"
var difficulty: String = "normal"
var race_btns: Dictionary = {}
var enemy_btns: Dictionary = {}
var diff_btns: Dictionary = {}
var help: Control


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.theme = UiKit.make_theme()
	add_child(root)
	var bg := TextureRect.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var grad := Gradient.new()
	grad.set_color(0, Color(0.13, 0.08, 0.2))
	grad.set_color(1, Color(0.03, 0.03, 0.06))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.35)
	gt.fill_to = Vector2(1.1, 1.1)
	bg.texture = gt
	bg.stretch_mode = TextureRect.STRETCH_SCALE
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	root.add_child(bg)
	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_CENTER)
	v.offset_left = -520
	v.offset_right = 520
	v.offset_top = -330
	v.offset_bottom = 330
	v.add_theme_constant_override("separation", 14)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	root.add_child(v)
	var t := UiKit.label("SHARDFALL", 72, UiKit.GOLD)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.add_theme_constant_override("outline_size", 10)
	v.add_child(t)
	var sub := UiKit.label("Gather golden crystals and Void Slime. Build an army. Break the enemy.", 18, UiKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	# race cards
	var cards := HBoxContainer.new()
	cards.alignment = BoxContainer.ALIGNMENT_CENTER
	cards.add_theme_constant_override("separation", 24)
	v.add_child(cards)
	for r in ["ambron", "void"]:
		var info: Dictionary = Defs.RACE_INFO[r]
		var b := Button.new()
		b.custom_minimum_size = Vector2(420, 230)
		b.focus_mode = Control.FOCUS_NONE
		b.toggle_mode = true
		var inner := VBoxContainer.new()
		inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		inner.offset_left = 12
		inner.offset_right = -12
		inner.offset_top = 10
		inner.offset_bottom = -10
		b.add_child(inner)
		var icons := HBoxContainer.new()
		icons.alignment = BoxContainer.ALIGNMENT_CENTER
		icons.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.add_child(icons)
		for slot in ["worker", "infantry", "vehicle_flame", "special"]:
			var tex := UiKit.icon(Defs.unit_id(r, slot))
			var tr := TextureRect.new()
			tr.custom_minimum_size = Vector2(88, 88)
			tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
			if tex:
				tr.texture = tex
			else:
				var cr := ColorRect.new()
				cr.color = info["color"]
				cr.custom_minimum_size = Vector2(60, 60)
				cr.mouse_filter = Control.MOUSE_FILTER_IGNORE
				icons.add_child(cr)
				continue
			icons.add_child(tr)
		var nm := UiKit.label(String(info["name"]).to_upper(), 34, info["accent"])
		nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		inner.add_child(nm)
		var bl := UiKit.label(info["blurb"], 15, UiKit.TEXT)
		bl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		bl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		inner.add_child(bl)
		var rr: String = r
		b.pressed.connect(func(): _set_race(rr))
		cards.add_child(b)
		race_btns[r] = b
	v.add_child(_row("Opponent", ["random", "ambron", "void"], enemy_btns, func(x): _set_enemy(x)))
	v.add_child(_row("Bot", ["easy", "normal", "hard"], diff_btns, func(x): _set_diff(x)))
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 20)
	v.add_child(h)
	var hb := Button.new()
	hb.text = "How to play"
	hb.custom_minimum_size = Vector2(200, 66)
	hb.focus_mode = Control.FOCUS_NONE
	hb.pressed.connect(func(): help.visible = true)
	h.add_child(hb)
	var pb := Button.new()
	pb.text = "PLAY"
	pb.name = "PlayButton"
	pb.custom_minimum_size = Vector2(280, 66)
	pb.focus_mode = Control.FOCUS_NONE
	pb.add_theme_font_size_override("font_size", 30)
	pb.add_theme_color_override("font_color", UiKit.GOLD)
	pb.pressed.connect(_go)
	h.add_child(pb)
	_help(root)
	_set_race("ambron")
	_set_enemy("random")
	_set_diff("normal")


func _row(label_text: String, opts: Array, store: Dictionary, cb: Callable) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 10)
	var l := UiKit.label(label_text, 20, UiKit.DIM)
	l.custom_minimum_size = Vector2(110, 0)
	h.add_child(l)
	for o in opts:
		var b := Button.new()
		b.text = String(o).capitalize()
		b.custom_minimum_size = Vector2(150, 52)
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


func _set_race(r: String) -> void:
	race = r
	_mark(race_btns, r)
	Sfx.play("click")


func _set_enemy(r: String) -> void:
	enemy = r
	_mark(enemy_btns, r)
	Sfx.play("click")


func _set_diff(d: String) -> void:
	difficulty = d
	_mark(diff_btns, d)
	Sfx.play("click")


func _go() -> void:
	var e := enemy
	if e == "random":
		e = ["ambron", "void"][randi() % 2]
	Sfx.play("complete")
	play.emit({"races": [race, e], "ai": [false, true], "difficulty": difficulty, "human": 0})


func _help(root: Control) -> void:
	help = ColorRect.new()
	(help as ColorRect).color = Color(0, 0, 0, 0.75)
	help.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	help.visible = false
	root.add_child(help)
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -470
	p.offset_right = 470
	p.offset_top = -300
	p.offset_bottom = 300
	help.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	p.add_child(v)
	var lines := [
		["How to play", 30, UiKit.GOLD],
		["Win by destroying every enemy building.", 18, UiKit.TEXT],
		["• Drag one finger to look around, pinch to zoom. Tap the minimap to jump.", 17, UiKit.TEXT],
		["• Tap a unit or building to select it. Double-tap a unit (or hold on it) to select all of that type on screen.", 17, UiKit.TEXT],
		["• Hold, then drag, to draw a selection box. ARMY selects every fighter.", 17, UiKit.TEXT],
		["• With units selected, tap the ground to attack-move, tap an enemy to attack. Use Move to retreat.", 17, UiKit.TEXT],
		["• Workers harvest on their own. Tap crystals (or your Void Machine / Void Maw) to send selected workers.", 17, UiKit.TEXT],
		["• BUILD (or a worker's Build button) opens the structures. Tap to place, tap again or ✓ to confirm.", 17, UiKit.TEXT],
		["• Void Slime needs an extractor built on a black slime pile first.", 17, UiKit.TEXT],
		["• Supply limits your army: build Power Relays (Ambron) or Brood Pods (Void).", 17, UiKit.TEXT],
		["• Expand: build a new main base at another crystal field to grow your economy.", 17, UiKit.TEXT],
		["Tech: main base → infantry → vehicles/beasts → air → special.", 17, UiKit.DIM],
	]
	for l in lines:
		var lab := UiKit.label(l[0], l[1], l[2])
		lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lab.custom_minimum_size = Vector2(880, 0)
		v.add_child(lab)
	var b := Button.new()
	b.text = "Got it"
	b.custom_minimum_size = Vector2(200, 56)
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(func(): help.visible = false)
	v.add_child(b)
