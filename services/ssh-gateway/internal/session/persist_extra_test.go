package session

import (
	"os"
	"path/filepath"
	"testing"
)

func TestValidateRecordingPathAndDeleteFiles(t *testing.T) {
	dir := t.TempDir()
	id := "sess-99"
	recPath := RecordingPath(dir, id)
	if err := os.WriteFile(recPath, []byte("cast"), 0o640); err != nil {
		t.Fatalf("write cast: %v", err)
	}
	if err := ValidateRecordingPath(dir, id, recPath); err != nil {
		t.Fatalf("validate ok path: %v", err)
	}
	if err := ValidateRecordingPath(dir, id, filepath.Join(dir, "other.cast")); err == nil {
		t.Fatal("expected path validation error")
	}
	if err := DeleteFiles(dir, id); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := os.Stat(recPath); !os.IsNotExist(err) {
		t.Fatalf("cast still exists: %v", err)
	}
}

func TestLoadAllMissingDir(t *testing.T) {
	all, err := LoadAll(filepath.Join(t.TempDir(), "missing"))
	if err != nil {
		t.Fatalf("LoadAll: %v", err)
	}
	if all != nil {
		t.Fatalf("expected nil slice, got %v", all)
	}
}
