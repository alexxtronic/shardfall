class_name GroupMenu
extends PanelContainer
## The menu that opens when you hold ARMY or BUILDINGS: every group of your own things you
## can grab at once. Slide onto a group and let go to select it (or, after a plain hold, tap
## one).
##   ARMY ("units"): all fighters, ground, air, workers, idle workers, then one entry per
##   unit type you have. Empty groups show greyed out and can't be picked.
##   BUILDINGS ("buildings"): one entry per finished building type that trains units, so
##   you can select every Assembly Bay at once and train from all of them. Supply
##   buildings, extractors and towers are left out.

signal picked(kind: String)

const CATEGORIES := [
	["army", "ALL ARMY"],
	["ground", "GROUND"],
	["air", "AIR"],
	["workers", "WORKERS"],
	["idle", "IDLE WORKERS"],
]

var world: World
var pid: int = 0
var mode: String = "units"
var opts: Array = []          # [Button, kind, count]
var hot: String = ""
var cold_box: StyleBoxFlat
var hot_box: StyleBoxFlat


## Who belongs to a group: "army", "ground", "air", "workers", "idle", "type:<unit id>"
## or "btype:<building id>" (finished buildings only). Workers tucked inside an
## extractor stay out.
static func members(w: World, p: int, kind: String) -> Array:
	var out: Array = []
	if kind.begins_with("btype:"):
		var bid := kind.substr(6)
		for b in w.buildings:
			if b.owner_id == p and not b.dead and b.built and b.def_id == bid:
				out.append(b)
		return out
	for u in w.units:
		if u.owner_id != p or u.dead or u.hidden_inside:
			continue
		var ok := false
		match kind:
			"army":
				ok = not u.is_worker
			"ground":
				ok = not u.is_worker and not u.is_air
			"air":
				ok = u.is_air
			"workers":
				ok = u.is_worker
			"idle":
				ok = u.is_worker and u.order == Unit.O.IDLE
			_:
				ok = kind.begins_with("type:") and u.def_id == kind.substr(5)
		if ok:
			out.append(u)
	return out


## How a group reads in a message: "12 Lancers", "3 ground units", "2 Assembly Bays".
static func describe(kind: String, n: int) -> String:
	if kind.begins_with("type:") or kind.begins_with("btype:"):
		var id := kind.get_slice(":", 1)
		var nm := String((Defs.buildings[id] if kind.begins_with("btype:") else Defs.units[id])["name"])
		return "%d %s" % [n, nm if n == 1 else nm + "s"]
	var noun: String = {"army": "fighter", "ground": "ground unit", "air": "flyer", "workers": "worker", "idle": "idle worker"}.get(kind, "unit")
	return "%d %s%s" % [n, noun, "" if n == 1 else "s"]


## Where to look at a group spread over the map: the middle of its biggest cluster, so a
## pick never lands the camera on empty ground between two bases.
static func cluster_center(list: Array, radius: float = 22.0) -> Vector2:
	var best := Vector2.ZERO
	var best_n := -1
	for a in list:
		var n := 0
		var c := Vector2.ZERO
		for b in list:
			if a.p.distance_to(b.p) <= radius:
				n += 1
				c += b.p
		if n > best_n:
			best_n = n
			best = c / n
	return best


func build(w: World, p: int, m: String = "units") -> void:
	world = w
	pid = p
	mode = m
	name = "GroupMenu"
	mouse_filter = Control.MOUSE_FILTER_STOP
	add_theme_stylebox_override("panel", UiKit.solid_panel(10))
	var a := UiKit.accent
	cold_box = UiKit.box(Color(0.07, 0.09, 0.13, 0.95), Color(1, 1, 1, 0.08), 8, 1)
	hot_box = UiKit.box(Color(a.r * 0.32, a.g * 0.32, a.b * 0.38, 0.98), a, 8, 2)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(v)
	var head := UiKit.head("SLIDE TO A GROUP, THEN LET GO" if mode == "units" else "SLIDE TO A BUILDING TYPE, THEN LET GO", 12, UiKit.GOLD)
	v.add_child(head)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 10)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(h)
	var race: String = world.players[pid].race
	if mode == "buildings":
		var kinds: Array = []
		# only buildings that train units: selecting those is for mass production
		for bid in Defs.race_building_list(race):
			var have := members(world, pid, "btype:" + bid)
			if have.size() > 0 and (have[0] as Building).produces().size() > 0:
				kinds.append(bid)
		var g := _grid(kinds.size())
		h.add_child(g)
		for bid in kinds:
			g.add_child(_option("btype:" + bid, String(Defs.buildings[bid]["name"]).to_upper(), bid))
	else:
		var cats := VBoxContainer.new()
		cats.add_theme_constant_override("separation", 6)
		cats.mouse_filter = Control.MOUSE_FILTER_IGNORE
		h.add_child(cats)
		var cat_icons := {
			"army": "ui:army", "ground": Defs.unit_id(race, "infantry"), "air": Defs.unit_id(race, "air_light"),
			"workers": "ui:worker", "idle": "ui:idle",
		}
		for c in CATEGORIES:
			cats.add_child(_option(c[0], c[1], cat_icons[c[0]]))
		# one entry per unit type you have, in tech order
		var types: Array = []
		for slot in Defs.UNIT_SLOTS:
			if slot == "worker":
				continue
			var id := Defs.unit_id(race, slot)
			if members(world, pid, "type:" + id).size() > 0:
				types.append(id)
		if types.size() > 0:
			var sep := VSeparator.new()
			sep.mouse_filter = Control.MOUSE_FILTER_IGNORE
			h.add_child(sep)
			var g := _grid(types.size())
			h.add_child(g)
			for id in types:
				g.add_child(_option("type:" + id, String(Defs.units[id]["name"]).to_upper(), id))
	# pop in
	modulate.a = 0.0
	scale = Vector2(0.94, 0.94)
	var tw := create_tween().set_parallel()
	tw.tween_property(self, "modulate:a", 1.0, 0.1)
	tw.tween_property(self, "scale", Vector2.ONE, 0.12).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func _grid(n: int) -> GridContainer:
	var g := GridContainer.new()
	g.columns = 1 if n <= 5 else 2
	g.add_theme_constant_override("h_separation", 6)
	g.add_theme_constant_override("v_separation", 6)
	g.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return g


func _option(kind: String, title: String, icon_id: String) -> Button:
	var n := members(world, pid, kind).size()
	var b := Button.new()
	b.name = kind.replace(":", "_")
	b.custom_minimum_size = Vector2(196, 54)
	b.focus_mode = Control.FOCUS_NONE
	for st in ["normal", "hover", "pressed", "disabled"]:
		b.add_theme_stylebox_override(st, cold_box)
	b.disabled = n == 0
	if n == 0:
		b.modulate.a = 0.4
	var h := HBoxContainer.new()
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 8
	h.offset_right = -8
	h.add_theme_constant_override("separation", 8)
	b.add_child(h)
	var glyph := icon_id.begins_with("ui:")
	var tex := UiKit.icon(icon_id)
	if tex:
		var tr := UiKit.tex_rect(tex, Vector2(34, 34), UiKit.accent.lerp(Color.WHITE, 0.35) if glyph else Color.WHITE)
		tr.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		h.add_child(tr)
	var col := VBoxContainer.new()
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 0)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(col)
	var t := UiKit.head(title, 12 if title.length() <= 12 else 10, UiKit.TEXT)
	t.clip_text = true
	t.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	col.add_child(t)
	col.add_child(UiKit.label(str(n), 15, UiKit.GOLD if n > 0 else UiKit.DIM))
	b.pressed.connect(func(): picked.emit(kind))
	opts.append([b, kind, n])
	return b


## The group under a screen point (lit up), or "" for none.
func hot_at(pos: Vector2) -> String:
	var k := ""
	for o in opts:
		var b: Button = o[0]
		if int(o[2]) > 0 and b.get_global_rect().has_point(pos):
			k = o[1]
	if k != hot:
		hot = k
		for o in opts:
			var st := hot_box if o[1] == hot else cold_box
			for state in ["normal", "hover", "pressed"]:
				(o[0] as Button).add_theme_stylebox_override(state, st)
			(o[0] as Button).scale = Vector2(1.04, 1.04) if o[1] == hot else Vector2.ONE
		if hot != "":
			Sfx.play("click", 1.25, -10.0)
	return hot


## An option's centre on screen (for tests and hints).
func option_center(kind: String) -> Vector2:
	for o in opts:
		if o[1] == kind:
			return (o[0] as Button).get_global_rect().get_center()
	return Vector2(-1, -1)
