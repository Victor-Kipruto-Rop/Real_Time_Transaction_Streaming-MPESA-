package co.pesaguard.onboarding;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Merchant Onboarding and KYB.
 *
 * Verification cases, evidence workflow and real provider adapters with pending/manual-review states.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class OnboardingApplication {
    public static void main(String[] args) {
        SpringApplication.run(OnboardingApplication.class, args);
    }
}
