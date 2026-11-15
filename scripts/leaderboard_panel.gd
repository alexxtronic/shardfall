class_name LeaderboardPanel
extends ColorRect
## The leaderboard overlay: your commander name (editable), rating and tier, then three tabs:
## the ladder (you among the AI rivals), your best score on each map, and recent games.

signal closed

var tab: String = "ladder"
var tab_btns: Dictionary = {}
var body: VBoxContainer
var name_edit: LineEdit
var summary: Label


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
	v.add_theme_constant_override("separation", 10)
	p.add_child(v)
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 14)
	v.add_child(top)
	var t := UiKit.head("LEADERBOARD", 30, UiKit.GOLD)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(t)
	top.add_child(UiKit.label("Commander", 17, UiKit.DIM))
	name_edit = LineEdit.new()
	name_edit.name = "NameEdit"
	name_edit.text = Profile.player_name()
	name_edit.max_length = Profile.NAME_MAX
	name_edit.custom_minimum_size = Vector2(260, 50)
	name_edit.add_theme_font_size_override("font_size", 20)
	name_edit.select_all_on_focus = true
	name_edit.text_submitted.connect(func(_t): _save_name(); name_edit.release_focus())
	name_edit.focus_exited.connect(_save_name)
	top.add_child(name_edit)
	summary = UiKit.label("", 17, UiKit.TEXT)
	summary.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(summary)
	var tabs := HBoxContainer.new()
	tabs.alignment = BoxContainer.ALIGNMENT_CENTER
	tabs.add_theme_constant_override("separation", 10)
	v.add_child(tabs)
	for spec in [["Ladder", "ladder"], ["Best scores", "best"], ["Recent games", "history"]]:
		var b := Button.new()
		b.text = spec[0]
		b.toggle_mode = true
		b.focus_mode = Control.FOCUS_NONE
		b.custom_minimum_size = Vector2(200, 50)
		var k: String = spec[1]
		b.pressed.connect(func(): _show(k))
		tabs.add_child(b)
		tab_btns[k] = b
	var sc := ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	v.add_child(sc)
	body = VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 4)
	sc.add_child(body)
	var done := Button.new()
	done.text = "Done"
	done.custom_minimum_size = Vector2(220, 58)
	done.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	done.focus_mode = Control.FOCUS_NONE
	done.pressed.connect(close)
	v.add_child(done)
	_show("ladder", false)


func _save_name() -> void:
	if name_edit.text.strip_edges() != Profile.player_name():
		Profile.set_player_name(name_edit.text)
		name_edit.text = Profile.player_name()
		_show(tab, false)


func _summary() -> void:
	var r := Profile.rating()
	var tr: Array = Profile.tier(r)
	var g := Profile.games()
	var wr := "%d%%" % roundi(100.0 * Profile.wins() / g) if g > 0 else "–"
	summary.text = "Rating %d  ·  %s  ·  Rank #%d of %d  ·  %d game%s, %s won" % [
		r, tr[0], Profile.rank(), Profile.RIVALS.size() + 1, g, "" if g == 1 else "s", wr]


func _show(k: String, sound: bool = true) -> void:
	tab = k
	for key in tab_btns:
		(tab_btns[key] as Button).button_pressed = key == k
	if sound:
		Sfx.play("click")
	_summary()
	for c in body.get_children():
		c.queue_free()
	match k:
		"ladder":
			_ladder()
		"best":
			_best()
		"history":
			_history()


func _row(cells: Array, widths: Array, hi: bool = false) -> PanelContainer:
	var pc := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(UiKit.accent.r * 0.3, UiKit.accent.g * 0.3, UiKit.accent.b * 0.35, 0.9) if hi else Color(1, 1, 1, 0.03)
	sb.border_color = Color(UiKit.accent.r, UiKit.accent.g, UiKit.accent.b, 0.8) if hi else Color(0, 0, 0, 0)
	sb.set_border_width_all(1 if hi else 0)
	sb.set_corner_radius_all(6)
	sb.content_margin_left = 12
	sb.content_margin_right = 12
	sb.content_margin_top = 3
	sb.content_margin_bottom = 3
	pc.add_theme_stylebox_override("panel", sb)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 10)
	pc.add_child(h)
	for i in cells.size():
		var c = cells[i]
		var node: Control = c if c is Control else UiKit.label(str(c), 18, UiKit.TEXT)
		node.custom_minimum_size.x = float(widths[i])
		if widths[i] == 0:
			node.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		h.add_child(node)
	return pc


func _ladder() -> void:
	var rows := Profile.ladder()
	for i in rows.size():
		var r: Dictionary = rows[i]
		var tr: Array = Profile.tier(int(r["rating"]))
		var nm := UiKit.label(String(r["name"]) + ("  (you)" if r["me"] else ""), 18, UiKit.GOLD if r["me"] else UiKit.TEXT)
		body.add_child(_row([UiKit.head("#%d" % (i + 1), 16, UiKit.DIM), nm, UiKit.label(tr[0], 17, tr[1]),
			UiKit.head(str(r["rating"]), 17, UiKit.TEXT)], [60, 0, 130, 80], r["me"]))
	var note := UiKit.label("The other commanders are AI rivals with fixed ratings. Beat harder bots to climb.", 14, UiKit.DIM)
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_child(note)


func _best() -> void:
	for id in Maps.LIST:
		var d: Dictionary = Maps.DEFS[id]
		var tr := TextureRect.new()
		tr.texture = Title._preview(id)
		tr.custom_minimum_size = Vector2(64, 64)
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		var b := Profile.best(id)
		body.add_child(_row([tr, UiKit.head(String(d["name"]).to_upper(), 18, d.get("accent", UiKit.TEXT)),
			UiKit.head(UiKit.fmt_int(b) if b > 0 else "–", 22, UiKit.GOLD if b > 0 else UiKit.DIM)], [64, 0, 140]))
	var note := UiKit.label("Score: 1,000 for a win (250 for a loss), plus damage dealt, resources gathered and a bonus for a quick win, times 0.6 / 0.8 / 1 / 1.5 for an easy / normal / hard / extreme bot.", 14, UiKit.DIM)
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_child(note)


func _history() -> void:
	var h := Profile.history()
	if h.is_empty():
		body.add_child(UiKit.label("No games yet. Play the bot and your results land here.", 18, UiKit.DIM))
		return
	for g in h:
		var won: bool = g.get("won", false)
		var d := int(g.get("delta", 0))
		var map_name: String = Maps.DEFS.get(String(g.get("map", "")), {}).get("name", "?")
		var who := "%s vs %s" % [String(g.get("race", "")).capitalize(), String(g.get("enemy", "")).capitalize()]
		body.add_child(_row([
			UiKit.head("WIN" if won else "LOSS", 16, UiKit.GOOD if won else UiKit.BAD),
			UiKit.label("%s · %s · %s bot" % [map_name, who, String(g.get("difficulty", "")).capitalize()], 16, UiKit.TEXT),
			UiKit.label(UiKit.fmt_time(float(g.get("time", 0))), 16, UiKit.DIM),
			UiKit.head(UiKit.fmt_int(int(g.get("score", 0))), 16, UiKit.GOLD),
			UiKit.head("%+d" % d, 16, UiKit.GOOD if d >= 0 else UiKit.BAD),
		], [64, 0, 60, 90, 56]))


func close() -> void:
	_save_name()
	Sfx.play("close")
	closed.emit()
	queue_free()
