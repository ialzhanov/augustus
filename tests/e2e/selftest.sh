#!/bin/sh
# Tests the end-to-end test tool itself: each part must fail when the feature that
# it protects breaks. Run it after a change to src/game/e2e*.c, the test hooks or run.sh.
# Usage: tests/e2e/selftest.sh [--slow]
# --slow also builds the code with the seam bug of 2b6e0ca02 and expects the seam case
# to fail (about 5 minutes; it changes src/core/image_hd.c and restores it).

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BUILD=$ROOT/build-e2e
BIN=$BUILD/augustus.app/Contents/MacOS/augustus
DATA=${C3_DATA:-$HOME/caesar3}
RUN=$ROOT/tests/e2e/run.sh
SLOW=0
[ "$1" = "--slow" ] && SLOW=1

TMP=$(mktemp -d)
cleanup() {
    rm -rf "$TMP"
}
trap cleanup EXIT

failures=0
pass() {
    echo "PASS $1"
}
fail() {
    echo "FAIL $1: $2"
    failures=$((failures + 1))
}

# Runs a command with a time limit. macOS has no timeout command.
limit() {
    perl -e 'alarm shift; exec @ARGV' "$@"
}

# ---------------------------------------------------------------- unit tests

if [ -x "$BUILD/e2e_logic_test" ]; then
    if out=$("$BUILD/e2e_logic_test"); then
        pass "unit tests ($(echo "$out" | tail -n 1))"
    else
        fail "unit tests" "$(echo "$out" | grep FAIL | head -n 3)"
    fi
else
    fail "unit tests" "no $BUILD/e2e_logic_test: build with cmake -DE2E_TESTS=ON"
fi

# ---------------------------------------------------------------- run.sh with a fake binary

# The fake binary reads these lines of the case file:
#   # fake-exit: <code>    the exit code
#   # fake-sleep: <s>      wait before the exit
#   # fake-random          write a state dump that is different in each run
FAKE=$TMP/fake_augustus
cat > "$FAKE" <<'EOF'
#!/bin/sh
case_file=$2
out=$4
name=$(basename "$case_file" .txt)
mkdir -p "$out/$name"
echo "fake log of $name" > "$out/$name/log.txt"
grep -q '^# fake-random' "$case_file" && echo "$$ $(date +%s%N)" > "$out/$name/state_end.json"
sleep_time=$(sed -n 's/^# fake-sleep: *//p' "$case_file")
[ -n "$sleep_time" ] && sleep "$sleep_time"
exit "$(sed -n 's/^# fake-exit: *//p' "$case_file")"
EOF
chmod +x "$FAKE"
mkdir -p "$TMP/fake/cases"
fake_case() {
    printf '%s\n' "$@" > "$TMP/fake/cases/$1.txt.tmp"
    tail -n +2 "$TMP/fake/cases/$1.txt.tmp" > "$TMP/fake/cases/$1.txt"
    rm "$TMP/fake/cases/$1.txt.tmp"
}
fake_case pass_ok '# expect: pass' '# fake-exit: 0'
fake_case pass_exit_1 '# expect: pass' '# fake-exit: 1'
fake_case fail_ok '# expect: fail' '# fake-exit: 1'
fake_case error_ok '# expect: error' '# fake-exit: 2'
fake_case error_exit_1 '# expect: error' '# fake-exit: 1'
fake_case no_expect '# fake-exit: 0'
fake_case log_ok '# expect: pass' '# expect-log: fake log of' '# fake-exit: 0'
fake_case log_missing '# expect: pass' '# expect-log: a text that is not in the log' '# fake-exit: 0'
fake_case file_missing '# expect: pass' '# expect-file: state_end.json' '# fake-exit: 0'
fake_case slow '# expect: pass' '# fake-sleep: 10' '# fake-exit: 0'
fake_case random '# expect: pass' '# fake-random' '# fake-exit: 0'

# Runs run.sh with the fake binary. $1 = PASS or FAIL (the expected first word), $2 = text in the output
expect_run() {
    want=$1
    text=$2
    shift 2
    out=$(E2E_BIN=$FAKE E2E_CASES=$TMP/fake/cases E2E_RESULTS=$TMP/fake/results E2E_TIMEOUT=2 \
        "$RUN" "$@" 2>&1)
    if [ "${out#$want}" != "$out" ] && echo "$out" | grep -qF -- "$text"; then
        pass "run.sh $*: $want"
    else
        fail "run.sh $*" "expected '$want ... $text', got: $out"
    fi
}
expect_run PASS "pass_ok" pass_ok
expect_run FAIL "expected pass, got exit 1" pass_exit_1
expect_run PASS "fail_ok" fail_ok
expect_run PASS "error_ok" error_ok
expect_run FAIL "expected error, got exit 1" error_exit_1
expect_run FAIL "no '# expect: pass|fail|error' line" no_expect
expect_run PASS "log_ok" log_ok
expect_run FAIL "log.txt does not have: a text that is not in the log" log_missing
expect_run FAIL "no file state_end.json" file_missing
expect_run FAIL "timeout or signal" slow
expect_run PASS "random" random
expect_run FAIL "state_end.json differs" --twice random
out=$(E2E_BIN=$FAKE E2E_CASES=$TMP/fake/cases "$RUN" --update-images 2>&1)
if [ $? -eq 2 ] && echo "$out" | grep -q "needs the names of the cases"; then
    pass "run.sh --update-images with no case names: refused"
else
    fail "run.sh --update-images with no case names" "$out"
fi

# ---------------------------------------------------------------- the real binary

if [ ! -x "$BIN" ]; then
    fail "binary" "no $BIN"
    echo "$failures failed"
    exit 1
fi
export MallocPreScribble=1 MallocScribble=1

# A test tree in the temporary folder: the binary finds saves/, hd/ and images/ next to cases/
make_tree() {
    tree=$TMP/$1
    mkdir -p "$tree/cases" "$tree/images"
    ln -s "$ROOT/tests/e2e/saves" "$tree/saves"
    [ "$2" = "with_hd" ] && ln -s "$ROOT/tests/e2e/hd" "$tree/hd"
    echo "$tree"
}
TREE=$(make_tree tree with_hd)
NO_HD=$(make_tree no_hd without_hd)

cat > "$TREE/cases/seed_a.txt" <<'EOF'
load_map Caesarea
seed 1
run ticks 2000
dump end
EOF
cp "$TREE/cases/seed_a.txt" "$TREE/cases/seed_b.txt"
sed 's/^seed 1$/seed 2/' "$TREE/cases/seed_a.txt" > "$TREE/cases/seed_c.txt"
cat > "$TREE/cases/approve.txt" <<'EOF'
# expect: pass
load flat_grass.svx
capture grass camera 40 40 zoom 100 size 64 64
check image grass
EOF
cat > "$TREE/cases/long.txt" <<'EOF'
load_map Caesarea
run ticks 2000000
EOF
cat > "$NO_HD/cases/hd.txt" <<'EOF'
load flat_grass.svx
capture grass camera 40 40 zoom 100 size 64 64
check hd grass terrain_grass_1
EOF

# Runs the binary on a case of a tree. Prints the exit code.
run_bin() {
    limit 120 "$BIN" --test "$1" --out "$TMP/out" "$DATA" > /dev/null 2>&1
    echo $?
}

# The paths of the test file and the results folder can be relative
code=$(cd "$TREE" && limit 120 "$BIN" --test cases/seed_a.txt --out out "$DATA" > /dev/null 2>&1; echo $?)
if [ "$code" = 0 ] && [ -f "$TREE/out/seed_a/state_end.json" ]; then
    pass "relative --test and --out paths"
else
    fail "relative --test and --out paths" "exit $code"
fi

# The seed changes the state, and the same seed gives the same state
run_bin "$TREE/cases/seed_b.txt" > /dev/null
run_bin "$TREE/cases/seed_c.txt" > /dev/null
if cmp -s "$TREE/out/seed_a/state_end.json" "$TMP/out/seed_b/state_end.json" &&
    ! cmp -s "$TREE/out/seed_a/state_end.json" "$TMP/out/seed_c/state_end.json"; then
    pass "seed: the same seed gives the same state, another seed another state"
else
    fail "seed" "compare $TMP/out/seed_a, seed_b and seed_c"
fi

# A data folder that does not exist stops the test with exit 2 and no message box
code=$(limit 30 "$BIN" --test "$TREE/cases/seed_a.txt" --out "$TMP/out" /no/such/folder > /dev/null 2>&1; echo $?)
[ "$code" = 2 ] && pass "bad data folder: exit 2" || fail "bad data folder" "exit $code (142 is the time limit: a message box waits)"

# The software renderer stops the test with exit 2
code=$(SDL_RENDER_DRIVER=software run_bin "$TREE/cases/seed_a.txt")
if [ "$code" = 2 ] && grep -q "software renderer" "$TMP/out/seed_a/log.txt"; then
    pass "software renderer: exit 2"
else
    fail "software renderer" "exit $code"
fi

# A crash stops the test with no message box and with an exit code that is not 0, 1 or 2
limit 60 "$BIN" --test "$TREE/cases/long.txt" --out "$TMP/out" "$DATA" > /dev/null 2>&1 &
pid=$!
sleep 8
kill -SEGV "$pid" 2>/dev/null
wait "$pid" 2>/dev/null
code=$?
if [ "$code" -gt 2 ] && [ "$code" != 142 ]; then
    pass "crash: exit $code, no message box"
else
    fail "crash" "exit $code (142 is the time limit: a message box waits)"
fi

# --update-images writes the approved image, and the next run compares with it
E2E_CASES=$TREE/cases E2E_RESULTS=$TMP/results "$RUN" --update-images approve > /dev/null
if [ -f "$TREE/images/approve/grass.png" ] &&
    E2E_CASES=$TREE/cases E2E_RESULTS=$TMP/results "$RUN" approve > /dev/null 2>&1; then
    pass "--update-images writes the approved image"
else
    fail "--update-images" "no $TREE/images/approve/grass.png or the next run failed"
fi

# With no HD folder, the HD check fails
code=$(run_bin "$NO_HD/cases/hd.txt")
[ "$code" = 1 ] && pass "no HD folder: the HD check fails" || fail "no HD folder" "exit $code"

# The test mode does not write the user options
for file in "$DATA/config/augustus.ini" "$DATA/config/c3.inf" "$DATA/augustus.ini" "$DATA/c3.inf"; do
    [ -f "$file" ] || continue
    before=$(stat -f %m "$file")
    run_bin "$TREE/cases/seed_a.txt" > /dev/null
    after=$(stat -f %m "$file")
    [ "$before" = "$after" ] && pass "user file not written: $file" || fail "user file written" "$file"
done

# A normal build has no test code
NORMAL=$ROOT/build/augustus.app/Contents/MacOS/augustus
if [ -x "$NORMAL" ]; then
    count=$(nm "$NORMAL" | grep -c "e2e_run\|platform_renderer_e2e\|random_set_test_seed")
    [ "$count" = 0 ] && pass "normal build has no test code" || fail "normal build" "$count test symbols"
fi

# ---------------------------------------------------------------- --slow: the real seam bug

if [ "$SLOW" = 1 ]; then
    if ! git -C "$ROOT" diff --quiet -- src/core/image_hd.c; then
        fail "seam bug" "src/core/image_hd.c has local changes; commit or remove them first"
    else
        restore() {
            git -C "$ROOT" checkout -- src/core/image_hd.c
            cmake --build "$BUILD" -j8 > /dev/null 2>&1
            cleanup
        }
        trap restore EXIT
        git -C "$ROOT" show 2b6e0ca02 -- src/core/image_hd.c | git -C "$ROOT" apply -R
        if cmake --build "$BUILD" -j8 > "$TMP/build.log" 2>&1; then
            out=$(E2E_RESULTS=$TMP/seam "$RUN" seams_flat_grass 2>&1)
            if [ "${out#FAIL}" != "$out" ] && echo "$out" | grep -q "seam lines"; then
                pass "seam bug of 2b6e0ca02: seams_flat_grass fails"
            else
                fail "seam bug of 2b6e0ca02" "seams_flat_grass did not fail: $out"
            fi
        else
            fail "seam bug of 2b6e0ca02" "the build with the bug failed: $TMP/build.log"
        fi
    fi
fi

echo "$failures failed"
[ "$failures" = 0 ]
