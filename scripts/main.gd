extends Node
## Entry point: the title screen, matches, and the test modes.
##   -- --autotest=DIR       plays scripted checks, saves screenshots to DIR
##   -- --balance            headless battles between equal-value armies
##   -- --play=ambron,void   skip the title (your race, the bot's race)

var title: Title
var match_node: Match
var last_cfg: Dictionary = {}


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	for a in args:
		if a.begins_with("--autotest="):
			var t := Autotest.new()
			t.out_dir = a.substr(11)
			t.args = args
			t.main = self
			add_child(t)
			return
		if a == "--balance":
			var b := Balance.new()
			b.args = args
			add_child(b)
			return
		if a.begins_with("--play="):
			var parts := a.substr(7).split(",")
			start_match({"races": [parts[0], parts[1] if parts.size() > 1 else "void"], "ai": [false, true], "difficulty": "normal", "human": 0})
			return
	show_title()


func show_title() -> void:
	if match_node:
		match_node.queue_free()
		match_node = null
	title = Title.new()
	title.name = "Title"
	add_child(title)
	title.play.connect(start_match)


func start_match(cfg: Dictionary) -> void:
	last_cfg = cfg
	if title:
		title.queue_free()
		title = null
	if match_node:
		match_node.queue_free()
		match_node = null
	match_node = Match.new()
	add_child(match_node)
	match_node.start(cfg)
	match_node.finished.connect(_on_finished)


func _on_finished(action: String) -> void:
	if action == "restart":
		start_match(last_cfg)
	else:
		show_title()
