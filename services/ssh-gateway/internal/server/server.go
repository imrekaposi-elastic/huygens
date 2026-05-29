package server

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"

	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/config"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/events"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/iam"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/inventory"
	jwtutil "github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/jwt"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/recording"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/session"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/sshbridge"
)

type Server struct {
	cfg       config.Config
	sessions  *session.Store
	iam       *iam.Client
	inventory *inventory.Client
	events    *events.Publisher
	upgrader  websocket.Upgrader
}

func New(cfg config.Config) *Server {
	s := &Server{
		cfg:       cfg,
		sessions:  session.NewStore(),
		iam:       iam.New(cfg.IAMURL, cfg.IAMServiceToken),
		inventory: inventory.New(cfg.InventoryURL, cfg.InventoryServiceToken),
		events:    events.NewPublisher(cfg.KafkaBootstrap, cfg.KafkaEnabled),
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		},
	}
	if loaded, err := session.LoadAll(cfg.RecordingDir); err == nil {
		for _, sess := range loaded {
			s.sessions.Put(sess)
		}
	}
	return s
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("GET /api/v1/ssh/sessions", s.handleListSessions)
	mux.HandleFunc("POST /api/v1/ssh/sessions", s.handleCreateSession)
	mux.HandleFunc("GET /api/v1/ssh/sessions/{id}", s.handleGetSession)
	mux.HandleFunc("GET /api/v1/ssh/sessions/{id}/recording", s.handleGetRecording)
	mux.HandleFunc("DELETE /api/v1/ssh/sessions/{id}", s.handleDeleteSession)
	mux.HandleFunc("GET /api/v1/ssh/sessions/{id}/ws", s.handleSessionWS)
	return otelhttp.NewHandler(mux, "huy-ssh-gateway")
}

func (s *Server) Close() error {
	return s.events.Close()
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "huy-ssh-gateway"})
}

type createSessionRequest struct {
	OrganizationID string `json:"organization_id"`
	ProjectID      string `json:"project_id"`
	VMName         string `json:"vm_name"`
}

func (s *Server) parseClaims(r *http.Request) (*jwtutil.Claims, error) {
	auth := r.Header.Get("Authorization")
	var token string
	if strings.HasPrefix(auth, "Bearer ") {
		token = strings.TrimPrefix(auth, "Bearer ")
	} else if q := r.URL.Query().Get("access_token"); q != "" {
		// Browser WebSocket cannot set Authorization; console/CLI may pass token in query.
		token = q
	} else {
		return nil, http.ErrNoCookie
	}
	return jwtutil.Parse(token, s.cfg.JWTSecret, s.cfg.JWTIssuer)
}

func (s *Server) handleCreateSession(w http.ResponseWriter, r *http.Request) {
	claims, err := s.parseClaims(r)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "missing or invalid bearer token"})
		return
	}
	var body createSessionRequest
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "invalid JSON"})
		return
	}
	ctx := r.Context()
	target, err := s.inventory.ResolveTarget(ctx, body.OrganizationID, body.ProjectID, body.VMName)
	if err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"detail": "vm target not found"})
		return
	}
	authz, err := s.iam.Authorize(ctx, iam.AuthorizeRequest{
		OrganizationID:      body.OrganizationID,
		ProjectID:           body.ProjectID,
		VMName:              body.VMName,
		VMAssignedToProject: target.ProjectID == body.ProjectID,
		UserID:              claims.Sub,
		UserEmail:           claims.Email,
		UserUsername:        claims.Username,
		PlatformRoles:       claims.PlatformRoles,
		OrgMemberships:      claims.OrgMemberships,
		ProjectRoles:        claims.ProjectRoles,
	})
	if err != nil || authz == nil || !authz.Allowed || authz.LinuxUsername == nil {
		reason := "rbac_denied"
		if authz != nil && authz.Reason != "" {
			reason = authz.Reason
		}
		writeJSON(w, http.StatusForbidden, map[string]string{"detail": reason})
		return
	}
	sessionID := uuid.NewString()
	recPath := s.cfg.RecordingDir + "/" + sessionID + ".cast"
	if rec, err := recording.NewWriter(s.cfg.RecordingDir, sessionID); err == nil {
		if path, err := rec.Close(); err == nil {
			recPath = path
		}
	}
	sess := &session.Session{
		ID:             sessionID,
		OrganizationID: body.OrganizationID,
		ProjectID:      body.ProjectID,
		VMName:         body.VMName,
		AgentID:        target.AgentID,
		GuestIP:        target.GuestIP,
		RelayHost:      target.RelayHost,
		RelayPort:      target.RelayPort,
		LinuxUser:      *authz.LinuxUsername,
		UserID:         claims.Sub,
		UserEmail:      claims.Email,
		UserUsername:   claims.Username,
		Status:         "active",
		StartedAt:      time.Now().UTC(),
		RecordingPath:  recPath,
		RecordingURI:   "file://" + recPath,
	}
	s.sessions.Put(sess)
	_ = session.Save(s.cfg.RecordingDir, sess)
	_ = s.events.PublishSessionEvent(ctx, events.SessionEventData{
		SessionID:      sessionID,
		OrganizationID: body.OrganizationID,
		ProjectID:      body.ProjectID,
		VMName:         body.VMName,
		AgentID:        target.AgentID,
		UserID:         claims.Sub,
		UserEmail:      claims.Email,
		LinuxUser:      *authz.LinuxUsername,
		Action:         "session.open",
		RecordingURI:   sess.RecordingURI,
	})
	writeJSON(w, http.StatusCreated, sess)
}

func (s *Server) handleListSessions(w http.ResponseWriter, r *http.Request) {
	claims, err := s.parseClaims(r)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
		return
	}
	orgID := r.URL.Query().Get("organization_id")
	if orgID == "" && len(claims.OrgMemberships) > 0 {
		if m, ok := claims.OrgMemberships[0]["organization_id"].(string); ok {
			orgID = m
		}
	}
	writeJSON(w, http.StatusOK, s.sessions.List(orgID))
}

func (s *Server) getSession(id string) (*session.Session, bool) {
	if sess, ok := s.sessions.Get(id); ok {
		return sess, true
	}
	if sess, ok := session.Load(s.cfg.RecordingDir, id); ok {
		s.sessions.Put(sess)
		return sess, true
	}
	return nil, false
}

func (s *Server) canViewSession(claims *jwtutil.Claims, sess *session.Session) bool {
	if sess.UserID == claims.Sub {
		return true
	}
	if contains(claims.PlatformRoles, "platform_admin") {
		return true
	}
	for _, m := range claims.OrgMemberships {
		orgID, _ := m["organization_id"].(string)
		if orgID == sess.OrganizationID {
			roles, _ := m["roles"].([]any)
			for _, r := range roles {
				if role, _ := r.(string); role == "admin" {
					return true
				}
			}
		}
	}
	return false
}

func (s *Server) handleGetSession(w http.ResponseWriter, r *http.Request) {
	claims, err := s.parseClaims(r)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
		return
	}
	id := r.PathValue("id")
	sess, ok := s.getSession(id)
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"detail": "session not found"})
		return
	}
	if !s.canViewSession(claims, sess) {
		writeJSON(w, http.StatusForbidden, map[string]string{"detail": "access denied"})
		return
	}
	writeJSON(w, http.StatusOK, sess)
}

func (s *Server) handleGetRecording(w http.ResponseWriter, r *http.Request) {
	claims, err := s.parseClaims(r)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
		return
	}
	id := r.PathValue("id")
	sess, ok := s.getSession(id)
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"detail": "session not found"})
		return
	}
	if !s.canViewSession(claims, sess) {
		writeJSON(w, http.StatusForbidden, map[string]string{"detail": "access denied"})
		return
	}
	recPath := sess.RecordingPath
	if recPath == "" {
		recPath = session.RecordingPath(s.cfg.RecordingDir, id)
	}
	f, err := os.Open(recPath)
	if err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"detail": "recording not found"})
		return
	}
	defer f.Close()
	w.Header().Set("Content-Type", "application/x-asciicast")
	w.Header().Set("Content-Disposition", `attachment; filename="`+id+`.cast"`)
	io.Copy(w, f)
}

func (s *Server) handleDeleteSession(w http.ResponseWriter, r *http.Request) {
	claims, err := s.parseClaims(r)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
		return
	}
	id := r.PathValue("id")
	sess, ok := s.getSession(id)
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"detail": "session not found"})
		return
	}
	if !s.canViewSession(claims, sess) {
		writeJSON(w, http.StatusForbidden, map[string]string{"detail": "access denied"})
		return
	}
	s.sessions.Delete(id)
	_ = session.DeleteFiles(s.cfg.RecordingDir, id)
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) handleSessionWS(w http.ResponseWriter, r *http.Request) {
	claims, err := s.parseClaims(r)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
		return
	}
	id := r.PathValue("id")
	sess, ok := s.getSession(id)
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"detail": "session not found"})
		return
	}
	if sess.UserID != claims.Sub && !contains(claims.PlatformRoles, "platform_admin") {
		writeJSON(w, http.StatusForbidden, map[string]string{"detail": "not session owner"})
		return
	}
	ws, err := s.upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer ws.Close()

	rec, err := recording.NewWriter(s.cfg.RecordingDir, id)
	if err != nil {
		_ = ws.WriteMessage(websocket.TextMessage, []byte("recording init failed"))
		return
	}
	defer func() {
		path, _ := rec.Close()
		sess.RecordingPath = path
		sess.RecordingURI = "file://" + path
		if closed, ok := s.sessions.Close(id); ok {
			_ = session.Save(s.cfg.RecordingDir, closed)
			_ = s.events.PublishSessionEvent(context.Background(), events.SessionEventData{
				SessionID:      closed.ID,
				OrganizationID: closed.OrganizationID,
				ProjectID:      closed.ProjectID,
				VMName:         closed.VMName,
				AgentID:        closed.AgentID,
				UserID:         closed.UserID,
				UserEmail:      closed.UserEmail,
				LinuxUser:      closed.LinuxUser,
				Action:         "session.close",
				RecordingURI:   closed.RecordingURI,
			})
		}
	}()

	err = sshbridge.BridgeWebSocket(
		r.Context(),
		ws,
		s.iam,
		s.cfg.SessionTokenSecret,
		sshbridge.SessionTarget{
			OrganizationID: sess.OrganizationID,
			SessionID:      sess.ID,
			AgentID:        sess.AgentID,
			GuestIP:        sess.GuestIP,
			RelayHost:      sess.RelayHost,
			RelayPort:      sess.RelayPort,
			LinuxUser:      sess.LinuxUser,
		},
		rec.WriteInput,
		rec.WriteOutput,
	)
	if err != nil {
		_ = ws.WriteMessage(websocket.TextMessage, []byte("session failed: "+err.Error()))
	}
}

func contains(items []string, want string) bool {
	for _, v := range items {
		if v == want {
			return true
		}
	}
	return false
}
