# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of M-Pesa Real-Time Transaction Streaming Pipeline seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **kiprutovictor39@gmail.com**

Include the following information:
- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (Critical: 7 days, High: 14 days, Medium: 30 days)

## Security Best Practices

### Authentication & Authorization

1. **API Keys & Secrets**
   - Never commit API keys, passwords, or secrets to version control
   - Use environment variables for sensitive configuration
   - Rotate credentials regularly (every 90 days minimum)
   - Use strong, unique passwords (minimum 16 characters)

2. **Daraja API Credentials**
   - Store Consumer Key and Consumer Secret securely
   - Use separate credentials for sandbox and production
   - Implement token caching with proper expiration
   - Monitor for unauthorized API access

3. **Database Access**
   - Use IAM authentication for AWS RDS when possible
   - Implement least privilege access control
   - Use connection pooling with proper limits
   - Enable SSL/TLS for database connections

### Data Protection

1. **Data in Transit**
   - Use HTTPS/TLS 1.2+ for all API communications
   - Implement certificate pinning for critical connections
   - Validate SSL certificates
   - Use secure WebSocket connections (WSS)

2. **Data at Rest**
   - Encrypt sensitive data in PostgreSQL
   - Use encrypted volumes for data storage
   - Implement database encryption at rest
   - Secure backup encryption

3. **PII Protection**
   - Mask phone numbers in logs (show only last 4 digits)
   - Hash customer identifiers where possible
   - Implement data retention policies
   - Comply with GDPR/data protection regulations

### Infrastructure Security

1. **Docker Security**
   - Use official base images
   - Scan images for vulnerabilities (Trivy, Snyk)
   - Run containers as non-root users
   - Implement resource limits
   - Keep images updated

2. **Network Security**
   - Implement network segmentation
   - Use private subnets for databases
   - Configure security groups properly
   - Enable VPC flow logs
   - Implement DDoS protection

3. **Kubernetes Security** (if applicable)
   - Use RBAC for access control
   - Implement pod security policies
   - Use network policies
   - Enable audit logging
   - Scan for misconfigurations

### Application Security

1. **Input Validation**
   - Validate all webhook payloads
   - Sanitize user inputs
   - Implement request size limits
   - Use parameterized queries (prevent SQL injection)
   - Validate data types and formats

2. **Rate Limiting**
   - Implement per-IP rate limiting
   - Use token bucket algorithm
   - Configure appropriate limits (default: 120 req/min)
   - Monitor for abuse patterns

3. **Error Handling**
   - Never expose stack traces to users
   - Log errors securely
   - Implement proper exception handling
   - Use generic error messages externally

4. **Dependency Management**
   - Regularly update dependencies
   - Use `safety` to check for vulnerabilities
   - Pin dependency versions
   - Review dependency licenses

### Monitoring & Logging

1. **Security Logging**
   - Log all authentication attempts
   - Log authorization failures
   - Log suspicious activities
   - Implement centralized logging
   - Set up alerts for security events

2. **Audit Trail**
   - Log all transaction modifications
   - Track user actions
   - Maintain immutable logs
   - Implement log retention policies

3. **Monitoring**
   - Monitor for unusual patterns
   - Set up fraud detection alerts
   - Track failed login attempts
   - Monitor API usage patterns

### Compliance

1. **PCI-DSS Considerations**
   - Never store full card numbers
   - Implement secure payment processing
   - Maintain audit logs
   - Regular security assessments

2. **GDPR Compliance**
   - Implement right to erasure
   - Data portability support
   - Privacy by design
   - Data processing agreements

3. **Local Regulations**
   - Comply with Kenya Data Protection Act
   - Follow CBK guidelines for financial data
   - Implement required reporting

## Security Checklist

### Development

- [ ] Code review for security issues
- [ ] Static code analysis (Bandit)
- [ ] Dependency vulnerability scanning
- [ ] Secret scanning (TruffleHog)
- [ ] Input validation implemented
- [ ] Error handling reviewed
- [ ] Logging configured properly

### Deployment

- [ ] Environment variables configured
- [ ] SSL/TLS certificates valid
- [ ] Firewall rules configured
- [ ] Security groups reviewed
- [ ] Monitoring alerts set up
- [ ] Backup encryption enabled
- [ ] Access controls implemented

### Production

- [ ] Regular security audits
- [ ] Penetration testing completed
- [ ] Incident response plan ready
- [ ] Disaster recovery tested
- [ ] Compliance requirements met
- [ ] Security training completed
- [ ] Documentation updated

## Incident Response

### Response Plan

1. **Detection**
   - Monitor alerts and logs
   - Investigate suspicious activities
   - Confirm security incident

2. **Containment**
   - Isolate affected systems
   - Prevent further damage
   - Preserve evidence

3. **Eradication**
   - Remove threat
   - Patch vulnerabilities
   - Update security controls

4. **Recovery**
   - Restore systems
   - Verify integrity
   - Resume operations

5. **Lessons Learned**
   - Document incident
   - Update procedures
   - Improve defenses

### Contact Information

- **Security Team**: kiprutovictor39@gmail.com
- **Emergency Contact**: +254723484552
- **Incident Response**: kiprutovictor39@gmail.com

## Security Tools

### Recommended Tools

- **SAST**: Bandit, SonarQube
- **DAST**: OWASP ZAP
- **Dependency Scanning**: Safety, Snyk
- **Container Scanning**: Trivy, Clair
- **Secret Scanning**: TruffleHog, GitGuardian
- **Monitoring**: Prometheus, Grafana
- **SIEM**: ELK Stack, Splunk

## Updates

This security policy is reviewed and updated quarterly. Last update: 2026-06-13

## Acknowledgments

We appreciate the security research community and will acknowledge researchers who responsibly disclose vulnerabilities (with their permission).
