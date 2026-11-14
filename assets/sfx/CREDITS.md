# Sound effect clips

`scripts/sfx.gd` loads `<name>.ogg` and the variants `<name>_2.ogg` … `<name>_6.ogg` from this
folder in place of its synthesised sound of the same name. Sounds with no clip here keep the
synthesised version.

Every clip is mono Ogg Vorbis at 44.1 kHz:
- leading silence is trimmed and the tail fades out;
- loudness is matched to the slot (mean volume about -27 dB for taps, -20 dB for shots, -14 dB for explosions);
- peaks are limited to -1 dBFS.

## Sources

See `assets/CREDITS.md` for every clip's source, author and licence (all CC0).
