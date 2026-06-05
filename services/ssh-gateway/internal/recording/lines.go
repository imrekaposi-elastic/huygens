package recording

import (
	"regexp"
	"strings"
	"unicode/utf8"
)

var ansiEscape = regexp.MustCompile(`\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)|\x1b[PX^_][^\x1b]*\x1b\\`)

type CastLine struct {
	Sequence  int
	Timestamp float64
	Stream    string
	Raw       string
	Plaintext string
}

func StripANSI(raw string) string {
	stripped := ansiEscape.ReplaceAllString(raw, "")
	stripped = strings.ReplaceAll(stripped, "\r", "")
	return strings.TrimSpace(stripped)
}

func ReadCastLines(path string) ([]CastLine, error) {
	events, err := ReadCastEvents(path)
	if err != nil {
		return nil, err
	}

	lines := make([]CastLine, 0)
	seq := 0
	var inputBuf strings.Builder

	flushInput := func(ts float64) {
		text := strings.TrimSpace(inputBuf.String())
		inputBuf.Reset()
		if text == "" {
			return
		}
		lines = append(lines, CastLine{
			Sequence:  seq,
			Timestamp: ts,
			Stream:    "i",
			Raw:       text,
			Plaintext: text,
		})
		seq++
	}

	var outputBuf strings.Builder
	flushOutputLine := func(ts float64, rawLine string) {
		plain := StripANSI(rawLine)
		if plain == "" {
			return
		}
		lines = append(lines, CastLine{
			Sequence:  seq,
			Timestamp: ts,
			Stream:    "o",
			Raw:       rawLine,
			Plaintext: plain,
		})
		seq++
	}
	flushOutput := func(ts float64) {
		for {
			raw := outputBuf.String()
			if raw == "" {
				return
			}
			idx := strings.IndexAny(raw, "\n")
			if idx < 0 {
				plain := StripANSI(raw)
				outputBuf.Reset()
				if plain != "" {
					flushOutputLine(ts, raw)
				}
				return
			}
			line := raw[:idx]
			outputBuf.Reset()
			outputBuf.WriteString(raw[idx+1:])
			flushOutputLine(ts, line)
		}
	}

	for _, ev := range events {
		switch ev.Stream {
		case "i":
			for len(ev.Data) > 0 {
				r, size := utf8.DecodeRuneInString(ev.Data)
				ev.Data = ev.Data[size:]
				switch r {
				case '\r', '\n':
					flushInput(ev.Timestamp)
				case 127, 8:
					s := inputBuf.String()
					if s != "" {
						inputBuf.Reset()
						inputBuf.WriteString(s[:len(s)-1])
					}
				default:
					if r == '\t' || (r >= 32 && r != 127) {
						inputBuf.WriteRune(r)
					}
				}
			}
		case "o":
			outputBuf.WriteString(ev.Data)
			for strings.Contains(outputBuf.String(), "\n") {
				raw := outputBuf.String()
				idx := strings.Index(raw, "\n")
				line := raw[:idx]
				outputBuf.Reset()
				outputBuf.WriteString(raw[idx+1:])
				flushOutputLine(ev.Timestamp, line)
			}
		}
	}

	if inputBuf.Len() > 0 {
		flushInput(events[len(events)-1].Timestamp)
	}
	if outputBuf.Len() > 0 {
		flushOutput(events[len(events)-1].Timestamp)
	}
	return lines, nil
}
