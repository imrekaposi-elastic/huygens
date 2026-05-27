package server

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

const testToken = "test-breakout-token"

func newTestServer() *Server {
	return New(testToken)
}

func authedRequest(method, target, body string) *http.Request {
	req := httptest.NewRequest(method, target, bytes.NewBufferString(body))
	req.Header.Set("X-Huy-Service-Token", testToken)
	req.Header.Set("Content-Type", "application/json")
	return req
}

func TestHealth(t *testing.T) {
	srv := newTestServer()
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/health", nil))

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	var body map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["status"] != "ok" || body["service"] != "huy-breakout-controller" {
		t.Fatalf("unexpected body: %v", body)
	}
}

func TestPlanUnauthorized(t *testing.T) {
	srv := newTestServer()
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(
		rec,
		httptest.NewRequest(http.MethodPost, "/v1/links/plan", bytes.NewBufferString(`{}`)),
	)
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", rec.Code)
	}
}

func TestPlanBearerAuth(t *testing.T) {
	srv := newTestServer()
	body := `{
		"left": {"network_name": "a", "tunnel_ip": "10.0.0.1", "private_key": "lpriv", "public_key": "lpub"},
		"right": {"network_name": "b", "tunnel_ip": "10.0.0.2", "private_key": "rpriv", "public_key": "rpub"}
	}`
	req := httptest.NewRequest(http.MethodPost, "/v1/links/plan", bytes.NewBufferString(body))
	req.Header.Set("Authorization", "Bearer "+testToken)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
}

func TestPlanValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantDetail string
	}{
		{
			name:       "invalid json",
			body:       `{`,
			wantStatus: http.StatusBadRequest,
			wantDetail: "invalid JSON",
		},
		{
			name: "missing network names",
			body: `{
				"left": {"tunnel_ip": "10.0.0.1", "private_key": "a", "public_key": "b"},
				"right": {"tunnel_ip": "10.0.0.2", "private_key": "c", "public_key": "d"}
			}`,
			wantStatus: http.StatusBadRequest,
			wantDetail: "left and right endpoints required",
		},
		{
			name: "missing private keys",
			body: `{
				"left": {"network_name": "net-a", "tunnel_ip": "10.0.0.1", "public_key": "b"},
				"right": {"network_name": "net-b", "tunnel_ip": "10.0.0.2", "public_key": "d"}
			}`,
			wantStatus: http.StatusBadRequest,
			wantDetail: "private keys required on endpoints",
		},
	}

	srv := newTestServer()
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := httptest.NewRecorder()
			srv.Handler().ServeHTTP(rec, authedRequest(http.MethodPost, "/v1/links/plan", tc.body))
			if rec.Code != tc.wantStatus {
				t.Fatalf("status = %d, want %d, body = %s", rec.Code, tc.wantStatus, rec.Body.String())
			}
			var errBody map[string]string
			_ = json.NewDecoder(rec.Body).Decode(&errBody)
			if errBody["detail"] != tc.wantDetail {
				t.Fatalf("detail = %q, want %q", errBody["detail"], tc.wantDetail)
			}
		})
	}
}

func TestPlanSuccess(t *testing.T) {
	srv := newTestServer()
	body := `{
		"link_id": "link-123",
		"listen_port_base": 52000,
		"left": {
			"network_name": "dmz",
			"vnet_cidr": "10.20.1.0/24",
			"tunnel_ip": "10.255.0.1",
			"private_key": "left-priv",
			"public_key": "right-pub"
		},
		"right": {
			"network_name": "lab0",
			"vnet_cidr": "10.20.2.0/24",
			"tunnel_ip": "10.255.0.2",
			"private_key": "right-priv",
			"public_key": "left-pub"
		}
	}`
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, authedRequest(http.MethodPost, "/v1/links/plan", body))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}

	var resp PlanResponse
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}

	if !resp.Left.Enabled || !resp.Right.Enabled {
		t.Fatal("expected both sides enabled")
	}
	if resp.Left.Interface != "wg-dmz" || resp.Right.Interface != "wg-lab0" {
		t.Fatalf("interfaces: left=%q right=%q", resp.Left.Interface, resp.Right.Interface)
	}
	if resp.Left.ListenPort != 52000 || resp.Right.ListenPort != 52001 {
		t.Fatalf("ports: left=%d right=%d", resp.Left.ListenPort, resp.Right.ListenPort)
	}
	if resp.Left.Address != "10.255.0.1/32" || resp.Right.Address != "10.255.0.2/32" {
		t.Fatalf("addresses: left=%q right=%q", resp.Left.Address, resp.Right.Address)
	}
	if len(resp.Left.VnetRoutes) != 1 || resp.Left.VnetRoutes[0] != "10.20.1.0/24" {
		t.Fatalf("left routes: %v", resp.Left.VnetRoutes)
	}
	if len(resp.Left.Peers) != 1 {
		t.Fatalf("left peers: %v", resp.Left.Peers)
	}
	peer := resp.Left.Peers[0]
	if peer.Name != "link-lab0" || peer.PublicKey != "left-pub" {
		t.Fatalf("left peer: %+v", peer)
	}
	wantAllowed := []string{"10.255.0.2/32", "10.20.2.0/24"}
	if len(peer.AllowedIPs) != len(wantAllowed) {
		t.Fatalf("allowed IPs: %v", peer.AllowedIPs)
	}
	for i, ip := range wantAllowed {
		if peer.AllowedIPs[i] != ip {
			t.Fatalf("allowed[%d] = %q, want %q", i, peer.AllowedIPs[i], ip)
		}
	}
}

func TestPlanSanitizeInterfaceName(t *testing.T) {
	srv := newTestServer()
	body := `{
		"left": {"network_name": "dmz/lab", "tunnel_ip": "10.0.0.1", "private_key": "a", "public_key": "b"},
		"right": {"network_name": "!!!", "tunnel_ip": "10.0.0.2", "private_key": "c", "public_key": "d"}
	}`
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, authedRequest(http.MethodPost, "/v1/links/plan", body))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
	var resp PlanResponse
	_ = json.NewDecoder(rec.Body).Decode(&resp)
	if resp.Left.Interface != "wg-dmz-lab" {
		t.Fatalf("left interface = %q", resp.Left.Interface)
	}
	if resp.Right.Interface != "wg-vnet" {
		t.Fatalf("right interface = %q, want wg-vnet for empty sanitize", resp.Right.Interface)
	}
}

func TestRevokeValidationAndSuccess(t *testing.T) {
	srv := newTestServer()

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, authedRequest(http.MethodPost, "/v1/links/revoke", `{}`))
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("empty revoke status = %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	body := `{"link_id": "abc", "left_network": "net-a", "right_network": "net-b"}`
	srv.Handler().ServeHTTP(rec, authedRequest(http.MethodPost, "/v1/links/revoke", body))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var resp map[string]any
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["disabled"] != true {
		t.Fatalf("disabled = %v", resp["disabled"])
	}
	if resp["link_id"] != "abc" || resp["left_network"] != "net-a" || resp["right_network"] != "net-b" {
		t.Fatalf("unexpected revoke response: %v", resp)
	}
}

func TestSanitize(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{"lab0", "lab0"},
		{"dmz/lab", "dmz-lab"},
		{"net_a", "net-a"},
		{"!!!", "vnet"},
		{"", "vnet"},
	}
	for _, tc := range tests {
		if got := sanitize(tc.in); got != tc.want {
			t.Errorf("sanitize(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}
