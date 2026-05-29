package relay

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"strconv"
	"time"
)

type DialRequest struct {
	SessionToken string `json:"session_token"`
	GuestIP      string `json:"guest_ip"`
	GuestPort    int    `json:"guest_port"`
	LinuxUser    string `json:"linux_user"`
	SessionID    string `json:"session_id"`
}

func BuildSessionToken(secret, sessionID, agentID string, expires time.Time) string {
	payload := sessionID + "|" + agentID + "|" + strconv.FormatInt(expires.Unix(), 10)
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(payload))
	return hex.EncodeToString(mac.Sum(nil)) + "." + strconv.FormatInt(expires.Unix(), 10)
}

func DialRelay(host string, port int, secret string, sessionID, agentID, guestIP, linuxUser string) (net.Conn, error) {
	addr := net.JoinHostPort(host, strconv.Itoa(port))
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		return nil, err
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
	if _, err := conn.Write(append(line, '\n')); err != nil {
		_ = conn.Close()
		return nil, err
	}
	return conn, nil
}

func Bridge(a, b net.Conn, onA, onB func([]byte)) error {
	errCh := make(chan error, 2)
	copy := func(dst net.Conn, src net.Conn, hook func([]byte)) {
		buf := make([]byte, 32*1024)
		for {
			n, err := src.Read(buf)
			if n > 0 {
				if hook != nil {
					hook(buf[:n])
				}
				if _, werr := dst.Write(buf[:n]); werr != nil {
					errCh <- werr
					return
				}
			}
			if err != nil {
				errCh <- err
				return
			}
		}
	}
	go copy(b, a, onA)
	go copy(a, b, onB)
	err := <-errCh
	_ = a.Close()
	_ = b.Close()
	return err
}

func FormatRelayError(err error) error {
	if err == nil {
		return nil
	}
	return fmt.Errorf("relay: %w", err)
}
