package main

import (
	"testing"
	"time"
)

func TestRetryBackoffCapsAtFiveMinutes(t *testing.T) {
	if got := retryBackoff(1); got != time.Second { t.Fatalf("attempt 1: got %s", got) }
	if got := retryBackoff(4); got != 8*time.Second { t.Fatalf("attempt 4: got %s", got) }
	if got := retryBackoff(30); got != 5*time.Minute { t.Fatalf("large attempt: got %s", got) }
}

func TestSplitCSVTrimsAndDropsEmptyValues(t *testing.T) {
	got := splitCSV(" broker-a:9092, ,broker-b:9092 ")
	if len(got) != 2 || got[0] != "broker-a:9092" || got[1] != "broker-b:9092" {
		t.Fatalf("unexpected brokers: %#v", got)
	}
}
