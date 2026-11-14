class_name SettingsPanel
extends ColorRect
## The settings overlay, shared by the title screen and the in-game menu: master, music and
## effects volume, and screen shake. Changes apply at once and are saved by Prefs.

signal closed


func _ready() -> void:
	color = Color(0, 0, 0, 0.72)
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -300
	p.offset_right = 300
	p.offset_top = -210
	p.offset_bottom = 210
	add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	p.add_child(v)
	var t := UiKit.head("SETTINGS", 30, UiKit.GOLD)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	for spec in [["Master volume", "master"], ["Music", "music"], ["Effects", "effects"]]:
		v.add_child(_slider(spec[0], spec[1]))
	var sh := CheckButton.new()
	sh.text = "Screen shake"
	sh.name = "shake"
	sh.focus_mode = Control.FOCUS_NONE
	sh.custom_minimum_size = Vector2(0, 52)
	sh.add_theme_font_size_override("font_size", 20)
	sh.button_pressed = bool(Prefs.get_v("shake"))
	sh.toggled.connect(func(on): Prefs.set_v("shake", on); Sfx.play("click"))
	v.add_child(sh)
	var b := Button.new()
	b.text = "Done"
	b.custom_minimum_size = Vector2(220, 60)
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(close)
	v.add_child(b)


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
