package sshbridge

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

func TestWsBinaryWriter(t *testing.T) {
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
	msgCh := make(chan []byte, 1)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		_, msg, err := conn.ReadMessage()
		if err == nil {
			msgCh <- msg
		}
	}))
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	ws, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("dial ws: %v", err)
	}
	defer ws.Close()

	var recorded []byte
	out := &wsWriter{ws: ws}
	writer := &wsBinaryWriter{
		out: out,
		onOutput: func(p []byte) error {
			recorded = append(recorded, p...)
			return nil
		},
	}
	payload := []byte("terminal output")
	n, err := writer.Write(payload)
	if err != nil || n != len(payload) {
		t.Fatalf("write n=%d err=%v", n, err)
	}
	if string(recorded) != string(payload) {
		t.Fatalf("hook got %q", recorded)
	}
	select {
	case msg := <-msgCh:
		if string(msg) != string(payload) {
			t.Fatalf("ws got %q", msg)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("expected websocket message")
	}

	if err := out.writeText("status"); err != nil {
		t.Fatalf("writeText: %v", err)
	}
}

func TestWsBinaryWriterEmptyWrite(t *testing.T) {
	out := &wsWriter{ws: nil}
	writer := &wsBinaryWriter{out: out}
	n, err := writer.Write(nil)
	if err != nil || n != 0 {
		t.Fatalf("empty write n=%d err=%v", n, err)
	}
}
