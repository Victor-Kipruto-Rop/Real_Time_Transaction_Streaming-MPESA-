package main

import (
	"errors"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	DatabaseURL  string
	Brokers      []string
	InstanceID   string
	PollInterval time.Duration
	BatchSize    int
	MaxAttempts  int
	Port         string
}

func loadConfig() (Config, error) {
	cfg := Config{
		DatabaseURL: strings.TrimSpace(os.Getenv("DATABASE_URL")),
		Brokers: splitCSV(os.Getenv("KAFKA_BROKERS")),
		InstanceID: strings.TrimSpace(os.Getenv("INSTANCE_ID")),
		PollInterval: 2 * time.Second,
		BatchSize: 50,
		MaxAttempts: 12,
		Port: strings.TrimSpace(os.Getenv("PORT")),
	}
	if cfg.InstanceID == "" {
		host, err := os.Hostname()
		if err != nil || strings.TrimSpace(host) == "" {
			host = "unknown-host"
		}
		cfg.InstanceID = host + "-" + strconv.Itoa(os.Getpid())
	}
	if cfg.Port == "" {
		cfg.Port = "8081"
	}
	if raw := strings.TrimSpace(os.Getenv("POLL_INTERVAL")); raw != "" {
		d, err := time.ParseDuration(raw)
		if err != nil || d < 250*time.Millisecond {
			return Config{}, errors.New("POLL_INTERVAL must be a duration of at least 250ms")
		}
		cfg.PollInterval = d
	}
	if raw := strings.TrimSpace(os.Getenv("BATCH_SIZE")); raw != "" {
		n, err := strconv.Atoi(raw)
		if err != nil || n < 1 || n > 500 {
			return Config{}, errors.New("BATCH_SIZE must be between 1 and 500")
		}
		cfg.BatchSize = n
	}
	if raw := strings.TrimSpace(os.Getenv("MAX_ATTEMPTS")); raw != "" {
		n, err := strconv.Atoi(raw)
		if err != nil || n < 1 || n > 100 {
			return Config{}, errors.New("MAX_ATTEMPTS must be between 1 and 100")
		}
		cfg.MaxAttempts = n
	}
	if cfg.DatabaseURL == "" {
		return Config{}, errors.New("DATABASE_URL is required")
	}
	if len(cfg.Brokers) == 0 {
		return Config{}, errors.New("KAFKA_BROKERS must contain at least one broker")
	}
	return cfg, nil
}

func splitCSV(raw string) []string {
	var values []string
	for _, item := range strings.Split(raw, ",") {
		if value := strings.TrimSpace(item); value != "" {
			values = append(values, value)
		}
	}
	return values
}
