extends Node
## Sound effects, synthesised at start-up (no audio files). play_at() fades a
## sound with its distance from the camera's focus and skips far-away ones.

const RATE := 22050
const VOICES := 18

var streams: Dictionary = {}
var players: Array = []
var next_voice: int = 0
var listener: Vector2 = Vector2.ZERO
var hear_radius: float = 40.0
var recent: Dictionary = {}
var enabled: bool = true
var volume_db: float = -6.0


func _ready() -> void:
	if DisplayServer.get_name() == "headless":
		enabled = false
		return
	for i in VOICES:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		players.append(p)
	_make_all()


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
	p.stream = streams[name]
	p.pitch_scale = pitch * randf_range(0.94, 1.06)
	p.volume_db = volume_db + vol
	p.play()


func play_at(name: String, at: Vector2, pitch: float = 1.0) -> void:
	var d := at.distance_to(listener)
	if d > hear_radius:
		return
	var k := 1.0 - d / hear_radius
	play(name, pitch, linear_to_db(maxf(0.05, k)) - 4.0)


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
