package recording

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type Writer struct {
	path string
	file *os.File
	mu   sync.Mutex
}

func NewWriter(dir, sessionID string) (*Writer, error) {
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return nil, err
	}
	path := filepath.Join(dir, sessionID+".cast")
	f, err := os.Create(path)
	if err != nil {
		return nil, err
	}
	header := map[string]any{
		"version":   2,
		"width":     120,
		"height":    32,
		"timestamp": time.Now().Unix(),
	}
	line, _ := json.Marshal(header)
	if _, err := f.Write(append(line, '\n')); err != nil {
		_ = f.Close()
		return nil, err
	}
	return &Writer{path: path, file: f}, nil
}

func (w *Writer) WriteOutput(data []byte) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.file == nil {
		return fmt.Errorf("recording closed")
	}
	event := []any{time.Now().UnixNano() / 1e9, "o", string(data)}
	line, err := json.Marshal(event)
	if err != nil {
		return err
	}
	_, err = w.file.Write(append(line, '\n'))
	return err
}

func (w *Writer) WriteInput(data []byte) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.file == nil {
		return fmt.Errorf("recording closed")
	}
	event := []any{time.Now().UnixNano() / 1e9, "i", string(data)}
	line, err := json.Marshal(event)
	if err != nil {
		return err
	}
	_, err = w.file.Write(append(line, '\n'))
	return err
}

func (w *Writer) Close() (string, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.file == nil {
		return w.path, nil
	}
	err := w.file.Close()
	w.file = nil
	return w.path, err
}

func (w *Writer) Path() string {
	return w.path
}
