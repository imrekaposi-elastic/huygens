package relay

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gorilla/websocket"
)

func TestDialRelayWSAndNetConn(t *testing.T) {
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		_, _, _ = conn.ReadMessage()
		_ = conn.WriteMessage(websocket.TextMessage, []byte("OK\n"))
		_ = conn.WriteMessage(websocket.BinaryMessage, []byte("ping"))
	}))
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	conn, err := dialRelayWS(wsURL, "secret", "sess-1", "agent-1", "10.0.0.5", "huygens")
	if err != nil {
		t.Fatalf("dialRelayWS: %v", err)
	}
	defer conn.Close()

	buf := make([]byte, 8)
	n, err := conn.Read(buf)
	if err != nil || n != 4 || string(buf[:n]) != "ping" {
		t.Fatalf("read = %d %q err=%v", n, buf[:n], err)
	}
	if _, err := conn.Write([]byte("pong")); err != nil {
		t.Fatalf("write: %v", err)
	}
	if conn.LocalAddr() == nil || conn.RemoteAddr() == nil {
		t.Fatal("expected addrs")
	}
}

func TestDialRelayWSRejectsBadHandshake(t *testing.T) {
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		_, _, _ = conn.ReadMessage()
		_ = conn.WriteMessage(websocket.TextMessage, []byte("DENIED\n"))
	}))
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	if _, err := dialRelayWS(wsURL, "secret", "sess", "agent", "10.0.0.1", "huygens"); err == nil {
		t.Fatal("expected rejection error")
	}
}
