package co.pesaguard.reconciliation;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Reconciliation.
 *
 * Ledger matching and persisted reconciliation decisions.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class ReconciliationApplication {
    public static void main(String[] args) {
        SpringApplication.run(ReconciliationApplication.class, args);
    }
}
