package main

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	targets, err := parseTargets(os.Getenv("CHECK_TARGETS"))
	if err != nil { logger.Error("invalid CHECK_TARGETS", "error", err); os.Exit(2) }
	token := os.Getenv("INTERNAL_TOKEN")
	if len(token) < 32 { logger.Error("INTERNAL_TOKEN must contain at least 32 characters"); os.Exit(2) }
	port := strings.TrimSpace(os.Getenv("PORT"))
	if port == "" { port = "8083" }
	monitor := NewMonitor(targets, 3*time.Second)
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	monitor.Refresh(ctx)
	go func() {
		ticker := time.NewTicker(15*time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done(): return
			case <-ticker.C: monitor.Refresh(ctx)
			}
		}
	}()
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK); _, _ = w.Write([]byte("ok\n")) })
	mux.Handle("GET /v1/health/targets", internalAuth(token, http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		results := monitor.Snapshot()
		allHealthy := len(results) > 0
		for _, result := range results { if !result.Healthy { allHealthy = false } }
		w.Header().Set("Content-Type", "application/json")
		if !allHealthy { w.WriteHeader(http.StatusServiceUnavailable) }
		_ = json.NewEncoder(w).Encode(map[string]any{"checkedAt":time.Now().UTC(), "healthy":allHealthy, "targets":results})
	})))
	server := &http.Server{Addr:":"+port, Handler:mux, ReadHeaderTimeout:3*time.Second}
	go func() { <-ctx.Done(); shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second); defer cancel(); _ = server.Shutdown(shutdownCtx) }()
	logger.Info("infrastructure monitor starting", "port", port, "target_count", len(targets))
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) { logger.Error("server failed", "error", err); os.Exit(1) }
}

func internalAuth(token string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		provided := r.Header.Get("X-PesaGuard-Internal-Token")
		if provided == "" || subtle.ConstantTimeCompare([]byte(provided), []byte(token)) != 1 {
			http.Error(w, "unauthorized", http.StatusUnauthorized); return
		}
		next.ServeHTTP(w, r)
	})
}
