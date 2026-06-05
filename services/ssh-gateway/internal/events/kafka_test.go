package events

import (
	"context"
	"testing"
)

func TestDisabledPublisherNoops(t *testing.T) {
	p := NewPublisher("", false)
	if err := p.PublishSessionEvent(context.Background(), SessionEventData{
		SessionID:      "sess-1",
		OrganizationID: "org-1",
		ProjectID:      "proj-1",
		VMName:         "web-01",
		UserID:         "user-1",
		UserEmail:      "u@example.com",
		LinuxUser:      "huygens",
		Action:         "session.open",
	}); err != nil {
		t.Fatalf("PublishSessionEvent: %v", err)
	}
	if err := p.PublishRecordingEvents(context.Background(), []RecordingEventData{
		{SessionID: "sess-1", Sequence: 1, Stream: "o", TerminalData: "hi"},
	}); err != nil {
		t.Fatalf("PublishRecordingEvents: %v", err)
	}
	if err := p.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
}

func TestPublishRecordingEventsEmpty(t *testing.T) {
	p := NewPublisher("localhost:9092", true)
	if err := p.PublishRecordingEvents(context.Background(), nil); err != nil {
		t.Fatalf("empty publish: %v", err)
	}
	_ = p.Close()
}
