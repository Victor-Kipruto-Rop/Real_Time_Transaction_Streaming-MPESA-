package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"math"
	"strings"
	"time"

	"github.com/segmentio/kafka-go"
)

type Event struct {
	ID       string
	Topic    string
	Key      string
	Payload  []byte
	Attempts int
}

type Relay struct {
	DB          *sql.DB
	Writer      *kafka.Writer
	InstanceID  string
	BatchSize   int
	MaxAttempts int
	Logger      *slog.Logger
}

func (r *Relay) Run(ctx context.Context, interval time.Duration) error {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		if err := r.RunOnce(ctx); err != nil && !errors.Is(err, context.Canceled) {
			r.Logger.Error("outbox relay iteration failed", "error", err)
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
		}
	}
}

// RunOnce claims a bounded batch, publishes it, and records each outcome.
// The resulting guarantee is at-least-once, not exactly-once.
func (r *Relay) RunOnce(ctx context.Context) error {
	events, err := r.claim(ctx)
	if err != nil {
		return err
	}
	for _, event := range events {
		if !json.Valid(event.Payload) {
			if err := r.deadLetter(ctx, event, "payload is not valid JSON"); err != nil {
				r.Logger.Error("failed to persist malformed event to dead letter", "event_id", event.ID, "error", err)
				continue
			}
			continue
		}
		err := r.Writer.WriteMessages(ctx, kafka.Message{
			Topic: event.Topic,
			Key:   []byte(event.Key),
			Value: event.Payload,
			Headers: []kafka.Header{{Key: "pesaguard-event-id", Value: []byte(event.ID)}},
		})
		if err != nil {
			if updateErr := r.retry(ctx, event, err); updateErr != nil {
				r.Logger.Error("failed to persist publish retry", "event_id", event.ID, "error", updateErr)
			}
			continue
		}
		if err := r.markPublished(ctx, event); err != nil {
			// A publish may have succeeded. Leaving the row unpublished causes a safe
			// duplicate on retry; downstream consumers must deduplicate by event ID.
			r.Logger.Error("broker acknowledged but outbox update failed", "event_id", event.ID, "error", err)
		}
	}
	return nil
}

func (r *Relay) claim(ctx context.Context) ([]Event, error) {
	tx, err := r.DB.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	rows, err := tx.QueryContext(ctx, `
SELECT id, topic, event_key, payload, attempts
FROM go_event_outbox
WHERE published_at IS NULL
  AND dead_lettered_at IS NULL
  AND next_attempt_at <= NOW()
  AND (locked_until IS NULL OR locked_until < NOW())
ORDER BY created_at
LIMIT $1
FOR UPDATE SKIP LOCKED`, r.BatchSize)
	if err != nil {
		return nil, err
	}
	var events []Event
	for rows.Next() {
		var e Event
		if err := rows.Scan(&e.ID, &e.Topic, &e.Key, &e.Payload, &e.Attempts); err != nil {
			rows.Close()
			return nil, err
		}
		events = append(events, e)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	for i := range events {
		_, err = tx.ExecContext(ctx, `UPDATE go_event_outbox
SET locked_by=$2, locked_until=NOW() + INTERVAL '10 minutes', attempts=attempts+1
WHERE id=$1`, events[i].ID, r.InstanceID)
		if err != nil {
			return nil, err
		}
		events[i].Attempts++
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return events, nil
}

func (r *Relay) markPublished(ctx context.Context, e Event) error {
	result, err := r.DB.ExecContext(ctx, `UPDATE go_event_outbox
SET published_at=NOW(), locked_by=NULL, locked_until=NULL, last_error=NULL
WHERE id=$1 AND locked_by=$2 AND published_at IS NULL`, e.ID, r.InstanceID)
	if err != nil {
		return err
	}
	n, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if n != 1 {
		return fmt.Errorf("outbox row %s lease was lost before publish acknowledgement was recorded", e.ID)
	}
	return nil
}

func (r *Relay) retry(ctx context.Context, e Event, publishErr error) error {
	message := strings.TrimSpace(publishErr.Error())
	if len(message) > 1000 {
		message = message[:1000]
	}
	if e.Attempts >= r.MaxAttempts {
		return r.deadLetter(ctx, e, message)
	}
	delay := retryBackoff(e.Attempts)
	_, err := r.DB.ExecContext(ctx, `UPDATE go_event_outbox
SET next_attempt_at=NOW() + ($3 * INTERVAL '1 second'),
    locked_by=NULL, locked_until=NULL, last_error=$4
WHERE id=$1 AND locked_by=$2 AND published_at IS NULL`,
		e.ID, r.InstanceID, delay.Seconds(), message)
	return err
}

func (r *Relay) deadLetter(ctx context.Context, e Event, reason string) error {
	tx, err := r.DB.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	_, err = tx.ExecContext(ctx, `INSERT INTO go_event_outbox_dead_letters
(event_id, topic, event_key, payload, attempts, failure_reason, dead_lettered_at)
VALUES ($1,$2,$3,$4,$5,$6,NOW())
ON CONFLICT (event_id) DO UPDATE SET
attempts=EXCLUDED.attempts, failure_reason=EXCLUDED.failure_reason,
dead_lettered_at=EXCLUDED.dead_lettered_at`,
		e.ID, e.Topic, e.Key, e.Payload, e.Attempts, reason)
	if err != nil {
		return err
	}
	_, err = tx.ExecContext(ctx, `UPDATE go_event_outbox
SET dead_lettered_at=NOW(), locked_by=NULL, locked_until=NULL, last_error=$3
WHERE id=$1 AND locked_by=$2 AND published_at IS NULL`, e.ID, r.InstanceID, reason)
	if err != nil {
		return err
	}
	return tx.Commit()
}

func retryBackoff(attempt int) time.Duration {
	if attempt < 1 {
		attempt = 1
	}
	seconds := math.Pow(2, float64(attempt-1))
	if seconds > 300 {
		seconds = 300
	}
	return time.Duration(seconds * float64(time.Second))
}
