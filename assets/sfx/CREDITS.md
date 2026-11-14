# Sound effect clips

`scripts/sfx.gd` loads `<name>.ogg` and the variants `<name>_2.ogg` … `<name>_6.ogg` from this
folder in place of its synthesised sound of the same name. Sounds with no clip here keep the
synthesised version.

Every clip is mono Ogg Vorbis at 44.1 kHz:
- leading silence is trimmed and the tail fades out;
- loudness is matched to the slot (mean volume about -17 dB for shots, -14 dB for explosions);
- peaks are limited to -1 dBFS.

## Sources

All current clips come from **Sci-Fi Sounds 1.0 by Kenney** (www.kenney.nl), licensed
**CC0 1.0** (public domain, free for commercial use, credit optional).

| Clip | Source file(s) | Plays for |
|---|---|---|
| bolt, bolt_2 … bolt_5 | laserSmall_000 … 004 | Lancer, Dart shots |
| beam, beam_2, beam_3 | laserLarge_000, 002, 004 | Sovereign beam |
| shell, shell_2 | explosionCrunch_002 + lowFrequency_explosion_001; explosionCrunch_004 + lowFrequency_explosion_000 (layered) | Bulwark shell, Monolith cannon |
| boom, boom_2, boom_3 | explosionCrunch_000, 001, 003 | Ambron deaths |
| slime | slime_000 | Slime Spire shots, slime impacts |
