package co.pesaguard.integrations;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Integration Registry.
 *
 * Provider capabilities, environment references and integration health.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class IntegrationsApplication {
    public static void main(String[] args) {
        SpringApplication.run(IntegrationsApplication.class, args);
    }
}
