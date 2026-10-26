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

	"github.com/redis/go-redis/v9"
)

type quotaServer struct {
	redis *redis.Client
	token string
	logger *slog.Logger
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	redisURL := strings.TrimSpace(os.Getenv("REDIS_URL"))
	token := os.Getenv("INTERNAL_TOKEN")
	port := strings.TrimSpace(os.Getenv("PORT"))
	if port == "" { port = "8082" }
	if redisURL == "" || len(token) < 32 {
		logger.Error("REDIS_URL and INTERNAL_TOKEN (at least 32 characters) are required")
		os.Exit(2)
	}
	client, err := redisClientFromURL(redisURL)
	if err != nil { logger.Error("invalid REDIS_URL", "error", err); os.Exit(2) }
	defer client.Close()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	pingCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
	err = client.Ping(pingCtx).Err()
	cancel()
	if err != nil { logger.Error("Redis unavailable", "error", err); os.Exit(1) }

	app := &quotaServer{redis: client, token: token, logger: logger}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK); _, _ = w.Write([]byte("ok\n")) })
	mux.Handle("POST /v1/quotas/check", app.internalAuth(http.HandlerFunc(app.check)))
	server := &http.Server{Addr: ":" + port, Handler: mux, ReadHeaderTimeout: 3*time.Second}
	go func() { <-ctx.Done(); shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second); defer cancel(); _ = server.Shutdown(shutdownCtx) }()
	logger.Info("quota engine starting", "port", port)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) { logger.Error("server failed", "error", err); os.Exit(1) }
}

func (s *quotaServer) internalAuth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		provided := r.Header.Get("X-PesaGuard-Internal-Token")
		if provided == "" || subtle.ConstantTimeCompare([]byte(provided), []byte(s.token)) != 1 {
			http.Error(w, "unauthorized", http.StatusUnauthorized); return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *quotaServer) check(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 16*1024)
	defer r.Body.Close()
	var req QuotaRequest
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest); return
	}
	result, err := checkQuota(r.Context(), s.redis, req)
	if err != nil {
		if strings.Contains(err.Error(), "required") || strings.Contains(err.Error(), "must be") || strings.Contains(err.Error(), "environment") {
			http.Error(w, err.Error(), http.StatusBadRequest); return
		}
		s.logger.Error("quota check failed", "error", err)
		http.Error(w, "quota service unavailable", http.StatusServiceUnavailable); return
	}
	w.Header().Set("Content-Type", "application/json")
	if !result.Allowed { w.WriteHeader(http.StatusTooManyRequests) }
	_ = json.NewEncoder(w).Encode(result)
}
