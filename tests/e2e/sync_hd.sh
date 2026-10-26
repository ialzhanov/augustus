#!/bin/sh
# Copies the live HD sprites into tests/e2e/hd/. The tests use only this copy,
# so a sprite change shows in git diff together with the new approved images.
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SOURCE=${C3_DATA:-$HOME/caesar3}/hd
if [ ! -d "$SOURCE" ]; then
    echo "no HD folder: $SOURCE"
    exit 2
fi
rsync -a --delete "$SOURCE/" "$ROOT/tests/e2e/hd/" || exit 2
echo "$(find "$ROOT/tests/e2e/hd" -type f | wc -l | tr -d ' ') files, $(du -sh "$ROOT/tests/e2e/hd" | cut -f1)"
