package main

import "testing"

func TestQuotaValidation(t *testing.T) {
	valid := QuotaRequest{TenantID:"tenant-1", Environment:"sandbox", APIKeyID:"key-1", Route:"GET /v1/transactions", Limit:100, WindowSecond:60}
	if err := validateQuotaRequest(valid); err != nil { t.Fatalf("valid request rejected: %v", err) }
	cases := []QuotaRequest{
		{Environment:"sandbox", APIKeyID:"key", Route:"/", Limit:1, WindowSecond:60},
		{TenantID:"t", Environment:"production", APIKeyID:"k", Route:"/", Limit:0, WindowSecond:60},
		{TenantID:"t", Environment:"test", APIKeyID:"k", Route:"/", Limit:1, WindowSecond:60},
		{TenantID:"t", Environment:"sandbox", APIKeyID:"k", Route:"/", Limit:1, WindowSecond:86401},
	}
	for i, req := range cases {
		if err := validateQuotaRequest(req); err == nil { t.Errorf("case %d should fail validation", i) }
	}
}

func TestQuotaKeyDoesNotExposeIdentifiers(t *testing.T) {
	req := QuotaRequest{TenantID:"sensitive-tenant-name", Environment:"production", APIKeyID:"secret-key-id", Route:"/payments"}
	key := quotaKey(req)
	if len(key) < 40 { t.Fatalf("unexpected key: %q", key) }
	for _, sensitive := range []string{req.TenantID, req.APIKeyID} {
		if sensitive != "" && contains(key, sensitive) { t.Fatalf("key leaks identifier %q", sensitive) }
	}
}

func contains(s, sub string) bool {
	for i:=0; i+len(sub)<=len(s); i++ { if s[i:i+len(sub)] == sub { return true } }
	return false
}
