package server_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/config"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/iam"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/inventory"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/server"
)

const (
	testJWTSecret = "test-jwt-secret-key-minimum-32-bytes!"
	testJWTIssuer = "huy-iam"
)

func TestMain(m *testing.M) {
	_ = os.Setenv("OTEL_SDK_DISABLED", "true")
	os.Exit(m.Run())
}

func signToken(t *testing.T, sub string, extra func(*jwt.MapClaims)) string {
	t.Helper()
	claims := jwt.MapClaims{
		"sub":      sub,
		"email":    sub + "@example.com",
		"username": sub,
		"org_memberships": []map[string]any{
			{"organization_id": "org-1", "roles": []any{"admin"}},
		},
		"iss": testJWTIssuer,
		"exp": time.Now().Add(time.Hour).Unix(),
	}
	if extra != nil {
		extra(&claims)
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString([]byte(testJWTSecret))
	if err != nil {
		t.Fatalf("sign token: %v", err)
	}
	return signed
}

type mockDeps struct {
	iamSrv *httptest.Server
	invSrv *httptest.Server
}

func startMocks(t *testing.T) mockDeps {
	t.Helper()
	linux := "huygens"
	iamSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/internal/v1/ssh/authorize":
			_ = json.NewEncoder(w).Encode(iam.AuthorizeResponse{
				Allowed:       true,
				Reason:        "ok",
				LinuxUsername: &linux,
			})
		case "/internal/v1/ssh/sign-cert":
			_ = json.NewEncoder(w).Encode(iam.SignCertResponse{
				CertificateOpenSSH: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHRlc3Q= cert",
			})
		default:
			http.NotFound(w, r)
		}
	}))
	invSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(inventory.SSHTarget{
			OrganizationID: "org-1",
			ProjectID:      "proj-1",
			AgentID:        "agent-1",
			VMName:         "web-01",
			GuestIP:        "10.0.0.5",
			RelayHost:      "agent.test",
			RelayPort:      9122,
			RelayWSURL:     "wss://agent.test/ws",
			SSHReady:       true,
		})
	}))
	t.Cleanup(func() {
		iamSrv.Close()
		invSrv.Close()
	})
	return mockDeps{iamSrv: iamSrv, invSrv: invSrv}
}

func newTestServer(t *testing.T, mocks mockDeps) *server.Server {
	t.Helper()
	dir := t.TempDir()
	t.Setenv("SSH_RECORDING_DIR", dir)
	t.Setenv("JWT_SECRET", testJWTSecret)
	t.Setenv("JWT_ISSUER", testJWTIssuer)
	t.Setenv("IAM_URL", mocks.iamSrv.URL)
	t.Setenv("INVENTORY_URL", mocks.invSrv.URL)
	t.Setenv("KAFKA_PUBLISH_ENABLED", "false")
	return server.New(config.Load())
}

func bearerReq(method, target, body, token string) *http.Request {
	var req *http.Request
	if body != "" {
		req = httptest.NewRequest(method, target, bytes.NewBufferString(body))
	} else {
		req = httptest.NewRequest(method, target, http.NoBody)
	}
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	return req
}

func TestHealth(t *testing.T) {
	srv := server.New(config.Load())
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestCreateSessionFlow(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	h := srv.Handler()
	token := signToken(t, "user-1", nil)

	createBody := `{"organization_id":"org-1","project_id":"proj-1","vm_name":"web-01"}`
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions", createBody, token))
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d body=%s", rec.Code, rec.Body.String())
	}
	var created map[string]any
	if err := json.NewDecoder(rec.Body).Decode(&created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	id, _ := created["id"].(string)
	if id == "" {
		t.Fatal("expected session id")
	}

	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/"+id, "", token))
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions?organization_id=org-1", "", token))
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/"+id+"/recording", "", token))
	if rec.Code != http.StatusOK {
		t.Fatalf("recording status = %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodDelete, "/api/v1/ssh/sessions/"+id, "", token))
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", rec.Code)
	}
}

func TestCreateSessionInvalidJSON(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions", `{`, signToken(t, "user-1", nil)))
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestCreateSessionUnauthorized(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions", `{}`, ""))
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestGetSessionForbiddenForOtherUser(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	h := srv.Handler()
	owner := signToken(t, "owner", nil)
	other := signToken(t, "other", func(c *jwt.MapClaims) {
		(*c)["org_memberships"] = []map[string]any{
			{"organization_id": "org-1", "roles": []any{"viewer"}},
		}
	})

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions",
		`{"organization_id":"org-1","project_id":"proj-1","vm_name":"web-01"}`, owner))
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d", rec.Code)
	}
	var created map[string]any
	_ = json.NewDecoder(rec.Body).Decode(&created)
	id := created["id"].(string)

	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/"+id, "", other))
	if rec.Code != http.StatusForbidden {
		t.Fatalf("forbidden status = %d", rec.Code)
	}
}

func TestGetSessionViaPersistedMeta(t *testing.T) {
	mocks := startMocks(t)
	dir := t.TempDir()
	t.Setenv("SSH_RECORDING_DIR", dir)
	t.Setenv("JWT_SECRET", testJWTSecret)
	t.Setenv("JWT_ISSUER", testJWTIssuer)
	t.Setenv("IAM_URL", mocks.iamSrv.URL)
	t.Setenv("INVENTORY_URL", mocks.invSrv.URL)
	t.Setenv("KAFKA_PUBLISH_ENABLED", "false")

	meta := filepath.Join(dir, "persisted.meta.json")
	sessJSON := `{
		"id":"persisted",
		"organization_id":"org-1",
		"project_id":"proj-1",
		"vm_name":"web-01",
		"user_id":"user-1",
		"status":"closed",
		"started_at":"2024-01-01T00:00:00Z"
	}`
	if err := os.WriteFile(meta, []byte(sessJSON), 0o640); err != nil {
		t.Fatalf("write meta: %v", err)
	}
	cast := filepath.Join(dir, "persisted.cast")
	if err := os.WriteFile(cast, []byte(`{"version":2}`), 0o640); err != nil {
		t.Fatalf("write cast: %v", err)
	}

	srv := server.New(config.Load())
	token := signToken(t, "user-1", nil)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/persisted", "", token))
	if rec.Code != http.StatusOK {
		t.Fatalf("get persisted status = %d body=%s", rec.Code, rec.Body.String())
	}
}

func TestCreateSessionInventoryNotFound(t *testing.T) {
	iamSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(iam.AuthorizeResponse{Allowed: true})
	}))
	invSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_ = json.NewEncoder(w).Encode(map[string]string{"detail": "VM not assigned"})
	}))
	t.Cleanup(func() { iamSrv.Close(); invSrv.Close() })

	dir := t.TempDir()
	t.Setenv("SSH_RECORDING_DIR", dir)
	t.Setenv("JWT_SECRET", testJWTSecret)
	t.Setenv("JWT_ISSUER", testJWTIssuer)
	t.Setenv("IAM_URL", iamSrv.URL)
	t.Setenv("INVENTORY_URL", invSrv.URL)
	t.Setenv("KAFKA_PUBLISH_ENABLED", "false")

	srv := server.New(config.Load())
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions",
		`{"organization_id":"org-1","project_id":"proj-1","vm_name":"missing"}`, signToken(t, "user-1", nil)))
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestCreateSessionIAMDenied(t *testing.T) {
	iamSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(iam.AuthorizeResponse{Allowed: false, Reason: "rbac_denied"})
	}))
	invSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(inventory.SSHTarget{ProjectID: "proj-1", AgentID: "a1", GuestIP: "10.0.0.1"})
	}))
	t.Cleanup(func() { iamSrv.Close(); invSrv.Close() })

	dir := t.TempDir()
	t.Setenv("SSH_RECORDING_DIR", dir)
	t.Setenv("JWT_SECRET", testJWTSecret)
	t.Setenv("JWT_ISSUER", testJWTIssuer)
	t.Setenv("IAM_URL", iamSrv.URL)
	t.Setenv("INVENTORY_URL", invSrv.URL)
	t.Setenv("KAFKA_PUBLISH_ENABLED", "false")

	srv := server.New(config.Load())
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions",
		`{"organization_id":"org-1","project_id":"proj-1","vm_name":"web-01"}`, signToken(t, "user-1", nil)))
	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d body=%s", rec.Code, rec.Body.String())
	}
}

func TestParseClaimsFromQueryToken(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	token := signToken(t, "user-1", nil)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/ssh/sessions?organization_id=org-1&access_token="+token, http.NoBody)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestGetSessionNotFound(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/does-not-exist", "", signToken(t, "user-1", nil)))
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestSessionWSNotFound(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/missing/ws", "", signToken(t, "user-1", nil)))
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestSessionWSForbiddenForOtherUser(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	h := srv.Handler()
	owner := signToken(t, "owner", nil)
	other := signToken(t, "other", nil)

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions",
		`{"organization_id":"org-1","project_id":"proj-1","vm_name":"web-01"}`, owner))
	var created map[string]any
	_ = json.NewDecoder(rec.Body).Decode(&created)

	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/"+created["id"].(string)+"/ws", "", other))
	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestServerClose(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	if err := srv.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
}

func TestPlatformAdminCanViewAnySession(t *testing.T) {
	mocks := startMocks(t)
	srv := newTestServer(t, mocks)
	h := srv.Handler()
	owner := signToken(t, "owner", nil)
	admin := signToken(t, "admin", func(c *jwt.MapClaims) {
		(*c)["platform_roles"] = []string{"platform_admin"}
	})

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodPost, "/api/v1/ssh/sessions",
		`{"organization_id":"org-1","project_id":"proj-1","vm_name":"web-01"}`, owner))
	var created map[string]any
	_ = json.NewDecoder(rec.Body).Decode(&created)

	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, bearerReq(http.MethodGet, "/api/v1/ssh/sessions/"+created["id"].(string), "", admin))
	if rec.Code != http.StatusOK {
		t.Fatalf("admin view status = %d", rec.Code)
	}
}
