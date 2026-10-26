package co.pesaguard.permissions;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Team and Permissions.
 *
 * Membership, role assignment and tenant-scoped authorization policies.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class PermissionsApplication {
    public static void main(String[] args) {
        SpringApplication.run(PermissionsApplication.class, args);
    }
}
