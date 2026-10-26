// Command server serves the HD sprite viewer with a local API: sprite data, attempts, install, uninstall and
// generation jobs (blender/make.sh or blender/terrain_make.sh, at most -workers renders at a time).
//
//	cd tools/hd_sprites/viewer/server && go run .      (then open http://127.0.0.1:8642)
//
// It listens on 127.0.0.1 only. Rendering, checks and attempt files stay in the pipeline scripts; the server
// runs them and copies attempt files to the game.
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"sync"
	"time"
)

var (
	addr    = flag.String("addr", "127.0.0.1:8642", "listen address (keep it on 127.0.0.1)")
	rootDir = flag.String("root", "", "tools/hd_sprites directory (default: found from the working directory)")
	python  = flag.String("python", filepath.Join(os.Getenv("HOME"), ".local/share/uv/tools/mflux/bin/python"), "Python with Pillow and numpy")
	gameHD  = flag.String("game-hd", filepath.Join(os.Getenv("HOME"), "caesar3/hd"), "folder the game loads HD sprites from")
	workers = flag.Int("workers", 2, "renders at the same time (one GPU: keep 1-2)")
)

var climates = []string{"c3", "c3_north", "c3_south"}

type scriptRange struct {
	From   int    `json:"from"`
	To     int    `json:"to"`
	Script string `json:"script"`
}

type server struct {
	root    string
	scripts []scriptRange

	dataMu   sync.Mutex
	dataJSON []byte
	dataAt   time.Time

	jobsMu sync.Mutex
	jobs   []*job
	queue  chan *job
	nextID int
}

type job struct {
	ID      int       `json:"id"`
	Sprite  int       `json:"sprite"`
	Seed    int       `json:"seed"`
	Script  string    `json:"script"`
	Status  string    `json:"status"` // queued, running, done, failed
	Queued  time.Time `json:"queued"`
	Started time.Time `json:"started,omitzero"`
	Ended   time.Time `json:"ended,omitzero"`
	Log     string    `json:"log"`
}

func main() {
	flag.Parse()
	root, err := findRoot(*rootDir)
	if err != nil {
		log.Fatal(err)
	}
	s := &server{root: root, queue: make(chan *job, 1000)}
	if err := s.loadScripts(); err != nil {
		log.Fatal(err)
	}
	for i := 0; i < *workers; i++ {
		go s.worker()
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, r *http.Request) { http.Redirect(w, r, "/viewer/", http.StatusFound) })
	mux.Handle("GET /", noCache(http.FileServer(http.Dir(root))))
	mux.HandleFunc("GET /api/data", s.handleData)
	mux.HandleFunc("GET /api/jobs", s.handleJobs)
	mux.HandleFunc("POST /api/generate", s.handleGenerate)
	mux.HandleFunc("POST /api/install", s.handleInstall)
	mux.HandleFunc("POST /api/uninstall", s.handleUninstall)
	log.Printf("viewer: http://%s  (root %s)", *addr, root)
	log.Fatal(http.ListenAndServe(*addr, mux))
}

// findRoot returns the tools/hd_sprites directory: the flag, or the first match from the working directory up.
func findRoot(flagValue string) (string, error) {
	if flagValue != "" {
		return filepath.Abs(flagValue)
	}
	dir, _ := os.Getwd()
	for {
		for _, c := range []string{dir, filepath.Join(dir, "tools", "hd_sprites")} {
			if _, err := os.Stat(filepath.Join(c, "blender", "scripts.json")); err == nil {
				return c, nil
			}
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", errors.New("tools/hd_sprites not found: run from the repository or pass -root")
		}
		dir = parent
	}
}

func noCache(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store") // renders change in place
		h.ServeHTTP(w, r)
	})
}

func (s *server) loadScripts() error {
	b, err := os.ReadFile(filepath.Join(s.root, "blender", "scripts.json"))
	if err != nil {
		return err
	}
	var f struct {
		Scripts []scriptRange `json:"scripts"`
	}
	if err := json.Unmarshal(b, &f); err != nil {
		return fmt.Errorf("scripts.json: %w", err)
	}
	s.scripts = f.Scripts
	return nil
}

func (s *server) scriptFor(id int) string {
	for _, r := range s.scripts {
		if id >= r.From && id <= r.To {
			return r.Script
		}
	}
	return ""
}

// climatesFor: terrain is coloured by the central climate's originals, so it installs only to c3.
func (s *server) climatesFor(id int) []string {
	if s.scriptFor(id) == "terrain" {
		return climates[:1]
	}
	return climates
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func fail(w http.ResponseWriter, code int, err error) {
	writeJSON(w, code, map[string]string{"error": err.Error()})
}

// handleData runs viewer/build_viewer.py (it rewrites data.js) and returns the data as JSON.
func (s *server) handleData(w http.ResponseWriter, r *http.Request) {
	s.dataMu.Lock()
	defer s.dataMu.Unlock()
	if s.dataJSON == nil || time.Since(s.dataAt) > 2*time.Second {
		cmd := exec.Command(*python, filepath.Join(s.root, "viewer", "build_viewer.py"))
		cmd.Dir = filepath.Join(s.root, "viewer")
		if out, err := cmd.CombinedOutput(); err != nil {
			fail(w, http.StatusInternalServerError, fmt.Errorf("build_viewer.py: %v: %s", err, out))
			return
		}
		js, err := os.ReadFile(filepath.Join(s.root, "viewer", "data.js"))
		if err != nil {
			fail(w, http.StatusInternalServerError, err)
			return
		}
		start, end := bytes.IndexByte(js, '{'), bytes.LastIndexByte(js, '}')
		if start < 0 || end < start {
			fail(w, http.StatusInternalServerError, errors.New("data.js has no JSON object"))
			return
		}
		s.dataJSON, s.dataAt = js[start:end+1], time.Now()
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write(s.dataJSON)
}

func readRequest(r *http.Request, v any) error {
	return json.NewDecoder(io.LimitReader(r.Body, 1<<16)).Decode(v)
}

func (s *server) handleGenerate(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID   int  `json:"id"`
		Seed *int `json:"seed"`
	}
	if err := readRequest(r, &req); err != nil {
		fail(w, http.StatusBadRequest, err)
		return
	}
	script := s.scriptFor(req.ID)
	if script == "" {
		fail(w, http.StatusBadRequest, fmt.Errorf("sprite %d has no script in blender/scripts.json", req.ID))
		return
	}
	seed := rand.Intn(1_000_000) + 1
	if req.Seed != nil {
		seed = *req.Seed
	}
	s.jobsMu.Lock()
	defer s.jobsMu.Unlock()
	for _, j := range s.jobs {
		if j.Sprite == req.ID && (j.Status == "queued" || j.Status == "running") {
			fail(w, http.StatusConflict, fmt.Errorf("sprite %d already has job %d (%s)", req.ID, j.ID, j.Status))
			return
		}
	}
	s.nextID++
	j := &job{ID: s.nextID, Sprite: req.ID, Seed: seed, Script: script, Status: "queued", Queued: time.Now()}
	s.jobs = append(s.jobs, j)
	s.queue <- j
	writeJSON(w, http.StatusAccepted, j)
}

func (s *server) handleJobs(w http.ResponseWriter, r *http.Request) {
	s.jobsMu.Lock()
	defer s.jobsMu.Unlock()
	out := make([]job, 0, len(s.jobs))
	for i := len(s.jobs) - 1; i >= 0 && len(out) < 50; i-- {
		out = append(out, *s.jobs[i])
	}
	writeJSON(w, http.StatusOK, out)
}

func (s *server) worker() {
	for j := range s.queue {
		s.withJobs(func() { j.Status, j.Started = "running", time.Now() })
		var cmd *exec.Cmd
		if j.Script == "terrain" {
			cmd = exec.Command("bash", "terrain_make.sh", strconv.Itoa(j.Sprite))
		} else {
			cmd = exec.Command("bash", "make.sh", j.Script, strconv.Itoa(j.Sprite))
		}
		cmd.Dir = filepath.Join(s.root, "blender")
		cmd.Env = append(os.Environ(), "C3_SEED="+strconv.Itoa(j.Seed))
		out, err := cmd.CombinedOutput()
		s.withJobs(func() {
			j.Ended, j.Log = time.Now(), tail(string(out), 4000)
			j.Status = "done"
			if err != nil {
				j.Status = "failed"
			}
		})
		s.dataMu.Lock()
		s.dataJSON = nil // new attempt: rebuild the data on the next request
		s.dataMu.Unlock()
	}
}

func (s *server) withJobs(f func()) {
	s.jobsMu.Lock()
	defer s.jobsMu.Unlock()
	f()
}

func tail(s string, n int) string {
	if len(s) > n {
		return "…" + s[len(s)-n:]
	}
	return s
}

type attemptMeta struct {
	Seed   int                       `json:"seed"`
	Script string                    `json:"script"`
	Checks map[string][2]any `json:"checks"`
}

func (s *server) attemptDir(id int, stamp string) (string, error) {
	if stamp == "" || filepath.Base(stamp) != stamp || stamp == "." || stamp == ".." {
		return "", fmt.Errorf("invalid attempt %q", stamp)
	}
	d := filepath.Join(s.root, "blender", "out", "attempts", strconv.Itoa(id), stamp)
	if _, err := os.Stat(filepath.Join(d, "meta.json")); err != nil {
		return "", fmt.Errorf("sprite %d has no attempt %s", id, stamp)
	}
	return d, nil
}

// failedChecks lists the failed checks of an attempt (none when every check passed).
func failedChecks(dir string) ([]string, error) {
	b, err := os.ReadFile(filepath.Join(dir, "meta.json"))
	if err != nil {
		return nil, err
	}
	var m attemptMeta
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	if len(m.Checks) == 0 {
		return []string{"no check results"}, nil
	}
	var bad []string
	for k, v := range m.Checks {
		if ok, _ := v[0].(bool); !ok {
			bad = append(bad, k)
		}
	}
	sort.Strings(bad)
	return bad, nil
}

func copyFile(src, dst string) error {
	b, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	tmp := dst + ".tmp"
	if err := os.WriteFile(tmp, b, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, dst) // the game never reads a half-written file
}

func (s *server) handleInstall(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID    int    `json:"id"`
		Stamp string `json:"stamp"`
		Force bool   `json:"force"`
	}
	if err := readRequest(r, &req); err != nil {
		fail(w, http.StatusBadRequest, err)
		return
	}
	dir, err := s.attemptDir(req.ID, req.Stamp)
	if err != nil {
		fail(w, http.StatusNotFound, err)
		return
	}
	bad, err := failedChecks(dir)
	if err != nil {
		fail(w, http.StatusInternalServerError, err)
		return
	}
	if len(bad) > 0 && !req.Force {
		fail(w, http.StatusConflict, fmt.Errorf("attempt %s fails checks: %v (install with force to override)", req.Stamp, bad))
		return
	}
	id := strconv.Itoa(req.ID)
	for _, c := range s.climatesFor(req.ID) {
		d := filepath.Join(*gameHD, c)
		if err := os.MkdirAll(d, 0o755); err != nil {
			fail(w, http.StatusInternalServerError, err)
			return
		}
		if err := copyFile(filepath.Join(dir, id+".png"), filepath.Join(d, id+".png")); err != nil {
			fail(w, http.StatusInternalServerError, err)
			return
		}
		top := filepath.Join(dir, id+"_top.png")
		var topErr error
		if _, statErr := os.Stat(top); statErr == nil {
			topErr = copyFile(top, filepath.Join(d, id+"_top.png"))
		} else if rmErr := os.Remove(filepath.Join(d, id+"_top.png")); !errors.Is(rmErr, os.ErrNotExist) {
			topErr = rmErr // an attempt without a top part: remove an older _top.png
		}
		if err := topErr; err != nil {
			fail(w, http.StatusInternalServerError, err)
			return
		}
	}
	s.invalidate()
	writeJSON(w, http.StatusOK, map[string]any{"installed": req.ID, "stamp": req.Stamp, "climates": s.climatesFor(req.ID), "failed_checks": bad})
}

func (s *server) handleUninstall(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID int `json:"id"`
	}
	if err := readRequest(r, &req); err != nil {
		fail(w, http.StatusBadRequest, err)
		return
	}
	removed := 0
	for _, c := range climates {
		for _, name := range []string{strconv.Itoa(req.ID) + ".png", strconv.Itoa(req.ID) + "_top.png"} {
			if err := os.Remove(filepath.Join(*gameHD, c, name)); err == nil {
				removed++
			} else if !errors.Is(err, os.ErrNotExist) {
				fail(w, http.StatusInternalServerError, err)
				return
			}
		}
	}
	s.invalidate()
	writeJSON(w, http.StatusOK, map[string]int{"uninstalled": req.ID, "files": removed})
}

func (s *server) invalidate() {
	s.dataMu.Lock()
	s.dataJSON = nil
	s.dataMu.Unlock()
}
