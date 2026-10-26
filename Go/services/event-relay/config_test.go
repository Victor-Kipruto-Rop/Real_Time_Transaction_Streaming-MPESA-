package main

import (
	"testing"
	"time"
)

func setValidEnvironment(t *testing.T) {
	t.Helper()
	t.Setenv("DATABASE_URL", "postgres://localhost/pesaguard?sslmode=disable")
	t.Setenv("KAFKA_BROKERS", "broker-a:9092, broker-b:9092")
	t.Setenv("INSTANCE_ID", "test-instance")
	t.Setenv("POLL_INTERVAL", "")
	t.Setenv("BATCH_SIZE", "")
	t.Setenv("MAX_ATTEMPTS", "")
	t.Setenv("PORT", "")
}

func TestLoadConfigDefaults(t *testing.T) {
	setValidEnvironment(t)
	cfg, err := loadConfig()
	if err != nil { t.Fatal(err) }
	if cfg.PollInterval != 2*time.Second || cfg.BatchSize != 50 || cfg.MaxAttempts != 12 || cfg.Port != "8081" {
		t.Fatalf("unexpected defaults: %+v", cfg)
	}
	if len(cfg.Brokers) != 2 { t.Fatalf("expected two brokers, got %v", cfg.Brokers) }
}
func TestLoadConfigRejectsInvalidValues(t *testing.T) {
	tests := []struct{name, value string}{
		{"POLL_INTERVAL", "10ms"},
		{"POLL_INTERVAL", "not-a-duration"},
		{"BATCH_SIZE", "0"},
		{"BATCH_SIZE", "501"},
		{"MAX_ATTEMPTS", "-1"},
	}
	for _, tc := range tests {
		t.Run(tc.name+"="+tc.value, func(t *testing.T) {
			setValidEnvironment(t)
			t.Setenv(tc.name, tc.value)
			if _, err := loadConfig(); err == nil { t.Fatalf("expected invalid %s to fail", tc.name) }
		})
	}
}
func TestLoadConfigRequiresDatabaseAndBroker(t *testing.T) {
	setValidEnvironment(t)
	t.Setenv("DATABASE_URL", "")
	if _, err := loadConfig(); err == nil { t.Fatal("expected missing DATABASE_URL to fail") }
	setValidEnvironment(t)
	t.Setenv("KAFKA_BROKERS", " , ")
	if _, err := loadConfig(); err == nil { t.Fatal("expected missing broker list to fail") }
}
