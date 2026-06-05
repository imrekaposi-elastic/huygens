package recording

import (
	"os"
	"testing"
)

func TestWriterRoundTrip(t *testing.T) {
	dir := t.TempDir()
	w, err := NewWriter(dir, "sess-1")
	if err != nil {
		t.Fatalf("NewWriter: %v", err)
	}
	if err := w.WriteOutput([]byte("output")); err != nil {
		t.Fatalf("WriteOutput: %v", err)
	}
	if err := w.WriteInput([]byte("input")); err != nil {
		t.Fatalf("WriteInput: %v", err)
	}
	path, err := w.Close()
	if err != nil {
		t.Fatalf("Close: %v", err)
	}
	if w.Path() != path {
		t.Fatalf("path = %q", w.Path())
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(data) == 0 {
		t.Fatal("expected cast file content")
	}
}
