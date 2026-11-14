extends Node
## Sound. Effects: every sound has a synthesised version made at start-up, and a recorded clip
## in assets/sfx/ replaces it: <name>.ogg, plus optional variants <name>_2.ogg ...
## <name>_6.ogg that play() picks between at random. play_at() fades a sound with its
## distance from the camera's focus and skips far-away ones.
##
## Music (assets/music/, Music bus): a calm track per map, crossfaded to a battle track while
## fighting is heard near the camera or the base is attacked, plus win and lose stings.
## Ambience (assets/ambience/): a quiet looped bed per map. Announcer (assets/voice/): short
## lines in the player's race voice, each with its own cooldown. See assets/CREDITS.md.

const RATE := 22050
const VOICES := 18
const SFX_DIR := "res://assets/sfx/"
const MUSIC_DIR := "res://assets/music/"
const AMB_DIR := "res://assets/ambience/"
const VOICE_DIR := "res://assets/voice/"
const MAX_VARIANTS := 6
const COMBAT_HOLD := 38.0       # seconds the battle track stays after the last fighting
const HEAT_TRIGGER := 14.0      # weapon sounds heard close together that count as a battle
const VOICE_COOLDOWN := {"look_out": 25.0, "target_destroyed": 12.0}

var streams: Dictionary = {}
var players: Array = []
var next_voice: int = 0
var listener: Vector2 = Vector2.ZERO
var hear_radius: float = 40.0
var recent: Dictionary = {}
var enabled: bool = true
var volume_db: float = -6.0

var calm: AudioStreamPlayer
var battle: AudioStreamPlayer
var amb: AudioStreamPlayer
var sting_player: AudioStreamPlayer
var announcer: AudioStreamPlayer
var calm_name: String = ""
var battle_name: String = ""
var combat_left: float = 0.0
var heat: float = 0.0
var mix_k: float = 0.0          # 0 = calm track, 1 = battle track
var music_fade: float = 1.0     # overall music level, faded down for stings
var voice_kind: String = "female"
var voice_last: Dictionary = {}
var _cache: Dictionary = {}


func _ready() -> void:
	if DisplayServer.get_name() == "headless":
		enabled = false
		return
	for i in VOICES:
		var p := AudioStreamPlayer.new()
		p.bus = "Effects"
		add_child(p)
		players.append(p)
	calm = _player("Music")
	battle = _player("Music")
	sting_player = _player("Music")
	amb = _player("Effects")
	announcer = _player("Effects")
	_make_all()
	_load_files()


func _player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func play(name: String, pitch: float = 1.0, vol: float = 0.0) -> void:
	if not enabled or not streams.has(name):
		return
	var now := Time.get_ticks_msec()
	var last: int = recent.get(name, -1000)
	if now - last < 45:
		return
	recent[name] = now
	var p: AudioStreamPlayer = players[next_voice]
	next_voice = (next_voice + 1) % VOICES
	var s = streams[name]
	p.stream = s.pick_random() if s is Array else s
	p.pitch_scale = pitch * randf_range(0.94, 1.06)
	p.volume_db = volume_db + vol
	p.play()


func play_at(name: String, at: Vector2, pitch: float = 1.0) -> void:
	var d := at.distance_to(listener)
	if d > hear_radius:
		return
	var k := 1.0 - d / hear_radius
	if k > 0.35:
		heat += 1.0
		if heat > HEAT_TRIGGER:
			combat()
	play(name, pitch, linear_to_db(maxf(0.05, k)) - 4.0)


# ---------------------------------------------------------------- music and ambience

func _load_stream(path: String, looped: bool) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	if not ResourceLoader.exists(path):
		return null
	var st = load(path)
	if st is AudioStreamOggVorbis:
		(st as AudioStreamOggVorbis).loop = looped
	_cache[path] = st
	return st


## Start the calm track `calm_id` (crossfading from whatever played), with `battle_id`
## ready for fights. An empty battle_id keeps the calm track throughout.
func music(calm_id: String, battle_id: String = "") -> void:
	if not enabled:
		return
	battle_name = battle_id
	combat_left = 0.0
	mix_k = 0.0
	music_fade = 1.0
	sting_player.stop()
	battle.stop()
	if calm_id == calm_name and calm.playing:
		return
	calm_name = calm_id
	calm.stream = _load_stream(MUSIC_DIR + calm_id + ".ogg", true)
	if calm.stream:
		calm.volume_db = -40.0
		calm.play()


func stop_music() -> void:
	calm_name = ""
	battle_name = ""
	calm.stop()
	battle.stop()


## Fighting is happening near the camera (or the base is under attack): bring in the battle track.
func combat() -> void:
	if battle_name == "" or not enabled:
		return
	combat_left = COMBAT_HOLD
	if not battle.playing:
		battle.stream = _load_stream(MUSIC_DIR + battle_name + ".ogg", true)
		if battle.stream:
			battle.volume_db = -40.0
			battle.play()


## Win or lose: the music dips out and the sting plays once.
func sting(id: String) -> void:
	if not enabled:
		return
	var st := _load_stream(MUSIC_DIR + id + ".ogg", false)
	if st == null:
		play(id)
		return
	music_fade = 0.0
	combat_left = 0.0
	sting_player.stream = st
	sting_player.volume_db = 0.0
	sting_player.play()


func ambience(id: String) -> void:
	if not enabled:
		return
	if id == "":
		amb.stop()
		return
	var st := _load_stream(AMB_DIR + id + ".ogg", true)
	if st == null or (amb.stream == st and amb.playing):
		return
	amb.stream = st
	amb.volume_db = -9.0
	amb.play()


## A spoken line in the player's race voice ("female" for Ambron, "male" for the Void),
## at most once per its cooldown.
func announce(line: String) -> void:
	if not enabled:
		return
	var now := Time.get_ticks_msec() / 1000.0
	if now - float(voice_last.get(line, -999.0)) < float(VOICE_COOLDOWN.get(line, 3.0)):
		return
	var st := _load_stream("%s%s/%s.ogg" % [VOICE_DIR, voice_kind, line], false)
	if st == null:
		return
	voice_last[line] = now
	announcer.stream = st
	announcer.pitch_scale = 0.86 if voice_kind == "male" else 1.0
	announcer.volume_db = 1.0
	announcer.play()


func set_voice_for(race: String) -> void:
	voice_kind = "male" if race == "void" else "female"


func _process(delta: float) -> void:
	if not enabled:
		return
	heat = maxf(0.0, heat - delta * 3.0)
	combat_left = maxf(0.0, combat_left - delta)
	var want := 1.0 if combat_left > 0.0 and battle.playing else 0.0
	mix_k = move_toward(mix_k, want, delta / (2.5 if want > mix_k else 5.0))
	var lvl := music_fade if music_fade > 0.0 else 0.0
	if calm.playing:
		calm.volume_db = linear_to_db(maxf(0.0001, (1.0 - mix_k) * lvl))
	if battle.playing:
		battle.volume_db = linear_to_db(maxf(0.0001, mix_k * lvl))
		if mix_k <= 0.0 and want == 0.0:
			battle.stop()
	if music_fade < 1.0 and not sting_player.playing and calm_name != "":
		music_fade = minf(1.0, music_fade + delta * 0.3)


# ---------------------------------------------------------------- recorded clips

func _load_files() -> void:
	for name in streams.keys():
		var found: Array = []
		for i in range(1, MAX_VARIANTS + 1):
			var path: String = SFX_DIR + name + ("" if i == 1 else "_%d" % i) + ".ogg"
			if ResourceLoader.exists(path):
				found.append(load(path))
		if not found.is_empty():
			streams[name] = found


# ---------------------------------------------------------------- synthesis

func _make_all() -> void:
	streams["bolt"] = _synth(0.13, func(t, k): return (sin(TAU * lerpf(1900.0, 500.0, k) * t) * 0.6 + _n() * 0.15) * (1.0 - k))
	streams["glob"] = _synth(0.16, func(t, k): return sin(TAU * lerpf(380.0, 110.0, k) * t + sin(TAU * 30.0 * t) * 2.0) * (1.0 - k) * 0.8)
	streams["shell"] = _synth(0.24, func(t, k): return (sin(TAU * lerpf(220.0, 70.0, k) * t) * 0.7 + _n() * 0.35 * (1.0 - k)) * pow(1.0 - k, 1.5))
	streams["missile"] = _synth(0.4, func(t, k): return _lp(_n(), 0.15 + k * 0.5) * sin(PI * k) * 0.9)
	streams["flame"] = _synth(0.42, func(t, k): return _lp(_n(), 0.25) * (1.0 - k) * 0.9)
	streams["beam"] = _synth(0.32, func(t, k): return (fmod(t * 220.0, 1.0) - 0.5 + sin(TAU * 440.0 * t) * 0.4) * 0.5 * sin(PI * k))
	streams["boom"] = _synth(0.8, func(t, k): return (_lp(_n(), 0.12) * 1.2 + sin(TAU * lerpf(90.0, 35.0, k) * t) * 0.6) * pow(1.0 - k, 2.0))
	streams["splat"] = _synth(0.45, func(t, k): return (_lp(_n(), 0.3) * 0.8 + sin(TAU * lerpf(160.0, 60.0, k) * t + sin(TAU * 18.0 * t) * 3.0) * 0.5) * pow(1.0 - k, 1.6))
	streams["zap"] = _synth(0.34, func(t, k): return (_n() * (1.0 if fmod(t * 85.0 + _n() * 0.3, 1.0) < 0.45 else 0.25) * 0.75 + sin(TAU * lerpf(2600.0, 700.0, k) * t) * 0.25) * pow(1.0 - k, 1.3))
	streams["spike"] = _synth(0.22, func(t, k): return (sin(TAU * lerpf(320.0, 80.0, k) * t) * 0.6 + _lp(_n(), 0.55) * 0.55 * (1.0 - k)) * pow(1.0 - k, 2.0))
	streams["slime"] = _synth(0.3, func(t, k): return (sin(TAU * lerpf(260.0, 70.0, k) * t + sin(TAU * 24.0 * t) * 3.5) * 0.7 + _lp(_n(), 0.2) * 0.3) * pow(1.0 - k, 1.4))
	streams["crack"] = _synth(0.2, func(t, k): return (_lp(_n(), 0.7) * 0.8 + sin(TAU * lerpf(500.0, 120.0, k) * t) * 0.3) * pow(1.0 - k, 2.5))
	streams["acid"] = _synth(0.4, func(t, k): return (_lp(_n(), 0.5) * 0.5 + sin(TAU * (300.0 + 200.0 * sin(TAU * 40.0 * t)) * t) * 0.25) * (1.0 - k))
	streams["bite"] = _synth(0.12, func(t, k): return (_lp(_n(), 0.4) * 0.8) * pow(1.0 - k, 2.0))
	streams["screech"] = _synth(0.7, func(t, k): return (sin(TAU * lerpf(900.0, 500.0, k) * t + sin(TAU * 55.0 * t) * 4.0) * 0.45 + _lp(_n(), 0.6) * 0.2) * sin(PI * k))
	streams["open"] = _synth(0.08, func(t, k): return sin(TAU * lerpf(700.0, 1100.0, k) * t) * (1.0 - k) * 0.4)
	streams["close"] = _synth(0.08, func(t, k): return sin(TAU * lerpf(1100.0, 700.0, k) * t) * (1.0 - k) * 0.4)
	streams["click"] = _synth(0.035, func(t, k): return sin(TAU * 1400.0 * t) * (1.0 - k) * 0.5)
	streams["ready"] = _synth(0.3, func(t, k): return sin(TAU * (660.0 if k < 0.45 else 990.0) * t) * (1.0 - fmod(k, 0.5) * 1.6) * 0.45)
	streams["complete"] = _synth(0.5, func(t, k): return sin(TAU * [523.0, 659.0, 784.0][mini(2, int(k * 3.0))] * t) * (1.0 - fmod(k * 3.0, 1.0) * 0.7) * 0.45)
	streams["alert"] = _synth(0.7, func(t, k): return (fmod(t * ([440.0, 330.0][int(k * 4.0) % 2]), 1.0) - 0.5) * 0.5 * (1.0 - k * 0.5))
	streams["error"] = _synth(0.2, func(t, k): return (fmod(t * 110.0, 1.0) - 0.5) * 0.5 * (1.0 - k))
	streams["win"] = _synth(1.4, func(t, k): return sin(TAU * [392.0, 523.0, 659.0, 784.0][mini(3, int(k * 4.0))] * t) * 0.4 * (1.0 - k * 0.6))
	streams["lose"] = _synth(1.4, func(t, k): return sin(TAU * [392.0, 330.0, 262.0, 196.0][mini(3, int(k * 4.0))] * t) * 0.4 * (1.0 - k * 0.6))


var _lp_state: float = 0.0


func _n() -> float:
	return randf() * 2.0 - 1.0


func _lp(x: float, a: float) -> float:
	_lp_state += (x - _lp_state) * a
	return _lp_state * 2.0


func _synth(dur: float, f: Callable) -> AudioStreamWAV:
	var n := int(dur * RATE)
	var data := PackedByteArray()
	data.resize(n * 2)
	_lp_state = 0.0
	for i in n:
		var t := float(i) / RATE
		var k := float(i) / n
		var v: float = clampf(f.call(t, k), -1.0, 1.0)
		# tiny fade in to avoid clicks
		v *= minf(1.0, float(i) / 40.0)
		data.encode_s16(i * 2, int(v * 30000.0))
	var s := AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = RATE
	s.stereo = false
	s.data = data
	return s
