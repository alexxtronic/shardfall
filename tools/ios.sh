#!/bin/bash
# Build Shardfall for iPhone and install it over USB or Wi-Fi.
#
#   tools/ios.sh            build, then install on the first paired iPhone
#   tools/ios.sh "iPad"     install on the paired device whose name contains "iPad"
#   tools/ios.sh --no-build install the last build again
#
# Needs Godot 4.7.2 with its iOS export template, Xcode signed in to the team
# in export_presets.cfg, and the phone paired with this Mac, unlocked and in
# Developer Mode. Signing is automatic (Apple Development).
set -euo pipefail
cd "$(dirname "$0")/.."
GODOT=${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}
IPA=build/ios/Shardfall.ipa

build=1
want="iPhone"
for a in "$@"; do
	case "$a" in
		--no-build) build=0 ;;
		*) want="$a" ;;
	esac
done

if [ $build = 1 ]; then
	rm -rf build/ios && mkdir -p build/ios
	"$GODOT" --headless --path . --export-release "iOS" "$IPA" 2>&1 | grep -E "ARCHIVE|EXPORT SUCCEEDED|error:|ERROR" || true
	[ -f "$IPA" ] || { echo "Build failed: no $IPA"; exit 1; }
fi

tmp=$(mktemp -t shardfall_devices)
xcrun devicectl list devices --json-output "$tmp" > /dev/null
udid=$(python3 -I -c '
import json, sys
want = sys.argv[2].lower()
for d in json.load(open(sys.argv[1]))["result"]["devices"]:
    name = d["deviceProperties"].get("name", "")
    if want in name.lower() or want == d["hardwareProperties"].get("udid", "").lower():
        print(d["hardwareProperties"]["udid"])
        break
' "$tmp" "$want")
rm -f "$tmp"
[ -n "$udid" ] || { echo "No paired device matches \"$want\"."; exit 1; }

echo "Installing on $want ($udid)..."
xcrun devicectl device install app --device "$udid" "$IPA" | grep -E "App installed|bundleID" || true
xcrun devicectl device process launch --device "$udid" com.alexdamore.shardfall > /dev/null && echo "Launched."
