package server

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRequestContextMiddlewareSetsRequestID(t *testing.T) {
	var gotID string
	handler := requestContextMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotID = w.Header().Get("X-Request-Id")
		w.WriteHeader(http.StatusNoContent)
	}))
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	handler.ServeHTTP(rec, req)
	if rec.Header().Get("X-Request-Id") == "" {
		t.Fatal("expected X-Request-Id response header")
	}
	if gotID == "" {
		t.Fatal("expected middleware to set request id before handler")
	}
}

func TestRequestContextMiddlewarePreservesRequestID(t *testing.T) {
	handler := requestContextMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	req.Header.Set("X-Request-Id", "fixed-id")
	handler.ServeHTTP(rec, req)
	if rec.Header().Get("X-Request-Id") != "fixed-id" {
		t.Fatalf("got %q", rec.Header().Get("X-Request-Id"))
	}
}
