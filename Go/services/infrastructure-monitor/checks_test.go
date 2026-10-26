package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestParseTargets(t *testing.T) {
	targets, err := parseTargets("api=https://api.example.test/healthz, worker=http://worker.internal/healthz")
	if err != nil || len(targets) != 2 { t.Fatalf("targets=%v err=%v", targets, err) }
	if _, err := parseTargets("api=ftp://example.test"); err == nil { t.Fatal("expected invalid scheme to fail") }
	if _, err := parseTargets("api=https://user:pass@example.test"); err == nil { t.Fatal("embedded credentials must fail") }
	if _, err := parseTargets("api=https://example.test,api=https://example.test/healthz"); err == nil { t.Fatal("duplicate name must fail") }
}

func TestMonitorChecksHTTPStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) }))
	defer server.Close()
	monitor := NewMonitor([]Target{{Name:"test", URL:server.URL}}, time.Second)
	result := monitor.Check(context.Background(), monitor.targets[0])
	if !result.Healthy || result.StatusCode != http.StatusOK { t.Fatalf("unexpected result: %+v", result) }
}

func TestMonitorMarksServerErrorUnhealthy(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusServiceUnavailable) }))
	defer server.Close()
	monitor := NewMonitor([]Target{{Name:"test", URL:server.URL}}, time.Second)
	result := monitor.Check(context.Background(), monitor.targets[0])
	if result.Healthy || result.StatusCode != http.StatusServiceUnavailable { t.Fatalf("unexpected result: %+v", result) }
}
