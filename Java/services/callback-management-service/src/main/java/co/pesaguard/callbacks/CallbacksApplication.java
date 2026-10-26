package co.pesaguard.callbacks;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Callback Management.
 *
 * Provider callback configuration and registration metadata; Python remains the ingestion owner initially.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class CallbacksApplication {
    public static void main(String[] args) {
        SpringApplication.run(CallbacksApplication.class, args);
    }
}
