#!/bin/sh
# Runs the end-to-end test cases and compares each exit code with the
# "# expect:" line of the case. Each "# expect-log: <text>" line must also be in
# log.txt, and each "# expect-file: <name>" file must be in the results folder.
# Usage: tests/e2e/run.sh [--twice] [--update-images] [case ...]
# --twice runs each case two times and compares the state dumps and the captures.

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BIN=${E2E_BIN:-$ROOT/build-e2e/augustus.app/Contents/MacOS/augustus}
DATA=${C3_DATA:-$HOME/caesar3}
RESULTS=${E2E_RESULTS:-$ROOT/build-e2e/e2e-results}
TIMEOUT=${E2E_TIMEOUT:-600}
CASE_DIR=${E2E_CASES:-$ROOT/tests/e2e/cases}
# The save functions skip bytes in buffers from malloc(). macOS fills new and
# freed memory with fixed bytes, so these bytes are the same in each run.
export MallocPreScribble=1 MallocScribble=1

UPDATE=""
TWICE=0
CASES=""
for arg in "$@"; do
    case "$arg" in
        --update-images) UPDATE="--update-images" ;;
        --twice) TWICE=1 ;;
        -*) echo "unknown option $arg"; exit 2 ;;
        *) CASES="$CASES $arg" ;;
    esac
done
if [ -n "$UPDATE" ] && [ -z "$CASES" ]; then
    # A run of all cases would approve the captures of the cases that expect a failure
    echo "--update-images needs the names of the cases to approve"
    exit 2
fi
if [ -z "$CASES" ]; then
    for f in "$CASE_DIR"/*.txt; do
        CASES="$CASES $(basename "$f" .txt)"
    done
fi

if [ ! -x "$BIN" ]; then
    echo "binary not found: $BIN"
    exit 2
fi

# Runs one case into the folder $2. Prints the result line and returns 0 when
# the exit code matches the expected code.
run_case() {
    name=$1
    out=$2
    file="$CASE_DIR/$name.txt"
    if [ ! -f "$file" ]; then
        echo "FAIL $name: no case file $file"
        return 1
    fi
    expect=$(sed -n 's/^# expect: *\([a-z]*\).*/\1/p' "$file" | head -n 1)
    case "$expect" in
        pass) want=0 ;;
        fail) want=1 ;;
        error) want=2 ;;
        *) echo "FAIL $name: no '# expect: pass|fail|error' line"; return 1 ;;
    esac
    rm -rf "${out:?}/$name"
    mkdir -p "$out/$name"
    # macOS has no timeout command. The alarm kills a test that does not exit.
    perl -e 'alarm shift; exec @ARGV' "$TIMEOUT" \
        "$BIN" --test "$file" --out "$out" $UPDATE "$DATA" > "$out/$name/stdout.txt" 2>&1
    code=$?
    if [ "$code" -gt 128 ]; then
        echo "timeout or signal after $TIMEOUT s (exit $code)" >> "$out/$name/log.txt"
    fi
    if [ "$code" -ne "$want" ]; then
        last=$(tail -n 1 "$out/$name/log.txt" 2>/dev/null)
        echo "FAIL $name: expected $expect, got exit $code: $last"
        return 1
    fi
    # The right exit code for the wrong reason is a failure too
    missing=$(sed -n 's/^# expect-log: *//p' "$file" | while IFS= read -r text; do
        grep -qF -- "$text" "$out/$name/log.txt" 2>/dev/null || { echo "$text"; break; }
    done)
    if [ -n "$missing" ]; then
        echo "FAIL $name: log.txt does not have: $missing"
        return 1
    fi
    missing=$(sed -n 's/^# expect-file: *//p' "$file" | while IFS= read -r wanted; do
        [ -f "$out/$name/$wanted" ] || { echo "$wanted"; break; }
    done)
    if [ -n "$missing" ]; then
        echo "FAIL $name: no file $missing in the results"
        return 1
    fi
    echo "PASS $name"
    return 0
}

# Compares the dumps and the captures of two runs of the case $1.
compare_runs() {
    name=$1
    for first in "$RESULTS/$name"/state_*.json "$RESULTS/$name"/*.png; do
        [ -f "$first" ] || continue
        file=$(basename "$first")
        if ! cmp -s "$first" "$SECOND/$name/$file"; then
            echo "FAIL $name: $file differs"
            return 1
        fi
    done
    echo "PASS $name"
}

SECOND="$RESULTS-second"
mkdir -p "$RESULTS"
: > "$RESULTS/summary.txt"
status=0
for name in $CASES; do
    line=$(run_case "$name" "$RESULTS") || status=1
    if [ "$TWICE" = 1 ] && [ "${line#PASS}" != "$line" ]; then
        line=$(run_case "$name" "$SECOND") && line=$(compare_runs "$name")
        [ "${line#PASS}" != "$line" ] || status=1
    fi
    echo "$line"
    echo "$line" >> "$RESULTS/summary.txt"
done
exit $status
