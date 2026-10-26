package main

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

type Target struct {
	Name string `json:"name"`
	URL string `json:"url"`
}

type CheckResult struct {
	Name        string    `json:"name"`
	Healthy     bool      `json:"healthy"`
	StatusCode  int       `json:"statusCode,omitempty"`
	LatencyMS   int64     `json:"latencyMs"`
	CheckedAt   time.Time `json:"checkedAt"`
	Error       string    `json:"error,omitempty"`
}

type Monitor struct {
	client *http.Client
	targets []Target
	mu sync.RWMutex
	results []CheckResult
}

func parseTargets(raw string) ([]Target, error) {
	var targets []Target
	seen := map[string]bool{}
	for _, item := range strings.Split(raw, ",") {
		item = strings.TrimSpace(item)
		if item == "" { continue }
		parts := strings.SplitN(item, "=", 2)
		if len(parts) != 2 { return nil, fmt.Errorf("target %q must use name=https://host/healthz", item) }
		name, targetURL := strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
		if name == "" || seen[name] { return nil, fmt.Errorf("target name %q is empty or duplicated", name) }
		parsed, err := url.Parse(targetURL)
		if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" || parsed.User != nil {
			return nil, fmt.Errorf("target %q must be an http(s) URL without embedded credentials", name)
		}
		if _, _, err := net.SplitHostPort(parsed.Host); err != nil && !strings.Contains(parsed.Host, ":") {
			// A hostname without an explicit port is valid.
		}
		seen[name] = true
		targets = append(targets, Target{Name:name, URL:targetURL})
	}
	if len(targets) == 0 { return nil, errors.New("CHECK_TARGETS must configure at least one target") }
	return targets, nil
}

func NewMonitor(targets []Target, timeout time.Duration) *Monitor {
	return &Monitor{client:&http.Client{Timeout:timeout, CheckRedirect:func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }}, targets:targets}
}

func (m *Monitor) Check(ctx context.Context, target Target) CheckResult {
	start := time.Now()
	result := CheckResult{Name:target.Name, CheckedAt:start.UTC()}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, target.URL, nil)
	if err != nil { result.Error = "invalid request"; result.LatencyMS = time.Since(start).Milliseconds(); return result }
	resp, err := m.client.Do(req)
	result.LatencyMS = time.Since(start).Milliseconds()
	if err != nil { result.Error = "target unreachable"; return result }
	defer resp.Body.Close()
	result.StatusCode = resp.StatusCode
	result.Healthy = resp.StatusCode >= 200 && resp.StatusCode < 400
	if !result.Healthy { result.Error = "unexpected HTTP status" }
	return result
}

func (m *Monitor) Refresh(ctx context.Context) {
	results := make([]CheckResult, 0, len(m.targets))
	for _, target := range m.targets {
		checkCtx, cancel := context.WithTimeout(ctx, m.client.Timeout)
		results = append(results, m.Check(checkCtx, target))
		cancel()
	}
	m.mu.Lock()
	m.results = results
	m.mu.Unlock()
}

func (m *Monitor) Snapshot() []CheckResult {
	m.mu.RLock()
	defer m.mu.RUnlock()
	copyOfResults := make([]CheckResult, len(m.results))
	copy(copyOfResults, m.results)
	return copyOfResults
}
