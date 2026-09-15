package main

import (
	"bufio"
	"os"
	"strings"
	"sync"
)

// postedState is the set of verdict keys already posted, persisted as one key
// per line in a file beside the verdicts. It is what makes a restart of
// `watch` not replay history and a second `post` of the same row a no-op.
type postedState struct {
	path string
	mu   sync.Mutex
	seen map[string]bool
}

func loadState(path string) (*postedState, error) {
	s := &postedState{path: path, seen: map[string]bool{}}
	f, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return s, nil
		}
		return nil, err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		k := strings.TrimSpace(sc.Text())
		if k != "" {
			s.seen[k] = true
		}
	}
	return s, sc.Err()
}

func (s *postedState) has(key string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.seen[key]
}

// mark records the key in memory and appends it to the file in one step, so
// a crash between the two cannot leave a posted verdict unrecorded.
func (s *postedState) mark(key string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.seen[key] {
		return nil
	}
	f, err := os.OpenFile(s.path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	if _, err := f.WriteString(key + "\n"); err != nil {
		return err
	}
	s.seen[key] = true
	return nil
}
