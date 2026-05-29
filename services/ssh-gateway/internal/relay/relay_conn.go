package relay

import (
	"bufio"
	"fmt"
	"net"
	"strings"
)

// relayConn is a TCP connection to the agent ssh-relay after the OK handshake.
type relayConn struct {
	net.Conn
	br *bufio.Reader
}

func (c *relayConn) Read(b []byte) (int, error) {
	return c.br.Read(b)
}

// DialRelaySSH connects to the agent relay and returns a net.Conn ready for SSH wire protocol.
func DialRelaySSH(host string, port int, secret, sessionID, agentID, guestIP, linuxUser string) (net.Conn, error) {
	conn, err := DialRelay(host, port, secret, sessionID, agentID, guestIP, linuxUser)
	if err != nil {
		return nil, err
	}
	br := bufio.NewReader(conn)
	line, err := br.ReadString('\n')
	if err != nil {
		_ = conn.Close()
		return nil, fmt.Errorf("relay handshake: %w", err)
	}
	line = strings.TrimSpace(line)
	if line != "OK" && !strings.HasPrefix(line, "OK") {
		_ = conn.Close()
		return nil, fmt.Errorf("relay rejected: %s", line)
	}
	return &relayConn{Conn: conn, br: br}, nil
}
