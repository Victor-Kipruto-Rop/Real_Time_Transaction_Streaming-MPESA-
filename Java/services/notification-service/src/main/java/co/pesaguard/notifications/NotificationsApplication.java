package co.pesaguard.notifications;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Notifications.
 *
 * Email/SMS/in-app notification orchestration, preferences and delivery state.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class NotificationsApplication {
    public static void main(String[] args) {
        SpringApplication.run(NotificationsApplication.class, args);
    }
}
