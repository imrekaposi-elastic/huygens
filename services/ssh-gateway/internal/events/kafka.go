package events

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/segmentio/kafka-go"
)

const (
	topicSessionEvents     = "huy.session.events"
	topicSessionRecording  = "huy.session.recording"
	sessionEventType       = "com.huygens.session.v1"
	sessionRecordingType   = "com.huygens.session.recording.v1"
	sessionDataSchema      = "https://huygens.dev/schemas/kafka/session-event.schema.json"
	sessionRecordingSchema = "https://huygens.dev/schemas/kafka/session-recording.schema.json"
)

type Publisher struct {
	sessionWriter   *kafka.Writer
	recordingWriter *kafka.Writer
}

func NewPublisher(bootstrap string, enabled bool) *Publisher {
	if !enabled || bootstrap == "" {
		return &Publisher{}
	}
	addr := kafka.TCP(bootstrap)
	return &Publisher{
		sessionWriter: &kafka.Writer{
			Addr:     addr,
			Topic:    topicSessionEvents,
			Balancer: &kafka.LeastBytes{},
		},
		recordingWriter: &kafka.Writer{
			Addr:     addr,
			Topic:    topicSessionRecording,
			Balancer: &kafka.LeastBytes{},
		},
	}
}

func (p *Publisher) Close() error {
	var first error
	if p.sessionWriter != nil {
		if err := p.sessionWriter.Close(); err != nil {
			first = err
		}
	}
	if p.recordingWriter != nil {
		if err := p.recordingWriter.Close(); err != nil && first == nil {
			first = err
		}
	}
	return first
}

type SessionEventData struct {
	Version        int    `json:"version"`
	SessionID      string `json:"session_id"`
	OrganizationID string `json:"organization_id"`
	ProjectID      string `json:"project_id"`
	VMName         string `json:"vm_name"`
	AgentID        string `json:"agent_id"`
	GuestIP        string `json:"guest_ip,omitempty"`
	UserID         string `json:"user_id"`
	UserEmail      string `json:"user_email"`
	UserUsername   string `json:"user_username,omitempty"`
	LinuxUser      string `json:"linux_user"`
	Status         string `json:"status,omitempty"`
	StartedAt      string `json:"started_at,omitempty"`
	EndedAt        string `json:"ended_at,omitempty"`
	Action         string `json:"action"`
	RecordingURI   string `json:"recording_uri,omitempty"`
	Timestamp      string `json:"timestamp"`
}

type RecordingEventData struct {
	Version        int     `json:"version"`
	SessionID      string  `json:"session_id"`
	OrganizationID string  `json:"organization_id"`
	ProjectID      string  `json:"project_id"`
	VMName         string  `json:"vm_name"`
	AgentID        string  `json:"agent_id"`
	GuestIP        string  `json:"guest_ip,omitempty"`
	UserID         string  `json:"user_id"`
	UserEmail      string  `json:"user_email"`
	UserUsername   string  `json:"user_username,omitempty"`
	LinuxUser      string  `json:"linux_user"`
	RecordingURI   string  `json:"recording_uri,omitempty"`
	Sequence       int     `json:"sequence"`
	CastTimestamp  float64 `json:"cast_timestamp"`
	Stream           string  `json:"stream"`
	TerminalData     string  `json:"terminal_data"`
	TerminalPlaintext string `json:"terminal_plaintext,omitempty"`
	Timestamp        string  `json:"timestamp"`
}

func (p *Publisher) PublishSessionEvent(ctx context.Context, data SessionEventData) error {
	if p.sessionWriter == nil {
		return nil
	}
	if data.Version == 0 {
		data.Version = 1
	}
	if data.Timestamp == "" {
		data.Timestamp = time.Now().UTC().Format(time.RFC3339Nano)
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
	return p.sessionWriter.WriteMessages(ctx, kafka.Message{
		Key:   []byte(data.SessionID),
		Value: payload,
	})
}

func (p *Publisher) PublishRecordingEvents(ctx context.Context, events []RecordingEventData) error {
	if p.recordingWriter == nil || len(events) == 0 {
		return nil
	}
	messages := make([]kafka.Message, 0, len(events))
	for _, data := range events {
		if data.Version == 0 {
			data.Version = 1
		}
		if data.Timestamp == "" {
			data.Timestamp = time.Now().UTC().Format(time.RFC3339Nano)
		}
		envelope := map[string]any{
			"specversion":     "1.0",
			"id":              uuid.NewString(),
			"source":          "huy-ssh-gateway",
			"type":            sessionRecordingType,
			"datacontenttype": "application/json",
			"dataschema":      sessionRecordingSchema,
			"time":            data.Timestamp,
			"data":            data,
		}
		payload, err := json.Marshal(envelope)
		if err != nil {
			return err
		}
		messages = append(messages, kafka.Message{
			Key:   []byte(data.SessionID),
			Value: payload,
		})
	}
	return p.recordingWriter.WriteMessages(ctx, messages...)
}
