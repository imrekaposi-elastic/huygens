package relay

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type wsNetConn struct {
	conn    *websocket.Conn
	readMu  sync.Mutex
	writeMu sync.Mutex
	readBuf []byte
}

func (c *wsNetConn) Read(b []byte) (int, error) {
	c.readMu.Lock()
	defer c.readMu.Unlock()
	if len(c.readBuf) == 0 {
		_, msg, err := c.conn.ReadMessage()
		if err != nil {
			return 0, err
		}
		c.readBuf = msg
	}
	n := copy(b, c.readBuf)
	c.readBuf = c.readBuf[n:]
	return n, nil
}

func (c *wsNetConn) Write(b []byte) (int, error) {
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	if err := c.conn.WriteMessage(websocket.BinaryMessage, b); err != nil {
		return 0, err
	}
	return len(b), nil
}

func (c *wsNetConn) Close() error {
	return c.conn.Close()
}

func (c *wsNetConn) LocalAddr() net.Addr                { return c.conn.LocalAddr() }
func (c *wsNetConn) RemoteAddr() net.Addr               { return c.conn.RemoteAddr() }
func (c *wsNetConn) SetDeadline(t time.Time) error      { return c.conn.SetReadDeadline(t) }
func (c *wsNetConn) SetReadDeadline(t time.Time) error  { return c.conn.SetReadDeadline(t) }
func (c *wsNetConn) SetWriteDeadline(t time.Time) error { return c.conn.SetWriteDeadline(t) }

func dialRelayWS(wsURL, secret, sessionID, agentID, guestIP, linuxUser string) (net.Conn, error) {
	dialer := websocket.Dialer{
		HandshakeTimeout: 15 * time.Second,
		TLSClientConfig:  &tls.Config{InsecureSkipVerify: true}, //nolint:gosec // hypervisor agents use private CAs
	}
	conn, resp, err := dialer.Dial(wsURL, http.Header{})
	if err != nil {
		if resp != nil {
			return nil, fmt.Errorf("ws dial: %w (HTTP %d)", err, resp.StatusCode)
		}
		return nil, fmt.Errorf("ws dial: %w", err)
	}
	expires := time.Now().Add(5 * time.Minute)
	token := BuildSessionToken(secret, sessionID, agentID, expires)
	req := DialRequest{
		SessionToken: token,
		GuestIP:      guestIP,
		GuestPort:    22,
		LinuxUser:    linuxUser,
		SessionID:    sessionID,
	}
	line, _ := json.Marshal(req)
	if err := conn.WriteMessage(websocket.TextMessage, append(line, '\n')); err != nil {
		_ = conn.Close()
		return nil, err
	}
	_, msg, err := conn.ReadMessage()
	if err != nil {
		_ = conn.Close()
		return nil, fmt.Errorf("relay ws handshake: %w", err)
	}
	lineStr := strings.TrimSpace(string(msg))
	if lineStr != "OK" && !strings.HasPrefix(lineStr, "OK") {
		_ = conn.Close()
		return nil, fmt.Errorf("relay ws rejected: %s", lineStr)
	}
	return &wsNetConn{conn: conn}, nil
}
