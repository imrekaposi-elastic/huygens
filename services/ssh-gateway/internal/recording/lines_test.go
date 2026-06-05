package recording

import (
	"os"
	"path/filepath"
	"testing"
)

func TestStripANSI(t *testing.T) {
	raw := "\u001b]0;huygens@localhost:~\u0007\u001b[?2004h[huygens@localhost ~]$ ls\r\n"
	plain := StripANSI(raw)
	if plain != "[huygens@localhost ~]$ ls" {
		t.Fatalf("unexpected plain: %q", plain)
	}
}

func TestReadCastLines(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "test.cast")
	content := `{"version":2,"width":120,"height":32,"timestamp":1000}
[1000.1,"i","ls\r"]
[1000.2,"o","l"]
[1000.3,"o","s\r\n"]
[1000.4,"o","\u001b[32mok\u001b[0m\r\n"]
`
	if err := os.WriteFile(path, []byte(content), 0o640); err != nil {
		t.Fatal(err)
	}

	lines, err := ReadCastLines(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(lines) != 3 {
		t.Fatalf("expected 3 lines, got %d: %+v", len(lines), lines)
	}
	if lines[0].Stream != "i" || lines[0].Plaintext != "ls" {
		t.Fatalf("unexpected input line: %+v", lines[0])
	}
	if lines[1].Stream != "o" || lines[1].Plaintext != "ls" {
		t.Fatalf("unexpected output line: %+v", lines[1])
	}
	if lines[2].Plaintext != "ok" {
		t.Fatalf("unexpected ansi-stripped output: %+v", lines[2])
	}
}

func TestReadCastLinesBackspace(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "test.cast")
	content := `{"version":2,"width":120,"height":32,"timestamp":1000}
[1000.1,"i","u"]
[1000.2,"i","\u007f"]
[1000.3,"i","it\r"]
`
	if err := os.WriteFile(path, []byte(content), 0o640); err != nil {
		t.Fatal(err)
	}
	lines, err := ReadCastLines(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(lines) != 1 {
		t.Fatalf("expected 1 line, got %d: %+v", len(lines), lines)
	}
	if lines[0].Plaintext != "it" {
		t.Fatalf("expected edited command 'it', got %q", lines[0].Plaintext)
	}
}
