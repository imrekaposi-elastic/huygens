package inventory

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestResolveTargetSuccess(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-Huy-Service-Token") != "svc-token" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		_ = json.NewEncoder(w).Encode(SSHTarget{
			OrganizationID: "org-1",
			ProjectID:      "proj-1",
			AgentID:        "agent-1",
			VMName:         "web-01",
			GuestIP:        "10.0.0.5",
			RelayHost:      "agent.test",
			RelayPort:      9122,
			RelayWSURL:     "wss://agent.test/api/v1/ssh/relay/ws",
			SSHReady:       true,
		})
	}))
	defer srv.Close()

	client := New(srv.URL, "svc-token")
	target, err := client.ResolveTarget(context.Background(), "org-1", "proj-1", "web-01")
	if err != nil {
		t.Fatalf("ResolveTarget: %v", err)
	}
	if target.GuestIP != "10.0.0.5" || target.AgentID != "agent-1" {
		t.Fatalf("target = %+v", target)
	}
}

func TestResolveTargetNotFound(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_ = json.NewEncoder(w).Encode(map[string]string{"detail": "VM not assigned to project"})
	}))
	defer srv.Close()

	client := New(srv.URL, "svc-token")
	_, err := client.ResolveTarget(context.Background(), "org-1", "proj-1", "missing")
	if err == nil || err.Error() != "VM not assigned to project" {
		t.Fatalf("err = %v", err)
	}
}

func TestResolveTargetServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "fail", http.StatusInternalServerError)
	}))
	defer srv.Close()

	client := New(srv.URL, "svc-token")
	_, err := client.ResolveTarget(context.Background(), "org-1", "proj-1", "web-01")
	if err == nil || !strings.Contains(err.Error(), "status 500") {
		t.Fatalf("err = %v", err)
	}
}
