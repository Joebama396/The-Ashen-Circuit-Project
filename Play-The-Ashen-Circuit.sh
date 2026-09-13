#!/bin/sh
# Run the adjacent AppImage without requiring a FUSE installation or mount.
set -u
launch_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=''
image_count=0
for candidate in "$launch_dir"/The_Ashen_Circuit-*-x86_64.AppImage; do
    if [ -f "$candidate" ]; then
        image="$candidate"
        image_count=$((image_count + 1))
    fi
done
if [ "$image_count" -ne 1 ]; then
    printf '%s\n' 'Keep this launcher in a folder containing exactly one The_Ashen_Circuit-*-x86_64.AppImage.' >&2
    exit 1
fi
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/ashen-circuit"
cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/ashen-circuit/runtime"
mkdir -p "$state_dir" "$cache_dir" || exit 1
log="$state_dir/launcher.log"
if [ "$(uname -m)" != x86_64 ]; then
    printf '%s\n' 'This build needs an Intel/AMD 64-bit Linux computer (x86_64).' >&2
    exit 1
fi
chmod u+x "$image" || exit 1
printf '%s\n' "Launching The Ashen Circuit without FUSE" > "$log"
TMPDIR="$cache_dir" "$image" --appimage-extract-and-run "$@" >> "$log" 2>&1
result=$?
if [ "$result" -ne 0 ]; then
    cat "$log" >&2
    printf '\n%s\n' "Launch failed (exit $result). Details: $log" >&2
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title='The Ashen Circuit' --text="The game could not start. Please share this log:\n$log" 2>/dev/null || :
    fi
fi
exit "$result"
