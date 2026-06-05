package recording

import (
	"os"
	"path/filepath"
	"testing"
)

func TestReadCastEvents(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "test.cast")
	content := `{"version":2,"width":120,"height":32,"timestamp":1000}
[1000.5,"o","hello\r\n"]
[1000.6,"i","ls\r\n"]
[1000.7,"o","ok\r\n"]
`
	if err := os.WriteFile(path, []byte(content), 0o640); err != nil {
		t.Fatal(err)
	}

	events, err := ReadCastEvents(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(events) != 3 {
		t.Fatalf("expected 3 events, got %d", len(events))
	}
	if events[0].Stream != "o" || events[0].Data != "hello\r\n" {
		t.Fatalf("unexpected first event: %+v", events[0])
	}
	if events[1].Stream != "i" || events[1].Data != "ls\r\n" {
		t.Fatalf("unexpected second event: %+v", events[1])
	}
}
