package server_test

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/config"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/server"
)

func TestHealth(t *testing.T) {
	srv := server.New(config.Load())
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
}
