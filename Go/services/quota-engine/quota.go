package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

type QuotaRequest struct {
	TenantID     string `json:"tenantId"`
	Environment  string `json:"environment"`
	APIKeyID     string `json:"apiKeyId"`
	Route        string `json:"route"`
	Limit        int64  `json:"limit"`
	WindowSecond int64  `json:"windowSeconds"`
}

type QuotaResult struct {
	Allowed bool  `json:"allowed"`
	Limit   int64 `json:"limit"`
	Window  int64 `json:"windowSeconds"`
}

var fixedWindowScript = redis.NewScript(`
local count = redis.call("INCR", KEYS[1])
if count == 1 then redis.call("EXPIRE", KEYS[1], ARGV[1]) end
if count <= tonumber(ARGV[2]) then return 1 else return 0 end
`)

func validateQuotaRequest(req QuotaRequest) error {
	for name, value := range map[string]string{
		"tenantId": req.TenantID, "apiKeyId": req.APIKeyID, "route": req.Route,
	} {
		if strings.TrimSpace(value) == "" || len(value) > 256 {
			return fmt.Errorf("%s is required and must be at most 256 characters", name)
		}
	}
	if req.Environment != "sandbox" && req.Environment != "production" {
		return errors.New("environment must be sandbox or production")
	}
	if req.Limit < 1 || req.Limit > 1_000_000 {
		return errors.New("limit must be between 1 and 1000000")
	}
	if req.WindowSecond < 1 || req.WindowSecond > 86400 {
		return errors.New("windowSeconds must be between 1 and 86400")
	}
	return nil
}

func quotaKey(req QuotaRequest) string {
	// Hash identifiers to keep tenant and API-key identifiers out of Redis key listings.
	raw := strings.Join([]string{req.TenantID, req.Environment, req.APIKeyID, req.Route}, "\x00")
	sum := sha256.Sum256([]byte(raw))
	return "pesaguard:quota:v1:" + hex.EncodeToString(sum[:])
}

func checkQuota(ctx context.Context, client redis.Scripter, req QuotaRequest) (QuotaResult, error) {
	if err := validateQuotaRequest(req); err != nil { return QuotaResult{}, err }
	allowed, err := fixedWindowScript.Run(ctx, client, []string{quotaKey(req)}, req.WindowSecond, req.Limit).Int64()
	if err != nil { return QuotaResult{}, err }
	return QuotaResult{Allowed: allowed == 1, Limit: req.Limit, Window: req.WindowSecond}, nil
}

func redisClientFromURL(raw string) (*redis.Client, error) {
	opt, err := redis.ParseURL(raw)
	if err != nil { return nil, err }
	opt.DialTimeout = 2 * time.Second
	opt.ReadTimeout = 2 * time.Second
	opt.WriteTimeout = 2 * time.Second
	return redis.NewClient(opt), nil
}
