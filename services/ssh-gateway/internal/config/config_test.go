package config

import (
	"testing"
)

func TestLoadUsesEnvOverrides(t *testing.T) {
	t.Setenv("HUY_SSH_GATEWAY_HOST", "127.0.0.1:9999")
	t.Setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
	t.Setenv("JWT_ISSUER", "test-issuer")
	t.Setenv("IAM_URL", "http://iam.test")
	t.Setenv("INVENTORY_URL", "http://inventory.test")
	t.Setenv("KAFKA_PUBLISH_ENABLED", "false")
	t.Setenv("SSH_RECORDING_DIR", "/tmp/recordings")

	cfg := Load()
	if cfg.Addr != "127.0.0.1:9999" {
		t.Fatalf("addr = %q", cfg.Addr)
	}
	if cfg.JWTSecret != "test-secret-32-chars-minimum-length!" {
		t.Fatalf("jwt secret mismatch")
	}
	if cfg.IAMURL != "http://iam.test" || cfg.InventoryURL != "http://inventory.test" {
		t.Fatalf("service urls: iam=%q inventory=%q", cfg.IAMURL, cfg.InventoryURL)
	}
	if cfg.KafkaEnabled {
		t.Fatal("expected kafka disabled")
	}
	if cfg.RecordingDir != "/tmp/recordings" {
		t.Fatalf("recording dir = %q", cfg.RecordingDir)
	}
}
