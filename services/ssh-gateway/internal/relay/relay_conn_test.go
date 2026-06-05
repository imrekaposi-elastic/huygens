package relay

import (
	"bufio"
	"net"
	"strconv"
	"strings"
	"testing"
)

func startMockTCPRelay(t *testing.T) (host string, port int) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	t.Cleanup(func() { _ = ln.Close() })
	_, portStr, _ := net.SplitHostPort(ln.Addr().String())
	port, _ = strconv.Atoi(portStr)
	go func() {
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			go func(conn net.Conn) {
				defer conn.Close()
				br := bufio.NewReader(conn)
				_, _ = br.ReadString('\n')
				_, _ = conn.Write([]byte("OK\n"))
			}(c)
		}
	}()
	return "127.0.0.1", port
}

func TestDialRelaySSHOverTCP(t *testing.T) {
	host, port := startMockTCPRelay(t)
	conn, err := DialRelaySSH(host, port, "", "secret", "sess-1", "agent-1", "10.0.0.5", "huygens")
	if err != nil {
		t.Fatalf("DialRelaySSH: %v", err)
	}
	defer conn.Close()

	if _, err := conn.Write([]byte("probe")); err != nil {
		t.Fatalf("write: %v", err)
	}
}

func TestDialRelaySSHFallsBackToTCP(t *testing.T) {
	host, port := startMockTCPRelay(t)
	conn, err := DialRelaySSH(host, port, "ws://127.0.0.1:1/ws", "secret", "sess", "agent", "10.0.0.1", "huygens")
	if err != nil {
		t.Fatalf("DialRelaySSH fallback: %v", err)
	}
	_ = conn.Close()
}

func TestDialRelayWritesRequest(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer ln.Close()
	got := make(chan string, 1)
	go func() {
		c, _ := ln.Accept()
		defer c.Close()
		br := bufio.NewReader(c)
		line, _ := br.ReadString('\n')
		got <- line
	}()
	_, portStr, _ := net.SplitHostPort(ln.Addr().String())
	port, _ := strconv.Atoi(portStr)
	conn, err := DialRelay("127.0.0.1", port, "secret", "sess", "agent", "10.0.0.1", "huygens")
	if err != nil {
		t.Fatalf("DialRelay: %v", err)
	}
	_ = conn.Close()
	line := <-got
	if line == "" || !strings.Contains(line, "sess") {
		t.Fatalf("unexpected dial line: %q", line)
	}
}

