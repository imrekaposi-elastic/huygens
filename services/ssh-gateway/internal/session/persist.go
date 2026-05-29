package session

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func metaPath(dir, id string) string {
	return filepath.Join(dir, id+".meta.json")
}

func Save(dir string, sess *Session) error {
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return err
	}
	data, err := json.Marshal(sess)
	if err != nil {
		return err
	}
	tmp := metaPath(dir, sess.ID) + ".tmp"
	if err := os.WriteFile(tmp, data, 0o640); err != nil {
		return err
	}
	return os.Rename(tmp, metaPath(dir, sess.ID))
}

func Load(dir, id string) (*Session, bool) {
	data, err := os.ReadFile(metaPath(dir, id))
	if err != nil {
		return nil, false
	}
	var sess Session
	if err := json.Unmarshal(data, &sess); err != nil {
		return nil, false
	}
	return &sess, true
}

func LoadAll(dir string) ([]*Session, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	out := make([]*Session, 0)
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".meta.json") {
			continue
		}
		id := strings.TrimSuffix(e.Name(), ".meta.json")
		if sess, ok := Load(dir, id); ok {
			out = append(out, sess)
		}
	}
	return out, nil
}

func RecordingPath(dir, id string) string {
	return filepath.Join(dir, id+".cast")
}

func ValidateRecordingPath(dir, id, path string) error {
	want := RecordingPath(dir, id)
	absWant, err := filepath.Abs(want)
	if err != nil {
		return err
	}
	absPath, err := filepath.Abs(path)
	if err != nil {
		return err
	}
	if absPath != absWant {
		return fmt.Errorf("recording path outside session dir")
	}
	return nil
}

func DeleteFiles(dir, id string) error {
	_ = os.Remove(metaPath(dir, id))
	_ = os.Remove(RecordingPath(dir, id))
	return nil
}
