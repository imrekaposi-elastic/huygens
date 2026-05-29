package session

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestSaveLoadSession(t *testing.T) {
	dir := t.TempDir()
	sess := &Session{
		ID:             "abc-123",
		OrganizationID: "org-1",
		ProjectID:      "proj-1",
		VMName:         "web-01",
		UserID:         "user-1",
		Status:         "active",
		StartedAt:      time.Now().UTC(),
		RecordingPath:  filepath.Join(dir, "abc-123.cast"),
	}
	if err := Save(dir, sess); err != nil {
		t.Fatalf("save: %v", err)
	}
	loaded, ok := Load(dir, "abc-123")
	if !ok {
		t.Fatal("expected session to load")
	}
	if loaded.VMName != "web-01" {
		t.Fatalf("got vm %q", loaded.VMName)
	}
	all, err := LoadAll(dir)
	if err != nil {
		t.Fatalf("load all: %v", err)
	}
	if len(all) != 1 {
		t.Fatalf("expected 1 session, got %d", len(all))
	}
	if _, err := os.Stat(metaPath(dir, "abc-123")); err != nil {
		t.Fatalf("meta file missing: %v", err)
	}
}
