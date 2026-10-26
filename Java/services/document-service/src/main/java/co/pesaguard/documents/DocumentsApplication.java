package co.pesaguard.documents;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Document and Evidence.
 *
 * Private document metadata, access checks, MIME validation and malware-scan/quarantine states.
 *
 * This is an initial application scaffold, not a completed business workflow.
 * Implement domain validation, authorization, persistence and failure recovery
 * before enabling production traffic.
 */
@SpringBootApplication
public class DocumentsApplication {
    public static void main(String[] args) {
        SpringApplication.run(DocumentsApplication.class, args);
    }
}
