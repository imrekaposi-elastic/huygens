package relay

import (
	"io"
	"net"
	"testing"
	"time"
)

func TestBuildSessionTokenDeterministic(t *testing.T) {
	exp := time.Unix(1700000000, 0)
	a := BuildSessionToken("secret", "sess", "agent", exp)
	b := BuildSessionToken("secret", "sess", "agent", exp)
	if a != b {
		t.Fatalf("tokens differ: %q vs %q", a, b)
	}
	if a == "" {
		t.Fatal("expected token")
	}
}

func TestBridgeReturnsOnPeerClose(t *testing.T) {
	a, b := net.Pipe()
	go func() { _ = b.Close() }()
	if err := Bridge(a, b, nil, nil); err == nil {
		t.Fatal("expected error when peer closes")
	}
}

func TestFormatRelayError(t *testing.T) {
	if FormatRelayError(nil) != nil {
		t.Fatal("nil stays nil")
	}
	wrapped := FormatRelayError(io.EOF)
	if wrapped == nil || wrapped.Error() == "" {
		t.Fatal("expected wrapped error")
	}
}
