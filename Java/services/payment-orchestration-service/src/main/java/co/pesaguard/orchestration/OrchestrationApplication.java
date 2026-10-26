package co.pesaguard.orchestration;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Payment Orchestration.
 *
 * Coordinates supported payment operations and state transitions; ingestion is not execution or settlement.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class OrchestrationApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrchestrationApplication.class, args);
    }
}
