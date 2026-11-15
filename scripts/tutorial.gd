class_name Tutorial
extends Node
## A guided first match on Shatterfield against an easy bot. One lesson at a time, each
## gated on something the player actually does: look around, train a worker, build supply,
## build a barracks, train infantry, move out, then destroy the enemy. The bot waits
## until the last step. The card sits on the right, under the minimap, and never blocks
## the battlefield; "Skip" ends the lessons and leaves a normal game.

signal step_changed(i: int)

var world: World
var hud: Hud
var rig: CameraRig
var cmd: Commander
var race: String = "ambron"
var step: int = -1
var steps: Array = []          # [title, text, check: Callable]
var card: PanelContainer
var head_lbl: Label
var body_lbl: Label
var tick_lbl: Label
var start_focus: Vector2
var start_dist: float
var advancing: bool = false
var ping_t: float = 0.0
var done: bool = false


func setup(w: World, h: Hud, r: CameraRig, c: Commander) -> void:
	world = w
	hud = h
	rig = r
	cmd = c
	race = world.players[0].race
	start_focus = rig.focus
	start_dist = rig.dist
	for ai in world.ais:
		ai.paused = true
	var main_n := _bname("main")
	var sup_n := _bname("supply")
	var bar_n := _bname("barracks")
	var inf_n := _uname("infantry")
	var power := " Ambron buildings need power: put it inside the Power Relay's blue field once the relay is finished." if race == "ambron" else ""
	steps = [
		["LOOK AROUND", "Drag one finger to move the camera. Pinch (or scroll) to zoom.", _looked],
		["MORE WORKERS", "Your workers harvest crystals on their own. Tap your %s, then tap the worker button to train one more." % main_n, _trained_worker],
		["SUPPLY", "Every unit takes supply. Tap BUILDINGS (left), choose %s, tap the ground to place it, then tap again or ✓." % _a(sup_n), _has.bind("supply")],
		["PRODUCTION", "Now place %s from BUILDINGS.%s" % [_a(bar_n), power], _has.bind("barracks")],
		["AN ARMY", "When the %s is finished, tap it and train 4 %ss. (Later, hold BUILDINGS and slide to select every one you own and train from all of them.)" % [bar_n, inf_n], _army_of.bind(4)],
		["MOVE OUT", "Tap ARMY to select every fighter (hold ARMY and slide to pick just ground, air or one unit type). Then tap Attack and tap the ground ahead: they fight anything they meet on the way.", _moving],
		["DESTROY THEM", "The enemy is awake. Their base is the red mark at the top right of the minimap. Climb the ramps: units can't see up a cliff, and shots fired uphill miss 30% of the time. Destroy every enemy building!", func() -> bool: return false],
	]
	_card()
	_go(0)


## "a Power Relay", "an Assembly Bay".
static func _a(noun: String) -> String:
	return ("an " if noun.left(1).to_lower() in ["a", "e", "i", "o", "u"] else "a ") + noun


func _bname(slot: String) -> String:
	return String(Defs.buildings[Defs.building_id(race, slot)]["name"])


func _uname(slot: String) -> String:
	return String(Defs.units[Defs.unit_id(race, slot)]["name"])


# ---------------------------------------------------------------- checks

func _looked() -> bool:
	return rig.focus.distance_to(start_focus) > 8.0 or absf(rig.dist - start_dist) > 6.0


func _trained_worker() -> bool:
	if world.players[0].units_made > 0:
		return true
	for b in world.buildings:
		if b.owner_id == 0 and not b.dead and b.slot == "main" and not b.queue.is_empty():
			return true
	return false


func _has(slot: String) -> bool:
	for b in world.buildings:
		if b.owner_id == 0 and not b.dead and b.slot == slot:
			return true
	# a worker on its way to build one counts too
	for u in world.units:
		if u.owner_id == 0 and not u.dead and u.build_id == Defs.building_id(race, slot):
			return true
	return false


func _army_of(n: int) -> bool:
	return _army().size() >= n


func _moving() -> bool:
	for u in _army():
		if u.order == Unit.O.AMOVE or u.order == Unit.O.MOVE or u.order == Unit.O.ATTACK:
			return true
	return false


func _army() -> Array:
	var out: Array = []
	for u in world.units:
		if u.owner_id == 0 and not u.dead and not u.is_worker:
			out.append(u)
	return out


# ---------------------------------------------------------------- flow

func _process(delta: float) -> void:
	if done or step < 0 or step >= steps.size() or world.over:
		return
	if step == steps.size() - 1:
		# keep pointing at the enemy main for a while
		ping_t -= delta
		if ping_t <= 0.0 and world.time < float(get_meta("final_t", 0.0)) + 40.0:
			ping_t = 5.0
			var s: Dictionary = world.sites[world.players[1].start_site]
			hud.minimap.ping(s["center"])
		return
	if advancing:
		return
	var check: Callable = steps[step][2]
	if check.call():
		advancing = true
		tick_lbl.visible = true
		Sfx.play("complete", 1.0, -4.0)
		get_tree().create_timer(1.1).timeout.connect(func():
			if not done and is_instance_valid(self):
				_go(step + 1))


func _go(i: int) -> void:
	step = i
	advancing = false
	tick_lbl.visible = false
	head_lbl.text = "TUTORIAL  ·  %d / %d  ·  %s" % [i + 1, steps.size(), steps[i][0]]
	body_lbl.text = steps[i][1]
	card.modulate.a = 0.0
	create_tween().tween_property(card, "modulate:a", 1.0, 0.3)
	if i == steps.size() - 1:
		set_meta("final_t", world.time)
		ping_t = 0.0
		for ai in world.ais:
			ai.paused = false
			# it waited the whole lesson; don't let it spend a hoard at once
			world.players[ai.pid].minerals = mini(world.players[ai.pid].minerals, 300)
		Sfx.announce("look_out")
	if i > 0:
		Sfx.play("open", 1.0, -6.0)
	step_changed.emit(i)


func skip() -> void:
	done = true
	for ai in world.ais:
		ai.paused = false
		world.players[ai.pid].minerals = mini(world.players[ai.pid].minerals, 300)
	Sfx.play("close")
	card.queue_free()


# ---------------------------------------------------------------- the card

func _card() -> void:
	card = PanelContainer.new()
	card.name = "TutorialCard"
	card.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	card.offset_left = -392
	card.offset_right = -14
	card.offset_top = 226        # under the minimap
	card.add_theme_stylebox_override("panel", UiKit.solid_panel())
	hud.root.add_child(card)
	hud.blockers.append(card)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	card.add_child(v)
	var top := HBoxContainer.new()
	v.add_child(top)
	head_lbl = UiKit.head("", 13, UiKit.GOLD)
	head_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(head_lbl)
	tick_lbl = UiKit.head("✓", 18, UiKit.GOOD)
	tick_lbl.visible = false
	top.add_child(tick_lbl)
	body_lbl = UiKit.label("", 16, UiKit.TEXT)
	body_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body_lbl.custom_minimum_size = Vector2(350, 0)
	v.add_child(body_lbl)
	var sk := Button.new()
	sk.text = "Skip tutorial"
	sk.name = "Skip"
	sk.flat = true
	sk.focus_mode = Control.FOCUS_NONE
	sk.add_theme_font_size_override("font_size", 13)
	sk.add_theme_color_override("font_color", UiKit.DIM)
	sk.size_flags_horizontal = Control.SIZE_SHRINK_END
	sk.pressed.connect(skip)
	v.add_child(sk)
