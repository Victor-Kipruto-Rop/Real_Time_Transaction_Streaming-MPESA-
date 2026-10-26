package co.pesaguard.webhooks;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Webhook Delivery.
 *
 * Tenant subscriptions, signed delivery, retries, replay protection and delivery history.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class WebhooksApplication {
    public static void main(String[] args) {
        SpringApplication.run(WebhooksApplication.class, args);
    }
}
