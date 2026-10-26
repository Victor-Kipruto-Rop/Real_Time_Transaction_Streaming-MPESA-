package co.pesaguard.developer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Developer Portal.
 *
 * Developer projects, sandbox, API-key lifecycle, usage and production-access requests; store only secret hashes.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class DeveloperApplication {
    public static void main(String[] args) {
        SpringApplication.run(DeveloperApplication.class, args);
    }
}
