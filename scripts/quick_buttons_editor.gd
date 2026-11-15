class_name QuickButtonsEditor
extends Control
## Settings > Customize buttons: lay out the quick buttons on a full-screen picture of the
## battlefield. Drag a button anywhere; tap a name in the list to add or remove it; Reset
## puts the starting five back (GROUND, AIR, ARMY, BUILDINGS, BASE on the left edge). Every change is saved at
## once (Prefs "quick_buttons") and a running match rebuilds its buttons to match.

var area: Rect2                  # the safe area, where the HUD lives
var race: String = "ambron"
var entries: Array = []          # the layout being edited
var previews: Dictionary = {}    # id -> Button
var toggles: Dictionary = {}     # id -> Button in the list
var palette: PanelContainer
var drag_id: String = ""
var drag_off: Vector2 = Vector2.ZERO


## The fixed panels of the battlefield screen, to show around the buttons (and to keep new
## buttons off them). Mirrors the offsets in hud.gd.
static func zones(a: Rect2) -> Array:
	return [
		["RESOURCES", Rect2(a.position + Vector2(232, 6), Vector2(600, 46))],
		["MENU", Rect2(Vector2(a.end.x - 296, a.position.y + 8), Vector2(68, 52))],
		["MINIMAP", Rect2(Vector2(a.end.x - 216, a.position.y + 8), Vector2(208, 208))],
		["SELECTION", Rect2(Vector2(a.position.x + 120, a.end.y - 150), Vector2(380, 142))],
		["COMMANDS", Rect2(Vector2(a.end.x - 514, a.end.y - 200), Vector2(506, 192))],
	]


func _ready() -> void:
	name = "QuickButtonsEditor"
	top_level = true
	mouse_filter = Control.MOUSE_FILTER_STOP
	theme = UiKit.make_theme()
	var vr := get_viewport().get_visible_rect()
	position = vr.position
	size = vr.size
	area = UiKit.safe_rect(get_viewport())
	race = String(Prefs.get_v("race"))
	if not (race in ["ambron", "void"]):
		race = "ambron"
	var bg := ColorRect.new()
	bg.color = Color(0.025, 0.03, 0.05, 0.96)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)
	for z in zones(area):
		var p := Panel.new()
		p.mouse_filter = Control.MOUSE_FILTER_IGNORE
		p.add_theme_stylebox_override("panel", UiKit.box(Color(1, 1, 1, 0.035), Color(1, 1, 1, 0.14), 10, 1))
		p.position = (z[1] as Rect2).position
		p.size = (z[1] as Rect2).size
		add_child(p)
		var l := UiKit.head(z[0], 12, Color(UiKit.DIM, 0.6))
		l.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		p.add_child(l)
	entries = QuickButtons.layout().duplicate(true)
	for e in entries:
		_add_preview(e)
	_palette()


func _palette() -> void:
	palette = PanelContainer.new()
	palette.name = "List"
	palette.add_theme_stylebox_override("panel", UiKit.solid_panel(10))
	add_child(palette)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	palette.add_child(v)
	v.add_child(UiKit.head("QUICK BUTTONS", 20, UiKit.GOLD))
	var hint := UiKit.label("Drag a button anywhere on the screen. Tap a name to add or remove it.", 14, UiKit.DIM)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.custom_minimum_size = Vector2(540, 0)
	v.add_child(hint)
	var g := GridContainer.new()
	g.columns = 3
	g.add_theme_constant_override("h_separation", 6)
	g.add_theme_constant_override("v_separation", 6)
	v.add_child(g)
	for id in QuickButtons.ids():
		var sp := QuickButtons.spec(id, race)
		if sp.is_empty():
			continue
		var t := Button.new()
		t.name = id.replace(":", "_")
		t.toggle_mode = true
		t.text = String(sp["title"])
		t.custom_minimum_size = Vector2(176, 38)
		t.focus_mode = Control.FOCUS_NONE
		t.add_theme_font_size_override("font_size", 14)
		t.button_pressed = previews.has(id)
		t.toggled.connect(_toggle.bind(id))
		g.add_child(t)
		toggles[id] = t
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 14)
	v.add_child(row)
	var rb := Button.new()
	rb.text = "Reset"
	rb.name = "Reset"
	rb.custom_minimum_size = Vector2(160, 52)
	rb.focus_mode = Control.FOCUS_NONE
	rb.pressed.connect(reset)
	row.add_child(rb)
	var db := Button.new()
	db.text = "Done"
	db.name = "Done"
	db.custom_minimum_size = Vector2(160, 52)
	db.focus_mode = Control.FOCUS_NONE
	db.pressed.connect(func():
		Sfx.play("click")
		queue_free())
	row.add_child(db)
	# in the middle of the screen, a little high: the thumb corners stay clear
	var ms := palette.get_combined_minimum_size()
	palette.position = (area.get_center() - ms * 0.5 - Vector2(0, 30)).round()


func _add_preview(e: Dictionary) -> void:
	var id: String = e["id"]
	var sp := QuickButtons.spec(id, race)
	if sp.is_empty() or previews.has(id):
		return
	var b := QuickButtons.make_button(sp)
	b.name = "Btn_" + id.replace(":", "_")
	b.position = QuickButtons.rect_of(e, area).position
	b.gui_input.connect(_on_btn_input.bind(id))
	add_child(b)
	previews[id] = b


## A press on a button picks it up; the finger (or mouse) then carries it in _input.
func _on_btn_input(ev: InputEvent, id: String) -> void:
	var b: Button = previews.get(id)
	if b == null or drag_id != "":
		return
	if ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT and ev.pressed:
		drag_id = id
		drag_off = (ev as InputEventMouseButton).global_position - b.global_position
		move_child(b, get_child_count() - 1)
		palette.modulate.a = 0.25
		b.scale = Vector2(1.06, 1.06)


## Viewport coordinates throughout: this editor is top-level at the viewport's origin.
func _input(ev: InputEvent) -> void:
	if drag_id == "":
		return
	var b: Button = previews.get(drag_id)
	if b == null:
		drag_id = ""
		return
	if ev is InputEventScreenDrag or ev is InputEventMouseMotion:
		var p: Vector2 = ev.position - drag_off
		p.x = clampf(p.x, area.position.x, area.end.x - QuickButtons.SIZE.x)
		p.y = clampf(p.y, area.position.y, area.end.y - QuickButtons.SIZE.y)
		b.global_position = p
	elif (ev is InputEventScreenTouch and not ev.pressed) or (ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT and not ev.pressed):
		var id := drag_id
		drag_id = ""
		palette.modulate.a = 1.0
		b.scale = Vector2.ONE
		b.position = (b.position / 4.0).round() * 4.0
		for i in entries.size():
			if entries[i]["id"] == id:
				entries[i] = QuickButtons.entry_at(id, b.position, area)
		_save()
		Sfx.play("click", 1.1, -8.0)


func _toggle(on: bool, id: String) -> void:
	Sfx.play("click")
	if on and not previews.has(id):
		var avoid: Array = []
		for z in zones(area):
			avoid.append(z[1])
		avoid.append(palette.get_global_rect())
		var e := QuickButtons.entry_at(id, QuickButtons.free_spot(entries, area, avoid), area)
		entries.append(e)
		_add_preview(e)
	elif not on and previews.has(id):
		previews[id].queue_free()
		previews.erase(id)
		for i in range(entries.size() - 1, -1, -1):
			if entries[i]["id"] == id:
				entries.remove_at(i)
	_save()


func _save() -> void:
	var out: Array = entries.duplicate(true)
	if out.is_empty():
		out = [{"id": "_none"}]     # "no buttons" on purpose, not "never set"
	Prefs.set_v("quick_buttons", out)


func reset() -> void:
	Sfx.play("click")
	for id in previews:
		previews[id].queue_free()
	previews.clear()
	Prefs.set_v("quick_buttons", [])
	entries = QuickButtons.default_layout()
	for e in entries:
		_add_preview(e)
	for id in toggles:
		(toggles[id] as Button).set_pressed_no_signal(previews.has(id))
	move_child(palette, get_child_count() - 1)
