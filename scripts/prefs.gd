extends Node
## Player settings kept between sessions in user://settings.cfg: volumes, screen shake and the
## last match setup. Also makes the Music and Effects audio buses the volume sliders drive.
## Test runs (--autotest, --balance) read the defaults and never write the file.

signal changed(key: String)

const PATH := "user://settings.cfg"
const DEFAULTS := {
	"master": 0.9,
	"music": 0.55,
	"effects": 0.85,
	"shake": true,
	"race": "ambron",
	"enemy": "random",
	"difficulty": "normal",
	"map": "shatterfield",
	"tutorial_done": false,
	"army_tip": 0,
}

var data: Dictionary = DEFAULTS.duplicate()
var persist: bool = true


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--autotest") or a == "--balance":
			persist = false
	for b in ["Music", "Effects"]:
		if AudioServer.get_bus_index(b) == -1:
			AudioServer.add_bus()
			var i := AudioServer.bus_count - 1
			AudioServer.set_bus_name(i, b)
			AudioServer.set_bus_send(i, "Master")
	if persist:
		var c := ConfigFile.new()
		if c.load(PATH) == OK:
			for k in DEFAULTS:
				var v = c.get_value("prefs", k, DEFAULTS[k])
				if typeof(v) == typeof(DEFAULTS[k]):
					data[k] = v
	apply()
	if not persist:
		AudioServer.set_bus_mute(0, true)    # test runs stay quiet


func get_v(key: String):
	return data.get(key, DEFAULTS.get(key))


func set_v(key: String, value) -> void:
	if data.get(key) == value:
		return
	data[key] = value
	apply()
	save()
	changed.emit(key)


func save() -> void:
	if not persist:
		return
	var c := ConfigFile.new()
	for k in data:
		c.set_value("prefs", k, data[k])
	c.save(PATH)


func apply() -> void:
	_vol("Master", float(data["master"]))
	_vol("Music", float(data["music"]))
	_vol("Effects", float(data["effects"]))


func _vol(bus: String, v: float) -> void:
	var i := AudioServer.get_bus_index(bus)
	if i < 0:
		return
	AudioServer.set_bus_volume_db(i, linear_to_db(maxf(v, 0.0001)))
	AudioServer.set_bus_mute(i, v <= 0.001 or (bus == "Master" and not persist))
