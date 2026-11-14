class_name Hud
extends CanvasLayer
## The in-match interface, laid out for a phone held sideways:
## resources along the top, quick buttons down the left, the minimap bottom
## left, what's selected bottom centre, and the command card bottom right.

signal menu_action(a: String)

var world: World
var cmd: Commander
var rig: CameraRig
var pid: int = 0
var root: Control
var lbl_min: Label
var lbl_slime: Label
var lbl_supply: Label
var lbl_time: Label
var lbl_workers: Label
var minimap: Minimap
var overlay: Overlay
var sel_panel: PanelContainer
var sel_content: Control
var card: GridContainer
var card_panel: PanelContainer
var card_state: String = ""
var card_sig: String = ""
var msg_box: VBoxContainer
var place_bar: HBoxContainer
var menu: Control
var blockers: Array = []
var refresh_t: float = 0.0
var sel_sig: String = ""
var idle_btn: Button


func setup(w: World, c: Commander, r: CameraRig) -> void:
	world = w
	cmd = c
	rig = r
	pid = c.pid
	layer = 5
	root = Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	UiKit.set_race(world.players[pid].race)
	root.theme = UiKit.make_theme()
	add_child(root)
	overlay = Overlay.new()
	overlay.world = w
	overlay.rig = r
	overlay.cmd = c
	root.add_child(overlay)
	_top_bar()
	_left_buttons()
	_minimap()
	_selection_panel()
	_command_card()
	_messages()
	_place_bar()
	_menu()
	cmd.selection_changed.connect(_on_selection)
	cmd.mode_changed.connect(_on_mode)
	world.message.connect(show_message)
	world.alert.connect(func(at):
		minimap.ping(at)
		Sfx.play("alert")
		Sfx.combat()
		Sfx.announce("look_out"))
	world.building_destroyed.connect(func(b):
		if b.owner_id >= 0 and b.owner_id != pid and b.shown:
			Sfx.announce("objective_achieved" if b.slot == "main" else "target_destroyed"))
	world.unit_ready.connect(func(u): Sfx.play("ready", 1.0, -6.0))
	_on_selection()


func blocks(pos: Vector2) -> bool:
	for c in blockers:
		if is_instance_valid(c) and c.visible and c.is_visible_in_tree() and c.get_global_rect().has_point(pos):
			return true
	return false


# ---------------------------------------------------------------- layout

func _top_bar() -> void:
	var bar := PanelContainer.new()
	var sb := UiKit.panel_box(14)
	sb.content_margin_left = 18
	sb.content_margin_right = 18
	bar.add_theme_stylebox_override("panel", sb)
	bar.position = Vector2(232, 6)
	bar.size = Vector2(600, 46)
	bar.set_anchors_preset(Control.PRESET_TOP_LEFT)
	root.add_child(bar)
	blockers.append(bar)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 14)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	bar.add_child(h)
	lbl_min = _res_chip(h, "ui:crystal", UiKit.GOLD, Color.WHITE, 26.0)
	_divider(h)
	lbl_slime = _res_chip(h, "ui:slime", UiKit.SLIME, Color.WHITE, 26.0)
	_divider(h)
	lbl_supply = _res_chip(h, "ui:supply", UiKit.TEXT, UiKit.accent)
	_divider(h)
	lbl_workers = _res_chip(h, "ui:worker", UiKit.DIM, UiKit.DIM)
	_divider(h)
	lbl_time = _res_chip(h, "ui:clock", UiKit.DIM, UiKit.DIM)
	var mb := Button.new()
	mb.icon = UiKit.icon("ui:menu")
	mb.expand_icon = true
	mb.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mb.add_theme_constant_override("icon_max_width", 30)
	mb.custom_minimum_size = Vector2(64, 52)
	mb.focus_mode = Control.FOCUS_NONE
	mb.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	root.add_child(mb)
	mb.anchor_left = 1.0
	mb.anchor_right = 1.0
	mb.offset_left = -74
	mb.offset_right = -10
	mb.offset_top = 6
	mb.offset_bottom = 58
	mb.pressed.connect(toggle_menu)
	blockers.append(mb)


func _divider(parent: Control) -> void:
	var d := ColorRect.new()
	d.color = Color(1, 1, 1, 0.12)
	d.custom_minimum_size = Vector2(1, 26)
	d.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var c := CenterContainer.new()
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.add_child(d)
	parent.add_child(c)


func _res_chip(parent: Control, icon_id: String, col: Color, tint: Color, icon_size: float = 0.0) -> Label:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(h)
	var tex := UiKit.icon(icon_id)
	if tex:
		var sz := icon_size if icon_size > 0.0 else (28.0 if not icon_id.begins_with("ui:") else 22.0)
		var tr := UiKit.tex_rect(tex, Vector2(sz, sz), tint)
		var cc := CenterContainer.new()
		cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cc.add_child(tr)
		h.add_child(cc)
	var l := UiKit.head("0", 17, col)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(l)
	return l


func _left_buttons() -> void:
	var v := VBoxContainer.new()
	v.position = Vector2(10, 64)
	v.add_theme_constant_override("separation", 8)
	root.add_child(v)
	for spec in [["ARMY", "army", "ui:army"], ["IDLE", "idle", "ui:idle"], ["BASE", "base", "ui:base"], ["BUILD", "build_menu", "ui:build"]]:
		var b := Button.new()
		b.custom_minimum_size = Vector2(86, 70)
		b.focus_mode = Control.FOCUS_NONE
		var col := VBoxContainer.new()
		col.mouse_filter = Control.MOUSE_FILTER_IGNORE
		col.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		col.alignment = BoxContainer.ALIGNMENT_CENTER
		col.add_theme_constant_override("separation", 2)
		b.add_child(col)
		col.add_child(UiKit.tex_rect(UiKit.icon(spec[2]), Vector2(70, 32), UiKit.accent.lerp(Color.WHITE, 0.35)))
		var t := UiKit.head(spec[0], 12, UiKit.TEXT)
		t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		t.name = "Title"
		col.add_child(t)
		var a: String = spec[1]
		b.pressed.connect(func(): _left_action(a))
		v.add_child(b)
		blockers.append(b)
		if a == "idle":
			idle_btn = b
			# a count badge in the corner
			var badge := UiKit.head("", 12, Color(0.1, 0.07, 0.02))
			badge.name = "Badge"
			badge.add_theme_constant_override("outline_size", 0)
			var bb := PanelContainer.new()
			var st := UiKit.box(UiKit.GOLD, UiKit.GOLD, 6, 1)
			st.content_margin_left = 5
			st.content_margin_right = 5
			st.content_margin_top = 0
			st.content_margin_bottom = 0
			bb.add_theme_stylebox_override("panel", st)
			bb.add_child(badge)
			bb.position = Vector2(56, -6)
			bb.mouse_filter = Control.MOUSE_FILTER_IGNORE
			bb.name = "BadgeBox"
			bb.visible = false
			b.add_child(bb)


func _left_action(a: String) -> void:
	Sfx.play("click")
	if a == "build_menu":
		# build without selecting a worker first: the nearest one goes
		card_state = "build_free"
		card_sig = ""
		_refresh_card(true)
		return
	cmd.action(a)


func _minimap() -> void:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", UiKit.panel_box(10))
	p.anchor_top = 1.0
	p.anchor_bottom = 1.0
	p.offset_left = 8
	p.offset_right = 8 + 208
	p.offset_top = -216
	p.offset_bottom = -8
	root.add_child(p)
	minimap = Minimap.new()
	minimap.custom_minimum_size = Vector2(192, 192)
	p.add_child(minimap)
	minimap.setup(world, rig, cmd)
	blockers.append(p)


func _selection_panel() -> void:
	sel_panel = PanelContainer.new()
	sel_panel.anchor_top = 1.0
	sel_panel.anchor_bottom = 1.0
	sel_panel.anchor_left = 0.0
	sel_panel.offset_left = 224
	sel_panel.offset_right = 224 + 380
	sel_panel.offset_top = -150
	sel_panel.offset_bottom = -8
	root.add_child(sel_panel)
	blockers.append(sel_panel)
	sel_content = Control.new()
	sel_content.custom_minimum_size = Vector2(360, 128)
	sel_panel.add_child(sel_content)


func _command_card() -> void:
	card_panel = PanelContainer.new()
	card_panel.anchor_left = 1.0
	card_panel.anchor_right = 1.0
	card_panel.anchor_top = 1.0
	card_panel.anchor_bottom = 1.0
	# five columns fit a race's eight buildings plus Back in two rows; if a card ever holds
	# more, the panel grows up and left rather than off the bottom of the screen
	card_panel.offset_left = -514
	card_panel.offset_right = -8
	card_panel.offset_top = -200
	card_panel.offset_bottom = -8
	card_panel.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	card_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	root.add_child(card_panel)
	blockers.append(card_panel)
	card = GridContainer.new()
	card.columns = 5
	card.add_theme_constant_override("h_separation", 6)
	card.add_theme_constant_override("v_separation", 6)
	card_panel.add_child(card)


func _messages() -> void:
	msg_box = VBoxContainer.new()
	msg_box.anchor_left = 0.5
	msg_box.anchor_right = 0.5
	msg_box.offset_left = -300
	msg_box.offset_right = 300
	msg_box.offset_top = 62
	msg_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	msg_box.alignment = BoxContainer.ALIGNMENT_BEGIN
	msg_box.add_theme_constant_override("separation", 4)
	root.add_child(msg_box)


func _place_bar() -> void:
	place_bar = HBoxContainer.new()
	place_bar.anchor_left = 0.5
	place_bar.anchor_right = 0.5
	place_bar.anchor_top = 1.0
	place_bar.anchor_bottom = 1.0
	place_bar.offset_left = 120
	place_bar.offset_right = 360
	place_bar.offset_top = -270
	place_bar.offset_bottom = -200
	place_bar.add_theme_constant_override("separation", 16)
	root.add_child(place_bar)
	for spec in [["ui:confirm", "confirm", UiKit.GOOD], ["ui:cancel", "cancel", UiKit.BAD]]:
		var b := Button.new()
		b.icon = UiKit.icon(spec[0])
		b.expand_icon = true
		b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		b.add_theme_constant_override("icon_max_width", 36)
		b.add_theme_color_override("icon_normal_color", spec[2])
		b.add_theme_color_override("icon_hover_color", spec[2].lightened(0.3))
		b.add_theme_color_override("icon_pressed_color", Color.WHITE)
		b.custom_minimum_size = Vector2(96, 64)
		b.focus_mode = Control.FOCUS_NONE
		var a: String = spec[1]
		b.pressed.connect(func(): cmd.action(a))
		place_bar.add_child(b)
	place_bar.visible = false
	blockers.append(place_bar)


func _menu() -> void:
	menu = ColorRect.new()
	(menu as ColorRect).color = Color(0, 0, 0, 0.55)
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu.visible = false
	root.add_child(menu)
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.custom_minimum_size = Vector2(340, 0)
	p.offset_left = -170
	p.offset_right = 170
	p.offset_top = -205
	p.offset_bottom = 205
	menu.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	p.add_child(v)
	var t := UiKit.head("PAUSED", 28, UiKit.accent)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	for spec in [["Resume", "resume"], ["Speed: Normal", "speed"], ["Settings", "settings"], ["Restart", "restart"], ["Surrender", "surrender"], ["Quit to title", "quit"]]:
		var b := Button.new()
		b.text = spec[0]
		b.custom_minimum_size = Vector2(300, 56)
		b.focus_mode = Control.FOCUS_NONE
		var a: String = spec[1]
		b.name = a
		b.pressed.connect(func(): _menu_pick(a))
		v.add_child(b)
	blockers.append(menu)


func toggle_menu() -> void:
	menu.visible = not menu.visible
	world.running = not menu.visible
	Sfx.play("click")


func _menu_pick(a: String) -> void:
	Sfx.play("click")
	if a == "resume":
		toggle_menu()
		return
	if a == "speed":
		var b: Button = menu.find_child("speed", true, false)
		if world.speed_mult < 1.2:
			world.speed_mult = 1.4
			b.text = "Speed: Fast"
		else:
			world.speed_mult = 1.0
			b.text = "Speed: Normal"
		return
	if a == "settings":
		var sp := SettingsPanel.new()
		sp.name = "Settings"
		root.add_child(sp)
		blockers.append(sp)
		sp.closed.connect(func(): blockers.erase(sp))
		return
	menu.visible = false
	world.running = true
	menu_action.emit(a)


# ---------------------------------------------------------------- live updates

func _process(delta: float) -> void:
	if world == null:
		return
	var pl: PlayerState = world.players[pid]
	lbl_min.text = str(pl.minerals)
	lbl_slime.text = str(pl.slime)
	var used := world.supply_used(pid)
	var cap := world.supply_cap(pid)
	lbl_supply.text = "%d/%d" % [used, cap]
	lbl_supply.add_theme_color_override("font_color", UiKit.BAD if used >= cap and cap < Defs.SUPPLY_MAX else UiKit.TEXT)
	lbl_time.text = UiKit.fmt_time(world.time)
	var workers := 0
	var idle := 0
	for u in world.units:
		if u.owner_id == pid and u.is_worker and not u.dead:
			workers += 1
			if u.order == Unit.O.IDLE:
				idle += 1
	lbl_workers.text = str(workers)
	var bb: Control = idle_btn.get_node("BadgeBox")
	bb.visible = idle > 0
	(bb.get_node("Badge") as Label).text = str(idle)
	refresh_t += delta
	if refresh_t > 0.2:
		refresh_t = 0.0
		_refresh_card(false)
		_refresh_selection(false)
	# an empty command card (nothing of yours selected) is hidden so it doesn't cover the map
	card_panel.visible = card.get_child_count() > 0
	place_bar.visible = cmd.mode == Commander.M.PLACE


func _on_selection() -> void:
	if card_state == "build" and cmd.own_workers().is_empty():
		card_state = ""
	if card_state == "build_free":
		card_state = ""
	_refresh_card(true)
	_refresh_selection(true)


func _on_mode() -> void:
	_refresh_card(true)


func show_message(text: String, kind: String = "info") -> void:
	var col := UiKit.TEXT
	match kind:
		"error":
			col = Color(1.0, 0.55, 0.45)
		"alert":
			col = Color(1.0, 0.35, 0.3)
		"done":
			col = Color(0.5, 1.0, 0.6)
		"hint":
			col = Color(0.75, 0.88, 1.0)
	if kind == "done":
		Sfx.play("complete", 1.0, -8.0)
	# don't stack the same line twice
	for c in msg_box.get_children():
		if c.has_meta("text") and c.get_meta("text") == text:
			c.queue_free()
			msg_box.remove_child(c)
	var l := PanelContainer.new()
	l.set_meta("text", text)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var st := UiKit.box(Color(0.03, 0.04, 0.07, 0.72), Color(col.r, col.g, col.b, 0.0), 8, 0)
	st.border_width_left = 3
	st.border_color = Color(col.r, col.g, col.b, 0.9)
	st.content_margin_left = 14
	st.content_margin_right = 14
	st.content_margin_top = 3
	st.content_margin_bottom = 3
	l.add_theme_stylebox_override("panel", st)
	l.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var lt := UiKit.label(text, 18, col)
	lt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_child(lt)
	msg_box.add_child(l)
	while msg_box.get_child_count() > 4:
		msg_box.get_child(0).queue_free()
		msg_box.remove_child(msg_box.get_child(0))
	var tw := l.create_tween()
	tw.tween_interval(2.6)
	tw.tween_property(l, "modulate:a", 0.0, 0.6)
	tw.tween_callback(l.queue_free)


func haptic_hint(t: String) -> void:
	show_message(t, "hint")


# ---------------------------------------------------------------- command card

func _cmd_button(title: String, icon_id: String, cost: Array, a: String, enabled: bool = true) -> Button:
	var b := UiKit.card_button(title, icon_id, cost)
	b.disabled = not enabled
	b.pressed.connect(func(): _card_action(a))
	card.add_child(b)
	return b


func _card_action(a: String) -> void:
	if a == "open_build":
		card_state = "build"
		Sfx.play("click")
		_refresh_card(true)
		return
	if a == "back":
		card_state = ""
		Sfx.play("click")
		_refresh_card(true)
		return
	cmd.action(a)
	if a.begins_with("build:"):
		card_state = ""
	_refresh_card(true)


func _refresh_card(force: bool) -> void:
	var pl: PlayerState = world.players[pid]
	var sel := cmd.selection
	var sig := "%s|%d|%d|%d|%d" % [card_state, cmd.mode, sel.size(), pl.minerals / 25, pl.slime / 25]
	for e in sel:
		sig += ":%d" % e.eid
		if e is Building:
			sig += "b%d%d" % [int(e.built), e.queue.size()]
	sig += "|%d" % world.buildings.size()
	if not force and sig == card_sig:
		return
	card_sig = sig
	for c in card.get_children():
		c.queue_free()
		card.remove_child(c)
	if cmd.mode == Commander.M.PLACE:
		_cmd_button("Cancel", "ui:cancel", [], "cancel")
		return
	if cmd.mode in [Commander.M.ATTACK, Commander.M.MOVE, Commander.M.RALLY]:
		_cmd_button("Cancel", "ui:cancel", [], "cancel")
		return
	var race: String = pl.race
	if card_state == "build" or card_state == "build_free":
		for bid in Defs.race_building_list(race):
			var bd: Dictionary = Defs.buildings[bid]
			var miss := world.missing_requirement(pid, bid)
			var b := _cmd_button(String(bd["name"]), bid, bd["cost"], "build:%s" % bid, true)
			if miss != "":
				b.modulate = Color(1, 1, 1, 0.45)
				b.tooltip_text = "Requires %s" % miss
			elif not pl.can_afford(bd["cost"]):
				b.modulate = Color(1, 0.75, 0.75, 0.8)
		_cmd_button("Back", "ui:back", [], "back")
		return
	var workers := cmd.own_workers()
	var army := cmd.own_units(false)
	var producers := cmd.own_producers()
	var own_b: Array = []
	for e in sel:
		if e is Building and e.owner_id == pid:
			own_b.append(e)
	if army.size() > 0 or workers.size() > 0:
		if workers.size() > 0 and army.is_empty():
			_cmd_button("Build", "ui:build", [], "open_build")
			_cmd_button("Harvest", "ui:harvest", [], "gather")
		_cmd_button("Attack", "ui:attack", [], "attack")
		_cmd_button("Move", "ui:move", [], "move")
		_cmd_button("Stop", "ui:stop", [], "stop")
		if army.size() > 0:
			_cmd_button("Hold", "ui:hold", [], "hold")
		return
	if own_b.size() > 0:
		var b0: Building = own_b[0]
		if not b0.built:
			_cmd_button("Cancel", "ui:cancel", [], "cancel_build")
			return
		if producers.size() > 0:
			for uid in b0.produces():
				var ud: Dictionary = Defs.units[uid]
				var ok := pl.can_afford(ud["cost"])
				var b := _cmd_button(String(ud["name"]), uid, ud["cost"], "train:%s" % uid, true)
				if not ok:
					b.modulate = Color(1, 0.75, 0.75, 0.8)
			_cmd_button("Rally", "ui:rally", [], "rally")


# ---------------------------------------------------------------- selection panel

func _refresh_selection(force: bool) -> void:
	var sel := cmd.selection
	var sig := ""
	for e in sel:
		sig += "%d,%d,%d,%d;" % [e.eid, int(e.hp), int(e.status_text().hash()), (e.queue.size() if e is Building else 0)]
	if not force and sig == sel_sig:
		return
	sel_sig = sig
	for c in sel_content.get_children():
		c.queue_free()
		sel_content.remove_child(c)
	if sel.is_empty():
		var hint := UiKit.label("Tap a unit or building.\nDrag to look around, pinch to zoom.\nHold then drag to box-select.", 15, UiKit.DIM)
		hint.position = Vector2(10, 18)
		sel_content.add_child(hint)
		return
	if sel.size() == 1:
		_single(sel[0])
		return
	# a grid of small portraits
	var counts := {}
	var grid := GridContainer.new()
	grid.columns = 8
	grid.add_theme_constant_override("h_separation", 3)
	grid.add_theme_constant_override("v_separation", 3)
	grid.position = Vector2(4, 24)
	sel_content.add_child(grid)
	var head := UiKit.head("%d SELECTED" % sel.size(), 13, UiKit.DIM)
	head.position = Vector2(6, 0)
	sel_content.add_child(head)
	var shown := 0
	for e in sel:
		counts[e.def_id] = int(counts.get(e.def_id, 0)) + 1
		if shown >= 16:
			continue
		shown += 1
		var b := Button.new()
		b.custom_minimum_size = Vector2(42, 46)
		b.focus_mode = Control.FOCUS_NONE
		var tex := UiKit.icon(e.def_id)
		if tex:
			b.icon = tex
			b.expand_icon = true
		else:
			b.text = String(e.def.get("name", "?")).substr(0, 2)
		var f: float = e.hp / e.max_hp
		b.modulate = Color(1, 1, 1) if f > 0.6 else (Color(1, 0.9, 0.5) if f > 0.3 else Color(1, 0.5, 0.45))
		var ent = e
		b.pressed.connect(func(): cmd.set_selection([ent]))
		grid.add_child(b)


func _single(e) -> void:
	var tex := UiKit.icon(e.def_id if not (e is ResourceNode) else ("crystal_a" if e.kind == "mineral" else "slime_pile"))
	if tex:
		var tr := TextureRect.new()
		tr.texture = tex
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		tr.size = Vector2(84, 84)
		tr.position = Vector2(4, 4)
		sel_content.add_child(tr)
	var x0 := 96.0
	var name: String = e.def.get("name", "")
	if e is ResourceNode:
		name = "Golden Crystals" if e.kind == "mineral" else "Void Slime"
	var owner_txt := ""
	if e.owner_id >= 0 and e.owner_id != pid:
		owner_txt = "  (enemy)"
	var t := UiKit.head(name.to_upper() + owner_txt, 16, UiKit.BAD if owner_txt != "" else UiKit.TEXT)
	t.position = Vector2(x0, 0)
	sel_content.add_child(t)
	if not (e is ResourceNode):
		var bar_bg := ColorRect.new()
		bar_bg.color = Color(0, 0, 0, 0.6)
		bar_bg.position = Vector2(x0, 30)
		bar_bg.size = Vector2(250, 12)
		sel_content.add_child(bar_bg)
		var bar := ColorRect.new()
		var f: float = e.hp / e.max_hp
		bar.color = Color(0.35, 1.0, 0.45) if f > 0.6 else (Color(1.0, 0.85, 0.25) if f > 0.3 else Color(1.0, 0.3, 0.25))
		bar.position = Vector2(x0, 30)
		bar.size = Vector2(250 * f, 12)
		sel_content.add_child(bar)
		var hpl := UiKit.label("%d / %d   armour %d" % [int(ceil(e.hp)), int(e.max_hp), int(e.armor)], 13, UiKit.DIM)
		hpl.position = Vector2(x0, 44)
		sel_content.add_child(hpl)
	var st: String = e.status_text()
	if e is Unit and not e.weapon.is_empty() and not e.is_worker:
		var w: Dictionary = e.weapon
		var hits := "air & ground" if bool(w["air"]) and bool(w["ground"]) else ("air" if bool(w["air"]) else "ground")
		st += "\n%s dmg, range %s, hits %s" % [str(w["dmg"]), str(w["range"]), hits]
	var desc: String = e.def.get("desc", "")
	var s := UiKit.label(st if st != "" else desc, 14, UiKit.TEXT)
	s.position = Vector2(x0, 64)
	s.size = Vector2(270, 60)
	s.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	sel_content.add_child(s)
	if e is Building and e.owner_id == pid and e.queue.size() > 0:
		var h := HBoxContainer.new()
		h.position = Vector2(x0, 92)
		h.add_theme_constant_override("separation", 4)
		sel_content.add_child(h)
		for i in e.queue.size():
			var b := Button.new()
			b.custom_minimum_size = Vector2(40, 36)
			b.focus_mode = Control.FOCUS_NONE
			var qt := UiKit.icon(e.queue[i])
			if qt:
				b.icon = qt
				b.expand_icon = true
			else:
				b.text = String(Defs.units[e.queue[i]]["name"]).substr(0, 2)
			b.tooltip_text = "Tap to cancel"
			var idx: int = i
			b.pressed.connect(func(): cmd.action("cancel_q:%d" % idx))
			h.add_child(b)
