package main

import (
	"context"
	"database/sql"
	"errors"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/segmentio/kafka-go"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	cfg, err := loadConfig()
	if err != nil { logger.Error("invalid configuration", "error", err); os.Exit(2) }

	db, err := sql.Open("pgx", cfg.DatabaseURL)
	if err != nil { logger.Error("open database", "error", err); os.Exit(1) }
	defer db.Close()
	db.SetMaxOpenConns(8)
	db.SetMaxIdleConns(4)
	db.SetConnMaxLifetime(5 * time.Minute)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	err = db.PingContext(pingCtx)
	cancel()
	if err != nil { logger.Error("database unavailable", "error", err); os.Exit(1) }

	writer := &kafka.Writer{
		Addr: kafka.TCP(cfg.Brokers...),
		Balancer: &kafka.Hash{},
		RequiredAcks: kafka.RequireAll,
		Async: false,
		BatchTimeout: 10 * time.Millisecond,
	}
	defer func() { if err := writer.Close(); err != nil { logger.Error("close Kafka writer", "error", err) } }()

	relay := &Relay{DB: db, Writer: writer, InstanceID: cfg.InstanceID,
		BatchSize: cfg.BatchSize, MaxAttempts: cfg.MaxAttempts, Logger: logger}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK); _, _ = w.Write([]byte("ok\n"))
	})
	server := &http.Server{Addr: ":" + cfg.Port, Handler: mux, ReadHeaderTimeout: 3*time.Second}
	go func() {
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("health server failed", "error", err); stop()
		}
	}()
	logger.Info("event relay started", "instance_id", cfg.InstanceID, "batch_size", cfg.BatchSize)
	if err := relay.Run(ctx, cfg.PollInterval); err != nil && !errors.Is(err, context.Canceled) {
		log.Printf("relay stopped: %v", err)
	}
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()
	_ = server.Shutdown(shutdownCtx)
}
