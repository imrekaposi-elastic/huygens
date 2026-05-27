package server

import (
	"net/http"
	"strings"
)

type Server struct {
	serviceToken string
	mux          *http.ServeMux
}

func New(serviceToken string) *Server {
	s := &Server{serviceToken: serviceToken, mux: http.NewServeMux()}
	s.mux.HandleFunc("GET /health", s.handleHealth)
	s.mux.HandleFunc("POST /v1/links/plan", s.auth(s.handlePlan))
	s.mux.HandleFunc("POST /v1/links/revoke", s.auth(s.handleRevoke))
	return s
}

func (s *Server) Handler() http.Handler {
	return s.mux
}

func (s *Server) auth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		token := r.Header.Get("X-Huy-Service-Token")
		if token == "" {
			token = strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
		}
		if token != s.serviceToken {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "invalid service token"})
			return
		}
		next(w, r)
	}
}
