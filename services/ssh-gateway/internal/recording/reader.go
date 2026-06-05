package recording

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

type CastEvent struct {
	Sequence  int
	Timestamp float64
	Stream    string
	Data      string
}

func ReadCastEvents(path string) ([]CastEvent, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	if !scanner.Scan() {
		if err := scanner.Err(); err != nil {
			return nil, err
		}
		return nil, fmt.Errorf("empty cast file")
	}

	events := make([]CastEvent, 0)
	seq := 0
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var raw []json.RawMessage
		if err := json.Unmarshal([]byte(line), &raw); err != nil || len(raw) < 3 {
			continue
		}
		var ts float64
		var stream string
		var data string
		if err := json.Unmarshal(raw[0], &ts); err != nil {
			continue
		}
		if err := json.Unmarshal(raw[1], &stream); err != nil {
			continue
		}
		if err := json.Unmarshal(raw[2], &data); err != nil {
			continue
		}
		if stream != "i" && stream != "o" {
			continue
		}
		events = append(events, CastEvent{
			Sequence:  seq,
			Timestamp: ts,
			Stream:    stream,
			Data:      data,
		})
		seq++
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return events, nil
}
