class_name UiKit
extends RefCounted
## Shared look for the interface: dark glass panels with cut corners and a
## lit top edge in the race's accent colour, chunky icon buttons for touch,
## Chakra Petch for text and Orbitron for titles and numbers (both OFL, see
## assets/fonts).

const BG := Color(0.05, 0.06, 0.09, 0.86)
const BG_HI := Color(0.1, 0.13, 0.19, 0.94)
const EDGE := Color(0.42, 0.5, 0.64, 0.5)
const GOLD := Color(1.0, 0.8, 0.3)
const SLIME := Color(0.72, 0.5, 1.0)
const TEXT := Color(0.92, 0.94, 0.98)
const DIM := Color(0.6, 0.64, 0.72)
const GOOD := Color(0.35, 1.0, 0.5)
const BAD := Color(1.0, 0.35, 0.3)

const FONT_BODY := "res://assets/fonts/ChakraPetch-SemiBold.ttf"
const FONT_BOLD := "res://assets/fonts/ChakraPetch-Bold.ttf"
const FONT_HEAD := "res://assets/fonts/Orbitron-Variable.ttf"

static var icon_cache: Dictionary = {}
static var theme: Theme
static var accent: Color = Color(0.37, 0.89, 1.0)
static var font_body: Font
static var font_bold: Font
static var font_head: Font


## Accent colour of a race: Ambron cyan, Void acid green.
static func set_race(race: String) -> void:
	var a: Color = Defs.RACE_INFO.get(race, {}).get("accent", Color(0.37, 0.89, 1.0))
	if a != accent:
		accent = a
		theme = null


static func fonts() -> void:
	if font_body:
		return
	font_body = load(FONT_BODY)
	font_bold = load(FONT_BOLD)
	var fv := FontVariation.new()
	fv.base_font = load(FONT_HEAD)
	var ts := TextServerManager.get_primary_interface()
	fv.variation_opentype = {ts.name_to_tag("wght"): 700}
	fv.spacing_glyph = 1
	font_head = fv


## A panel or button box: cut corners, thin edge, a brighter top edge.
static func box(col: Color, edge: Color = EDGE, r: int = 10, bw: int = 2, top: Color = Color(0, 0, 0, 0)) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = col
	s.border_color = edge
	s.set_border_width_all(bw)
	s.set_corner_radius_all(r)
	s.corner_detail = 1          # straight chamfers instead of rounded corners
	s.anti_aliasing = true
	s.content_margin_left = 8
	s.content_margin_right = 8
	s.content_margin_top = 6
	s.content_margin_bottom = 6
	if top.a > 0.0:
		s.border_color = top
		s.border_width_top = bw + 1
		s.border_width_left = bw
		s.border_width_right = bw
		s.border_width_bottom = bw
		s.shadow_color = Color(top.r, top.g, top.b, 0.12)
		s.shadow_size = 6
	return s


## A panel with the accent edge along its top.
static func panel_box(r: int = 12) -> StyleBoxFlat:
	var s := box(BG, EDGE, r, 1)
	s.border_width_top = 3
	s.border_color = Color(accent.r, accent.g, accent.b, 0.75)
	s.shadow_color = Color(0, 0, 0, 0.45)
	s.shadow_size = 8
	s.shadow_offset = Vector2(0, 3)
	return s


static func make_theme() -> Theme:
	if theme:
		return theme
	fonts()
	theme = Theme.new()
	theme.default_font = font_body
	theme.default_font_size = 18
	var lit := Color(accent.r, accent.g, accent.b, 0.95)
	theme.set_stylebox("normal", "Button", box(Color(0.07, 0.085, 0.12, 0.9), Color(0.5, 0.58, 0.72, 0.45), 10, 2))
	theme.set_stylebox("hover", "Button", box(BG_HI, Color(accent.r, accent.g, accent.b, 0.7), 10, 2))
	theme.set_stylebox("pressed", "Button", box(Color(accent.r * 0.25, accent.g * 0.25, accent.b * 0.3, 0.96), lit, 10, 2, lit))
	theme.set_stylebox("disabled", "Button", box(Color(0.04, 0.04, 0.06, 0.7), Color(0.3, 0.3, 0.35, 0.4), 10, 2))
	theme.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	theme.set_color("font_color", "Button", TEXT)
	theme.set_color("font_hover_color", "Button", Color.WHITE)
	theme.set_color("font_pressed_color", "Button", Color.WHITE)
	theme.set_color("font_disabled_color", "Button", Color(0.45, 0.47, 0.52))
	theme.set_color("icon_normal_color", "Button", TEXT)
	theme.set_font("font", "Button", font_bold)
	theme.set_stylebox("panel", "PanelContainer", panel_box())
	theme.set_stylebox("panel", "Panel", panel_box())
	theme.set_color("font_color", "Label", TEXT)
	theme.set_color("font_outline_color", "Label", Color(0, 0, 0, 0.85))
	theme.set_constant("outline_size", "Label", 4)
	theme.set_color("font_outline_color", "Button", Color(0, 0, 0, 0.7))
	theme.set_constant("outline_size", "Button", 3)
	return theme


## An icon by id: unit and building portraits from assets/icons, interface
## glyphs ("ui:attack") from assets/ui.
static func icon(id: String) -> Texture2D:
	if icon_cache.has(id):
		return icon_cache[id]
	var path := "res://assets/icons/%s.png" % id
	if id.begins_with("ui:"):
		path = "res://assets/ui/%s.svg" % id.substr(3)
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


## A label in the title face (Orbitron).
static func head(text: String, size: int = 18, col: Color = TEXT) -> Label:
	fonts()
	var l := label(text, size, col)
	l.add_theme_font_override("font", font_head)
	return l


static func tex_rect(tex: Texture2D, sz: Vector2, tint: Color = Color.WHITE) -> TextureRect:
	var tr := TextureRect.new()
	tr.texture = tex
	tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	tr.custom_minimum_size = sz
	tr.modulate = tint
	tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return tr


## A small icon and number, for costs and the resource bar.
static func amount(icon_id: String, n: String, col: Color, size: int = 13, isz: float = 14.0) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.add_theme_constant_override("separation", 2)
	var tex := icon(icon_id)
	if tex:
		h.add_child(tex_rect(tex, Vector2(isz, isz)))
	var l := head(n, size, col)
	l.name = "N"
	h.add_child(l)
	return h


## A big square touch button: an icon, a title and an optional cost line.
static func card_button(title: String, icon_id: String, cost: Array, hotkey: String = "") -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(92, 86)
	b.focus_mode = Control.FOCUS_NONE
	b.clip_contents = true
	var v := VBoxContainer.new()
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.add_theme_constant_override("separation", 1)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	b.add_child(v)
	var tex := icon(icon_id) if icon_id != "" else null
	if tex:
		var glyph := icon_id.begins_with("ui:")
		var tr := tex_rect(tex, Vector2(80, 34 if glyph else 44), accent.lerp(Color.WHITE, 0.35) if glyph else Color.WHITE)
		tr.name = "Icon"
		v.add_child(tr)
	var t := label(title, 13 if tex else 16)
	t.add_theme_font_override("font", font_bold)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.name = "Title"
	v.add_child(t)
	if cost.size() >= 2 and (int(cost[0]) > 0 or int(cost[1]) > 0):
		var h := HBoxContainer.new()
		h.alignment = BoxContainer.ALIGNMENT_CENTER
		h.mouse_filter = Control.MOUSE_FILTER_IGNORE
		h.add_theme_constant_override("separation", 6)
		h.name = "Cost"
		var m := amount("crystal_a", str(cost[0]), GOLD, 11, 13.0)
		m.name = "M"
		h.add_child(m)
		if int(cost[1]) > 0:
			var s := amount("slime_pile", str(cost[1]), SLIME, 11, 13.0)
			s.name = "S"
			h.add_child(s)
		v.add_child(h)
	if hotkey != "":
		b.tooltip_text = hotkey
	return b


static func fmt_time(t: float) -> String:
	var s := int(t)
	return "%02d:%02d" % [s / 60, s % 60]
