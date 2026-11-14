extends Node
# Loads every script so parse errors show up at once.
#   Godot --headless --path . res://tools/check.tscn
func _ready() -> void:
	var d := DirAccess.open("res://scripts")
	for f in d.get_files():
		if f.ends_with(".gd"):
			var s = load("res://scripts/" + f)
			if s == null:
				print("LOAD FAIL ", f)
	print("CHECK DONE")
	get_tree().quit()
