class_name SettingsPanel
extends ColorRect
## The settings overlay, shared by the title screen and the in-game menu: master, music and
## effects volume, graphics quality, screen shake, and the quick-button editor. Changes apply
## at once and are saved by Prefs.

signal closed

var bench_cb: Callable = Callable()   # set by the title screen: runs the performance check


func _ready() -> void:
	color = Color(0, 0, 0, 0.72)
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	theme = UiKit.make_theme()
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -300
	p.offset_right = 300
	p.offset_top = -236
	p.offset_bottom = 236
	p.add_theme_stylebox_override("panel", UiKit.solid_panel())
	add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	p.add_child(v)
	var t := UiKit.head("SETTINGS", 30, UiKit.GOLD)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	for spec in [["Master volume", "master"], ["Music", "music"], ["Effects", "effects"]]:
		v.add_child(_slider(spec[0], spec[1]))
	v.add_child(_graphics())
	var sh := CheckButton.new()
	sh.text = "Screen shake"
	sh.name = "shake"
	sh.focus_mode = Control.FOCUS_NONE
	sh.custom_minimum_size = Vector2(0, 52)
	sh.add_theme_font_size_override("font_size", 20)
	sh.button_pressed = bool(Prefs.get_v("shake"))
	sh.toggled.connect(func(on): Prefs.set_v("shake", on); Sfx.play("click"))
	v.add_child(sh)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 16)
	v.add_child(row)
	var qb := Button.new()
	qb.text = "Customize buttons"
	qb.name = "Customize"
	qb.custom_minimum_size = Vector2(250, 60)
	qb.focus_mode = Control.FOCUS_NONE
	qb.pressed.connect(_customize)
	row.add_child(qb)
	var b := Button.new()
	b.text = "Done"
	b.custom_minimum_size = Vector2(200, 60)
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(close)
	row.add_child(b)
	if bench_cb.is_valid():
		p.offset_top = -262
		p.offset_bottom = 262
		var pc := Button.new()
		pc.text = "Performance check (2 minutes, hands off)"
		pc.name = "Bench"
		pc.flat = true
		pc.focus_mode = Control.FOCUS_NONE
		pc.custom_minimum_size = Vector2(0, 40)
		pc.add_theme_font_size_override("font_size", 15)
		pc.add_theme_color_override("font_color", UiKit.DIM)
		pc.pressed.connect(func():
			Sfx.play("click")
			var cb := bench_cb
			closed.emit()
			queue_free()
			cb.call())
		v.add_child(pc)


## Graphics: one slider from Battery to Max, with what the level means under it.
func _graphics() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 0)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 14)
	box.add_child(h)
	var l := UiKit.label("Graphics", 20, UiKit.TEXT)
	l.custom_minimum_size = Vector2(170, 0)
	h.add_child(l)
	var s := HSlider.new()
	s.name = "graphics"
	s.min_value = 0
	s.max_value = Graphics.LEVELS.size() - 1
	s.step = 1
	s.tick_count = Graphics.LEVELS.size()
	s.ticks_on_borders = true
	s.value = Graphics.level()
	s.custom_minimum_size = Vector2(280, 44)
	s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	s.focus_mode = Control.FOCUS_NONE
	h.add_child(s)
	var nm := UiKit.label(String(Graphics.LEVELS[Graphics.level()]["name"]), 18, UiKit.DIM)
	nm.custom_minimum_size = Vector2(90, 0)
	h.add_child(nm)
	var hint := UiKit.label("", 14, UiKit.DIM)
	hint.name = "graphics_hint"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(hint)
	var show := func(lv: int):
		nm.text = String(Graphics.LEVELS[lv]["name"])
		hint.text = Graphics.describe(lv) + ("  ·  runs cooler, saves battery" if lv <= 1 else "  ·  sharpest picture, most heat")
	show.call(Graphics.level())
	s.value_changed.connect(func(x):
		Prefs.set_v("graphics", int(x))
		show.call(int(x))
		Sfx.play("click"))
	return box


func _customize() -> void:
	Sfx.play("click")
	var ed := QuickButtonsEditor.new()
	ed.name = "QuickButtonsEditor"
	add_child(ed)


func _slider(label_text: String, key: String) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 14)
	var l := UiKit.label(label_text, 20, UiKit.TEXT)
	l.custom_minimum_size = Vector2(170, 0)
	h.add_child(l)
	var s := HSlider.new()
	s.name = key
	s.min_value = 0.0
	s.max_value = 1.0
	s.step = 0.05
	s.value = float(Prefs.get_v(key))
	s.custom_minimum_size = Vector2(280, 44)
	s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	s.focus_mode = Control.FOCUS_NONE
	h.add_child(s)
	var pct := UiKit.label("%d%%" % roundi(s.value * 100.0), 18, UiKit.DIM)
	pct.custom_minimum_size = Vector2(60, 0)
	h.add_child(pct)
	s.value_changed.connect(func(x):
		Prefs.set_v(key, x)
		pct.text = "%d%%" % roundi(x * 100.0)
		if key != "music":
			Sfx.play("click"))
	return h


func close() -> void:
	Sfx.play("click")
	closed.emit()
	queue_free()
