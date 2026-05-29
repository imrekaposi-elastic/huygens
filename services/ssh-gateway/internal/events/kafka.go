package events

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/segmentio/kafka-go"
)

const (
	topicSessionEvents    = "huy.session.events"
	sessionEventType      = "com.huygens.session.v1"
	sessionDataSchema     = "https://huygens.dev/schemas/kafka/session-event.schema.json"
)

type Publisher struct {
	writer *kafka.Writer
}

func NewPublisher(bootstrap string, enabled bool) *Publisher {
	if !enabled || bootstrap == "" {
		return &Publisher{}
	}
	return &Publisher{
		writer: &kafka.Writer{
			Addr:     kafka.TCP(bootstrap),
			Topic:    topicSessionEvents,
			Balancer: &kafka.LeastBytes{},
		},
	}
}

func (p *Publisher) Close() error {
	if p.writer == nil {
		return nil
	}
	return p.writer.Close()
}

type SessionEventData struct {
	Version        int    `json:"version"`
	SessionID      string `json:"session_id"`
	OrganizationID string `json:"organization_id"`
	ProjectID      string `json:"project_id"`
	VMName         string `json:"vm_name"`
	AgentID        string `json:"agent_id"`
	UserID         string `json:"user_id"`
	UserEmail      string `json:"user_email"`
	LinuxUser      string `json:"linux_user"`
	Action         string `json:"action"`
	RecordingURI   string `json:"recording_uri,omitempty"`
	Timestamp      string `json:"timestamp"`
}

func (p *Publisher) PublishSessionEvent(ctx context.Context, data SessionEventData) error {
	if p.writer == nil {
		return nil
	}
	if data.Version == 0 {
		data.Version = 1
	}
	if data.Timestamp == "" {
		data.Timestamp = time.Now().UTC().Format(time.RFC3339)
	}
	envelope := map[string]any{
		"specversion":     "1.0",
		"id":              uuid.NewString(),
		"source":          "huy-ssh-gateway",
		"type":            sessionEventType,
		"datacontenttype": "application/json",
		"dataschema":      sessionDataSchema,
		"time":            data.Timestamp,
		"data":            data,
	}
	payload, err := json.Marshal(envelope)
	if err != nil {
		return err
	}
	return p.writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(data.SessionID),
		Value: payload,
	})
}
