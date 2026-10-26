package co.pesaguard.tenant;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Tenant Service.
 *
 * Tenant lifecycle, tenant metadata and trusted tenant-context resolution.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class TenantApplication {
    public static void main(String[] args) {
        SpringApplication.run(TenantApplication.class, args);
    }
}
