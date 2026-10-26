package co.pesaguard.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * API Gateway.
 *
 * Routing, request correlation and gateway policy; service-level authorization remains mandatory.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
