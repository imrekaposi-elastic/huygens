package session

import (
	"sync"
	"time"
)

type Session struct {
	ID             string     `json:"id"`
	OrganizationID string     `json:"organization_id"`
	ProjectID      string     `json:"project_id"`
	VMName         string     `json:"vm_name"`
	AgentID        string     `json:"agent_id"`
	GuestIP        string     `json:"guest_ip"`
	RelayHost      string     `json:"relay_host"`
	RelayPort      int        `json:"relay_port"`
	RelayWSURL     string     `json:"relay_ws_url"`
	LinuxUser      string     `json:"linux_user"`
	UserID         string     `json:"user_id"`
	UserEmail      string     `json:"user_email"`
	UserUsername   string     `json:"user_username"`
	Status         string     `json:"status"`
	StartedAt      time.Time  `json:"started_at"`
	EndedAt        *time.Time `json:"ended_at,omitempty"`
	RecordingPath  string     `json:"recording_path"`
	RecordingURI   string     `json:"recording_uri"`
}

type Store struct {
	mu       sync.RWMutex
	sessions map[string]*Session
}

func NewStore() *Store {
	return &Store{sessions: make(map[string]*Session)}
}

func (s *Store) Put(sess *Session) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.sessions[sess.ID] = sess
}

func (s *Store) Get(id string) (*Session, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	sess, ok := s.sessions[id]
	return sess, ok
}

func (s *Store) List(orgID string) []*Session {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*Session, 0)
	for _, sess := range s.sessions {
		if orgID == "" || sess.OrganizationID == orgID {
			out = append(out, sess)
		}
	}
	return out
}

func (s *Store) Close(id string) (*Session, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	sess, ok := s.sessions[id]
	if !ok {
		return nil, false
	}
	now := time.Now().UTC()
	sess.Status = "closed"
	sess.EndedAt = &now
	return sess, true
}

func (s *Store) Delete(id string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.sessions, id)
}
