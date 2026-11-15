class_name QuickButtons
extends RefCounted
## The quick buttons on the battlefield: which ones show and where. The player picks and
## places them in Settings > Customize buttons (QuickButtonsEditor); they start on the left
## edge, where the left thumb rests (see default_layout).
##
## A layout is an Array of {id, ax, ay, x, y}: the button's top-left corner is (x, y) pixels
## from the screen corner (ax, ay), each 0 or 1, inside the phone's safe area. Anchoring to
## the nearest corner keeps a button by the same edge on any screen shape.
##
## Ids: "base", "buildings", "army" (tap and hold as before), "ground", "air", "workers",
## "idle", "unit:<slot>" (every unit of that type) and "bld:<slot>" (every finished
## building of that type, camera jumps there).

const SIZE := Vector2(100, 72)
const GAP := 8.0
const MARGIN := 8.0
const UNIT_SLOTS := ["infantry", "raider", "heavy", "vehicle_flame", "vehicle_missile", "air_light", "air_heavy", "special"]
const BUILDING_SLOTS := ["barracks", "factory", "airfield", "special", "tower"]


## Every button the player can place, in the editor's order.
static func ids() -> Array:
	var out := ["base", "buildings", "army", "ground", "air", "workers", "idle"]
	for s in UNIT_SLOTS:
		out.append("unit:" + s)
	for s in BUILDING_SLOTS:
		out.append("bld:" + s)
	return out


## What a button shows and does for a race: {title, icon, kind}. kind is a GroupMenu group
## ("ground", "type:<unit id>", "btype:<building id>") or "" for base, buildings and army.
static func spec(id: String, race: String) -> Dictionary:
	match id:
		"base":
			return {"title": "BASE", "icon": "ui:base", "kind": ""}
		"buildings":
			return {"title": "BUILDINGS", "icon": "ui:build", "kind": ""}
		"army":
			return {"title": "ARMY", "icon": "ui:army", "kind": ""}
		"ground":
			return {"title": "GROUND", "icon": Defs.unit_id(race, "infantry"), "kind": "ground"}
		"air":
			return {"title": "AIR", "icon": Defs.unit_id(race, "air_light"), "kind": "air"}
		"workers":
			return {"title": "WORKERS", "icon": "ui:worker", "kind": "workers"}
		"idle":
			return {"title": "IDLE", "icon": "ui:idle", "kind": "idle"}
	if id.begins_with("unit:"):
		var uid := Defs.unit_id(race, id.substr(5))
		if Defs.units.has(uid):
			return {"title": String(Defs.units[uid]["name"]).to_upper(), "icon": uid, "kind": "type:" + uid}
	if id.begins_with("bld:"):
		var bid := Defs.building_id(race, id.substr(4))
		if Defs.buildings.has(bid):
			return {"title": String(Defs.buildings[bid]["name"]).to_upper(), "icon": bid, "kind": "btype:" + bid}
	return {}


## The layout a new player starts with: Alex's own, from his phone (2026-11-15). On the left
## edge, where the thumb rests: GROUND and AIR side by side, ARMY and BUILDINGS below them,
## and BASE at the bottom, just above the selection panel's row.
static func default_layout() -> Array:
	return [
		{"id": "base", "ax": 0, "ay": 1, "x": 0.0, "y": -148.0},
		{"id": "buildings", "ax": 0, "ay": 1, "x": 124.0, "y": -244.0},
		{"id": "army", "ax": 0, "ay": 1, "x": 0.0, "y": -244.0},
		{"id": "ground", "ax": 0, "ay": 0, "x": 0.0, "y": 296.0},
		{"id": "air", "ax": 0, "ay": 0, "x": 124.0, "y": 296.0},
	]


## The saved layout, or the default when there is none.
static func layout() -> Array:
	var saved = Prefs.get_v("quick_buttons")
	var out: Array = []
	var known := ids()
	if saved is Array:
		for e in saved:
			if e is Dictionary and known.has(String(e.get("id", ""))) and not _has(out, String(e["id"])):
				out.append({"id": String(e["id"]), "ax": int(e.get("ax", 0)), "ay": int(e.get("ay", 1)), "x": float(e.get("x", MARGIN)), "y": float(e.get("y", -SIZE.y))})
	if out.is_empty() and (not (saved is Array) or (saved as Array).is_empty()):
		return default_layout()
	return out


static func _has(list: Array, id: String) -> bool:
	for e in list:
		if e["id"] == id:
			return true
	return false


## Where a layout entry sits inside `area` (the safe area), kept fully on screen.
static func rect_of(e: Dictionary, area: Rect2) -> Rect2:
	var corner := area.position + Vector2(float(e["ax"]) * area.size.x, float(e["ay"]) * area.size.y)
	var p := corner + Vector2(float(e["x"]), float(e["y"]))
	p.x = clampf(p.x, area.position.x, area.end.x - SIZE.x)
	p.y = clampf(p.y, area.position.y, area.end.y - SIZE.y)
	return Rect2(p, SIZE)


## A layout entry for a button whose top-left is at `top_left`, anchored to the nearest corner.
static func entry_at(id: String, top_left: Vector2, area: Rect2) -> Dictionary:
	var c := top_left + SIZE * 0.5
	var ax := 0 if c.x < area.get_center().x else 1
	var ay := 0 if c.y < area.get_center().y else 1
	var corner := area.position + Vector2(ax * area.size.x, ay * area.size.y)
	var off := (top_left - corner).round()
	return {"id": id, "ax": ax, "ay": ay, "x": off.x, "y": off.y}


## A free place for a new button: up the left edge from the bottom-left corner first, then
## the next columns, skipping other buttons and the fixed panels in `avoid`.
static func free_spot(list: Array, area: Rect2, avoid: Array) -> Vector2:
	var taken: Array = avoid.duplicate()
	for e in list:
		taken.append(rect_of(e, area))
	for col in 6:
		for row in 7:
			var p := Vector2(area.position.x + MARGIN + col * (SIZE.x + GAP), area.end.y - MARGIN - SIZE.y - row * (SIZE.y + GAP))
			var r := Rect2(p, SIZE)
			if p.y < area.position.y + 60.0 or r.end.x > area.end.x:
				continue
			var clear := true
			for t in taken:
				if (t as Rect2).grow(-1).intersects(r):
					clear = false
					break
			if clear:
				return p
	return area.get_center() - SIZE * 0.5


## The button itself: icon over title, the same look in the game and in the editor.
static func make_button(s: Dictionary) -> Button:
	var b := Button.new()
	b.custom_minimum_size = SIZE
	b.size = SIZE
	b.focus_mode = Control.FOCUS_NONE
	var col := VBoxContainer.new()
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 2)
	b.add_child(col)
	var icon_id: String = s["icon"]
	var glyph := icon_id.begins_with("ui:")
	var tex := UiKit.icon(icon_id)
	if tex:
		col.add_child(UiKit.tex_rect(tex, Vector2(70, 32 if glyph else 36), UiKit.accent.lerp(Color.WHITE, 0.35) if glyph else Color.WHITE))
	var title: String = s["title"]
	var t := UiKit.head(title, 12 if title.length() <= 7 else (10 if title.length() <= 10 else 9), UiKit.TEXT)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.clip_text = true
	t.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	t.custom_minimum_size = Vector2(SIZE.x - 8, 0)
	t.name = "Title"
	col.add_child(t)
	return b
