package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

// newTestServer makes a pipeline root with scripts.json and one attempt per entry of attempts (stamp -> checks ok).
func newTestServer(t *testing.T, sprite int, attempts map[string]bool, withTop map[string]bool) (*server, string) {
	t.Helper()
	root := t.TempDir()
	game := t.TempDir()
	*gameHD = game
	must(t, os.MkdirAll(filepath.Join(root, "blender"), 0o755))
	must(t, os.WriteFile(filepath.Join(root, "blender", "scripts.json"),
		[]byte(`{"scripts":[{"from":2779,"to":2782,"script":"tent.py"},{"from":306,"to":363,"script":"terrain"}]}`), 0o644))
	for stamp, ok := range attempts {
		d := filepath.Join(root, "blender", "out", "attempts", itoa(sprite), stamp)
		must(t, os.MkdirAll(d, 0o755))
		must(t, os.WriteFile(filepath.Join(d, itoa(sprite)+".png"), []byte("png-"+stamp), 0o644))
		if withTop[stamp] {
			must(t, os.WriteFile(filepath.Join(d, itoa(sprite)+"_top.png"), []byte("top-"+stamp), 0o644))
		}
		meta, _ := json.Marshal(map[string]any{"seed": 1, "script": "tent.py",
			"checks": map[string][2]any{"size": {true, "ok"}, "colour": {ok, "dE"}}})
		must(t, os.WriteFile(filepath.Join(d, "meta.json"), meta, 0o644))
	}
	s := &server{root: root, queue: make(chan *job, 10)}
	must(t, s.loadScripts())
	return s, game
}

func must(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func itoa(i int) string { b, _ := json.Marshal(i); return string(b) }

func post(h http.HandlerFunc, body any) *httptest.ResponseRecorder {
	b, _ := json.Marshal(body)
	rec := httptest.NewRecorder()
	h(rec, httptest.NewRequest("POST", "/", bytes.NewReader(b)))
	return rec
}

func TestInstallRefusesFailingAttempt(t *testing.T) {
	s, game := newTestServer(t, 2780, map[string]bool{"bad": false}, nil)
	if rec := post(s.handleInstall, map[string]any{"id": 2780, "stamp": "bad"}); rec.Code != http.StatusConflict {
		t.Fatalf("failing attempt installed: %d %s", rec.Code, rec.Body)
	}
	if _, err := os.Stat(filepath.Join(game, "c3", "2780.png")); err == nil {
		t.Fatal("file copied although the checks failed")
	}
	if rec := post(s.handleInstall, map[string]any{"id": 2780, "stamp": "bad", "force": true}); rec.Code != http.StatusOK {
		t.Fatalf("forced install refused: %d %s", rec.Code, rec.Body)
	}
}

func TestInstallCopiesToAllClimatesAndRemovesOldTop(t *testing.T) {
	s, game := newTestServer(t, 2780, map[string]bool{"a": true, "b": true}, map[string]bool{"a": true})
	if rec := post(s.handleInstall, map[string]any{"id": 2780, "stamp": "a"}); rec.Code != http.StatusOK {
		t.Fatal(rec.Body)
	}
	for _, c := range climates {
		if b, _ := os.ReadFile(filepath.Join(game, c, "2780_top.png")); string(b) != "top-a" {
			t.Fatalf("%s: top part not installed", c)
		}
	}
	// attempt b has no top part: an older _top.png must go, or the game draws the old top over the new sprite
	if rec := post(s.handleInstall, map[string]any{"id": 2780, "stamp": "b"}); rec.Code != http.StatusOK {
		t.Fatal(rec.Body)
	}
	for _, c := range climates {
		if b, _ := os.ReadFile(filepath.Join(game, c, "2780.png")); string(b) != "png-b" {
			t.Fatalf("%s: sprite not replaced", c)
		}
		if _, err := os.Stat(filepath.Join(game, c, "2780_top.png")); err == nil {
			t.Fatalf("%s: old _top.png left behind", c)
		}
	}
}

func TestTerrainInstallsOnlyCentralClimate(t *testing.T) {
	s, game := newTestServer(t, 306, map[string]bool{"a": true}, nil)
	if rec := post(s.handleInstall, map[string]any{"id": 306, "stamp": "a"}); rec.Code != http.StatusOK {
		t.Fatal(rec.Body)
	}
	if _, err := os.Stat(filepath.Join(game, "c3", "306.png")); err != nil {
		t.Fatal("not installed to c3")
	}
	for _, c := range climates[1:] {
		if _, err := os.Stat(filepath.Join(game, c, "306.png")); err == nil {
			t.Fatalf("terrain installed to %s (other climates have other grass)", c)
		}
	}
}

func TestAttemptNameCannotLeaveTheFolder(t *testing.T) {
	s, _ := newTestServer(t, 2780, map[string]bool{"a": true}, nil)
	for _, stamp := range []string{"../../x", "..", ".", "", "a/../a"} {
		if rec := post(s.handleInstall, map[string]any{"id": 2780, "stamp": stamp}); rec.Code == http.StatusOK {
			t.Fatalf("attempt name %q accepted", stamp)
		}
	}
}

func TestUninstallRemovesEveryClimate(t *testing.T) {
	s, game := newTestServer(t, 2780, map[string]bool{"a": true}, map[string]bool{"a": true})
	post(s.handleInstall, map[string]any{"id": 2780, "stamp": "a"})
	rec := post(s.handleUninstall, map[string]any{"id": 2780})
	if rec.Code != http.StatusOK {
		t.Fatal(rec.Body)
	}
	for _, c := range climates {
		for _, f := range []string{"2780.png", "2780_top.png"} {
			if _, err := os.Stat(filepath.Join(game, c, f)); err == nil {
				t.Fatalf("%s/%s not removed", c, f)
			}
		}
	}
}

func TestGenerateNeedsScriptAndOneJobPerSprite(t *testing.T) {
	s, _ := newTestServer(t, 2780, nil, nil)
	if rec := post(s.handleGenerate, map[string]any{"id": 5}); rec.Code != http.StatusBadRequest {
		t.Fatalf("sprite without a script queued: %d", rec.Code)
	}
	if rec := post(s.handleGenerate, map[string]any{"id": 2780}); rec.Code != http.StatusAccepted {
		t.Fatalf("job not queued: %d %s", rec.Code, rec.Body)
	}
	if rec := post(s.handleGenerate, map[string]any{"id": 2780}); rec.Code != http.StatusConflict {
		t.Fatalf("second job for the same sprite queued: %d", rec.Code)
	}
}
