package config

import "os"

type Config struct {
	Addr                 string
	JWTSecret            string
	JWTIssuer            string
	IAMURL               string
	IAMServiceToken      string
	InventoryURL         string
	InventoryServiceToken string
	RecordingDir         string
	KafkaBootstrap       string
	KafkaEnabled         bool
	SessionTokenSecret   string
}

func Load() Config {
	return Config{
		Addr:                  env("HUY_SSH_GATEWAY_HOST", "0.0.0.0:8087"),
		JWTSecret:             env("JWT_SECRET", "dev-jwt-secret-change-me-minimum-32-chars"),
		JWTIssuer:             env("JWT_ISSUER", "huy-iam"),
		IAMURL:                env("IAM_URL", "http://iam:8081"),
		IAMServiceToken:       env("IAM_SERVICE_TOKEN", "dev-iam-service-token"),
		InventoryURL:          env("INVENTORY_URL", "http://inventory:8083"),
		InventoryServiceToken: env("INVENTORY_SERVICE_TOKEN", "dev-inventory-service-token"),
		RecordingDir:          env("SSH_RECORDING_DIR", "/data/ssh-recordings"),
		KafkaBootstrap:        env("KAFKA_BOOTSTRAP", "kafka:9092"),
		KafkaEnabled:          env("KAFKA_PUBLISH_ENABLED", "true") == "true",
		SessionTokenSecret:    env("SSH_GATEWAY_SERVICE_TOKEN", "dev-ssh-gateway-service-token"),
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
