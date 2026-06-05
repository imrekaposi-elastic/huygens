package telemetry

import (
	"context"
	"os"
	"testing"
)

func TestInitDisabled(t *testing.T) {
	t.Setenv("OTEL_SDK_DISABLED", "true")
	shutdown, err := Init(context.Background())
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	if err := shutdown(context.Background()); err != nil {
		t.Fatalf("shutdown: %v", err)
	}
}

func TestInitWithoutExporterEndpoint(t *testing.T) {
	t.Setenv("OTEL_SDK_DISABLED", "false")
	t.Setenv("OTEL_SERVICE_NAME", "huy-breakout-test")
	_ = os.Unsetenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	shutdown, err := Init(context.Background())
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	if err := shutdown(context.Background()); err != nil {
		t.Fatalf("shutdown: %v", err)
	}
}

func TestParseResourceAttributes(t *testing.T) {
	t.Setenv("OTEL_RESOURCE_ATTRIBUTES", "huy.org.id=org-1,empty=,bad")
	attrs := parseResourceAttributes()
	if len(attrs) != 2 {
		t.Fatalf("attrs = %v, want 2", attrs)
	}
	if string(attrs[0].Key) != "huy.org.id" || attrs[0].Value.AsString() != "org-1" {
		t.Fatalf("unexpected attr: %v", attrs[0])
	}
	if string(attrs[1].Key) != "empty" || attrs[1].Value.AsString() != "" {
		t.Fatalf("unexpected empty attr: %v", attrs[1])
	}
}

func TestGrpcEndpoint(t *testing.T) {
	host, err := grpcEndpoint("http://collector:4317")
	if err != nil || host != "collector:4317" {
		t.Fatalf("grpcEndpoint http = %q err=%v", host, err)
	}
	host, err = grpcEndpoint("collector:4317")
	if err != nil || host != "collector:4317" {
		t.Fatalf("grpcEndpoint bare = %q err=%v", host, err)
	}
}

func TestOtlpProtocolHelpers(t *testing.T) {
	_ = os.Unsetenv("OTEL_EXPORTER_OTLP_PROTOCOL")
	if useHTTPExporter() {
		t.Fatal("default should be grpc")
	}
	t.Setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
	if !useHTTPExporter() {
		t.Fatal("expected http exporter")
	}
	if otlpProtocol() != "http/protobuf" {
		t.Fatalf("protocol = %q", otlpProtocol())
	}
}
