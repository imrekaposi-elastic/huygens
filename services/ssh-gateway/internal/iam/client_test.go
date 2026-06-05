package iam

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAuthorizeAndSignCert(t *testing.T) {
	linux := "huygens"
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-Huy-Service-Token") != "svc-token" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		switch r.URL.Path {
		case "/internal/v1/ssh/authorize":
			_ = json.NewEncoder(w).Encode(AuthorizeResponse{
				Allowed:       true,
				Reason:        "ok",
				LinuxUsername: &linux,
			})
		case "/internal/v1/ssh/sign-cert":
			_ = json.NewEncoder(w).Encode(SignCertResponse{
				CertificateOpenSSH: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHRlc3Q= cert",
				ValidAfter:         1,
				ValidBefore:        999,
			})
		default:
			http.NotFound(w, r)
		}
	}))
	defer srv.Close()

	client := New(srv.URL, "svc-token")
	authz, err := client.Authorize(context.Background(), AuthorizeRequest{
		OrganizationID: "org-1",
		ProjectID:      "proj-1",
		VMName:         "web-01",
		UserID:         "user-1",
	})
	if err != nil {
		t.Fatalf("Authorize: %v", err)
	}
	if !authz.Allowed || authz.LinuxUsername == nil || *authz.LinuxUsername != linux {
		t.Fatalf("authz = %+v", authz)
	}

	signed, err := client.SignCert(context.Background(), SignCertRequest{
		OrganizationID:   "org-1",
		LinuxUsername:    linux,
		SessionID:        "sess-1",
		PublicKeyOpenSSH: "ssh-ed25519 AAAA",
	})
	if err != nil {
		t.Fatalf("SignCert: %v", err)
	}
	if signed.CertificateOpenSSH == "" {
		t.Fatal("expected certificate")
	}
}

func TestAuthorizeHTTPError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "fail", http.StatusInternalServerError)
	}))
	defer srv.Close()

	client := New(srv.URL, "svc-token")
	_, err := client.Authorize(context.Background(), AuthorizeRequest{OrganizationID: "org-1"})
	if err == nil || !strings.Contains(err.Error(), "status 500") {
		t.Fatalf("err = %v", err)
	}
}
