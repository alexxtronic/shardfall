class_name UiKit
extends RefCounted
## Shared look for the interface: dark glass panels, chunky touch buttons.

const BG := Color(0.06, 0.07, 0.1, 0.82)
const BG_HI := Color(0.13, 0.16, 0.22, 0.92)
const EDGE := Color(0.45, 0.55, 0.7, 0.55)
const GOLD := Color(1.0, 0.8, 0.3)
const SLIME := Color(0.72, 0.5, 1.0)
const TEXT := Color(0.92, 0.94, 0.98)
const DIM := Color(0.6, 0.64, 0.72)
const GOOD := Color(0.35, 1.0, 0.5)
const BAD := Color(1.0, 0.35, 0.3)

static var icon_cache: Dictionary = {}
static var theme: Theme


static func box(col: Color, edge: Color = EDGE, r: int = 12, bw: int = 2) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = col
	s.border_color = edge
	s.set_border_width_all(bw)
	s.set_corner_radius_all(r)
	s.content_margin_left = 8
	s.content_margin_right = 8
	s.content_margin_top = 6
	s.content_margin_bottom = 6
	return s


static func make_theme() -> Theme:
	if theme:
		return theme
	theme = Theme.new()
	theme.default_font_size = 18
	theme.set_stylebox("normal", "Button", box(BG))
	theme.set_stylebox("hover", "Button", box(BG_HI, Color(0.6, 0.75, 1.0, 0.8)))
	theme.set_stylebox("pressed", "Button", box(Color(0.2, 0.3, 0.45, 0.95), Color(0.7, 0.9, 1.0)))
	theme.set_stylebox("disabled", "Button", box(Color(0.05, 0.05, 0.07, 0.7), Color(0.3, 0.3, 0.35, 0.5)))
	theme.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	theme.set_color("font_color", "Button", TEXT)
	theme.set_color("font_disabled_color", "Button", Color(0.45, 0.47, 0.52))
	theme.set_stylebox("panel", "PanelContainer", box(BG))
	theme.set_stylebox("panel", "Panel", box(BG))
	theme.set_color("font_color", "Label", TEXT)
	theme.set_color("font_outline_color", "Label", Color(0, 0, 0, 0.85))
	theme.set_constant("outline_size", "Label", 4)
	return theme


static func icon(id: String) -> Texture2D:
	if icon_cache.has(id):
		return icon_cache[id]
	var path := "res://assets/icons/%s.png" % id
	var t: Texture2D = null
	if ResourceLoader.exists(path):
		t = load(path)
	icon_cache[id] = t
	return t


static func label(text: String, size: int = 18, col: Color = TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## A big square touch button with an icon, a title and an optional cost line.
static func card_button(title: String, icon_id: String, cost: Array, hotkey: String = "") -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(92, 86)
	b.focus_mode = Control.FOCUS_NONE
	b.clip_contents = true
	var v := VBoxContainer.new()
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.add_theme_constant_override("separation", 0)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	b.add_child(v)
	var tex := icon(icon_id) if icon_id != "" else null
	if tex:
		var tr := TextureRect.new()
		tr.texture = tex
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		tr.custom_minimum_size = Vector2(80, 44)
		tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
		tr.name = "Icon"
		v.add_child(tr)
	var t := label(title, 14 if tex else 17)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.name = "Title"
	v.add_child(t)
	if cost.size() >= 2 and (int(cost[0]) > 0 or int(cost[1]) > 0):
		var h := HBoxContainer.new()
		h.alignment = BoxContainer.ALIGNMENT_CENTER
		h.mouse_filter = Control.MOUSE_FILTER_IGNORE
		h.add_theme_constant_override("separation", 6)
		h.name = "Cost"
		var m := label(str(cost[0]), 13, GOLD)
		m.name = "M"
		h.add_child(m)
		if int(cost[1]) > 0:
			var s := label(str(cost[1]), 13, SLIME)
			s.name = "S"
			h.add_child(s)
		v.add_child(h)
	if hotkey != "":
		b.tooltip_text = hotkey
	return b


static func fmt_time(t: float) -> String:
	var s := int(t)
	return "%02d:%02d" % [s / 60, s % 60]
