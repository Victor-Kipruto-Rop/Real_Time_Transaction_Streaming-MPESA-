package co.pesaguard.compliance;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Compliance and Retention.
 *
 * Retention workflows, compliance evidence and policy enforcement.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class ComplianceApplication {
    public static void main(String[] args) {
        SpringApplication.run(ComplianceApplication.class, args);
    }
}
