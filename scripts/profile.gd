extends Node
## The local player's profile, kept in user://profile.json: name, Elo rating, win record,
## best score per map and recent match history.
##
## Rating: each bot difficulty has a fixed rating (easy 600, normal 900, hard 1200, extreme 1600) and a
## result moves the player's rating by K * (result - expected), the usual Elo update. K is 40
## for the first 10 games so a new player finds their level quickly, then 24.
##
## The ladder ranks the player among AI rival commanders with fixed ratings, so the
## leaderboard means something offline. An online version swaps `ladder()` and `submit()`
## for a backend (see docs/MOBILE_MULTIPLAYER.md: Nakama leaderboards); nothing else changes.
## Test runs (--autotest, --balance) keep the profile in memory and never write the file.

signal changed

const PATH := "user://profile.json"
const BOT_RATING := {"easy": 600, "normal": 900, "hard": 1200, "extreme": 1600}
const DIFF_MULT := {"easy": 0.6, "normal": 0.8, "hard": 1.0, "extreme": 1.5}
const HISTORY_MAX := 40
const NAME_MAX := 16
const RIVALS := [
	["VEX//ZERO", 1860], ["Iris-9", 1745], ["The Ninth Choir", 1640], ["Oru Tanaq", 1555],
	["Sable", 1470], ["Corvin Ashe", 1390], ["Hollow Saint", 1310], ["Dax", 1230],
	["Pell the Quiet", 1150], ["Juno Fenn", 1070], ["Grit", 990], ["Tamsin", 905],
	["Rookie Unit 7", 800],
]
const TIERS := [
	[1700, "Master", Color(1.0, 0.45, 0.85)],
	[1500, "Diamond", Color(0.55, 0.9, 1.0)],
	[1300, "Platinum", Color(0.6, 1.0, 0.85)],
	[1100, "Gold", Color(1.0, 0.8, 0.3)],
	[900, "Silver", Color(0.8, 0.84, 0.9)],
	[0, "Bronze", Color(0.85, 0.55, 0.35)],
]

var data: Dictionary = {}
var persist: bool = true


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--autotest") or a == "--balance":
			persist = false
	if Bench.requested() != -9:
		persist = false
	data = defaults()
	if persist and FileAccess.file_exists(PATH):
		var f := FileAccess.open(PATH, FileAccess.READ)
		var got = JSON.parse_string(f.get_as_text()) if f else null
		if got is Dictionary:
			for k in data:
				if got.has(k) and typeof(got[k]) == typeof(data[k]):
					data[k] = got[k]


static func defaults() -> Dictionary:
	return {"name": "Commander", "rating": 1000.0, "peak": 1000.0, "games": 0.0, "wins": 0.0,
		"streak": 0.0, "best": {}, "history": []}


func reset() -> void:
	data = defaults()
	changed.emit()


func save() -> void:
	if not persist:
		return
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(data, "\t"))


func player_name() -> String:
	return String(data["name"])


func set_player_name(n: String) -> void:
	n = n.strip_edges().left(NAME_MAX)
	if n == "":
		n = "Commander"
	data["name"] = n
	save()
	changed.emit()


func rating() -> int:
	return roundi(float(data["rating"]))


func games() -> int:
	return int(data["games"])


func wins() -> int:
	return int(data["wins"])


func best(map_id: String) -> int:
	return int((data["best"] as Dictionary).get(map_id, 0))


func history() -> Array:
	return data["history"]


## [name, colour] of the tier a rating falls in.
static func tier(r: int) -> Array:
	for t in TIERS:
		if r >= int(t[0]):
			return [t[1], t[2]]
	return [TIERS[-1][1], TIERS[-1][2]]


## Everyone on the ladder, best first: {name, rating, me}.
func ladder() -> Array:
	var rows: Array = []
	for r in RIVALS:
		rows.append({"name": r[0], "rating": int(r[1]), "me": false})
	rows.append({"name": player_name(), "rating": rating(), "me": true})
	rows.sort_custom(func(a, b): return a["rating"] > b["rating"] or (a["rating"] == b["rating"] and a["me"]))
	return rows


func rank() -> int:
	var rows := ladder()
	for i in rows.size():
		if rows[i]["me"]:
			return i + 1
	return rows.size()


## Elo expectation and change for one game against a bot of `difficulty`.
static func elo_delta(r: float, difficulty: String, won: bool, played: int) -> int:
	var rb := float(BOT_RATING.get(difficulty, 1200))
	var expected := 1.0 / (1.0 + pow(10.0, (rb - r) / 400.0))
	var k := 40.0 if played < 10 else 24.0
	return roundi(k * ((1.0 if won else 0.0) - expected))


## Match score: a base for the result, plus damage dealt, economy and (on a win) speed,
## all scaled by the bot's difficulty.
static func score_of(won: bool, difficulty: String, me: PlayerState, time: float) -> int:
	var s := 1000.0 if won else 250.0
	s += me.value_killed * 0.4
	s += float(me.gathered_m + me.gathered_s) * 0.08
	if won:
		s += maxf(0.0, 1500.0 - time) * 0.5
	return roundi(s * float(DIFF_MULT.get(difficulty, 1.0)))


## Record a finished game against the bot and return what changed, for the results screen:
## {score, best_before, new_best, delta, rating, rank_before, rank, tier, tier_before}.
func submit(map_id: String, race: String, enemy: String, difficulty: String, won: bool,
		me: PlayerState, time: float) -> Dictionary:
	var played := games()
	var r0 := float(data["rating"])
	var rank0 := rank()
	var delta := elo_delta(r0, difficulty, won, played)
	var score := score_of(won, difficulty, me, time)
	var best0 := best(map_id)
	data["rating"] = maxf(100.0, r0 + delta)
	data["peak"] = maxf(float(data["peak"]), float(data["rating"]))
	data["games"] = float(played + 1)
	if won:
		data["wins"] = float(wins() + 1)
		data["streak"] = maxf(1.0, float(data["streak"]) + 1.0) if float(data["streak"]) >= 0.0 else 1.0
	else:
		data["streak"] = minf(-1.0, float(data["streak"]) - 1.0) if float(data["streak"]) <= 0.0 else -1.0
	if score > best0:
		(data["best"] as Dictionary)[map_id] = score
	var h: Array = data["history"]
	h.push_front({
		"date": Time.get_datetime_string_from_system(false, true).left(16),
		"map": map_id, "race": race, "enemy": enemy, "difficulty": difficulty, "won": won,
		"score": score, "delta": delta, "rating": rating(), "time": roundi(time),
		"kills": me.kills,
	})
	while h.size() > HISTORY_MAX:
		h.pop_back()
	save()
	changed.emit()
	return {"score": score, "best_before": best0, "new_best": score > best0, "delta": delta,
		"rating": rating(), "rank_before": rank0, "rank": rank(), "tier": tier(rating()),
		"tier_before": tier(roundi(r0))}
