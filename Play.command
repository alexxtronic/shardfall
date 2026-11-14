#!/bin/bash
# Double-click to play Shardfall (needs Godot 4.7 in /Applications).
cd "$(dirname "$0")"
exec /Applications/Godot.app/Contents/MacOS/Godot --path . --resolution 1280x720
