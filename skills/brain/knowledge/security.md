# Security Best Practices

These guidelines apply to all security-related skills, covering application security, DevSecOps, and operational security.

---

## 1. Core Mindset

- **Defense in depth**: Multiple layers of protection; never rely on a single control.
- **Least privilege**: Grant only the minimum permissions needed for the task.
- **Zero trust**: Never trust, always verify. Authenticate and authorize every request.
- **Assume breach**: Design for containment. Limit blast radius.
- **Shift left**: Integrate security into development, not just deployment.

---

## 2. Application Security

### Input Validation

- Validate all user input at system boundaries (type, length, format, range).
- Use allowlists over denylists when possible.
- Never trust client-side validation alone; always validate server-side.

### Injection Prevention

- **SQL Injection**: Parameterized queries, prepared statements. Never string concatenation.
- **Command Injection**: Avoid shell execution with user input. Use safe APIs.
- **XSS**: Escape output by context (HTML, JS, URL). Use framework auto-escaping.
- **SSRF**: Validate and allowlist outbound URLs.

### Authentication & Authorization

- Use established frameworks/libraries; never roll your own crypto.
- Store passwords with strong hashing (bcrypt, argon2, scrypt).
- Use HTTP-only, Secure, SameSite cookies for session tokens.
- Implement RBAC or ABAC at the application layer.
- Enforce MFA for sensitive operations.

### Secrets Management

- Never hardcode secrets in source code.
- Use environment variables, vaults (HashiCorp Vault, Azure Key Vault, AWS Secrets Manager).
- Rotate secrets regularly.
- Never log secrets, tokens, or credentials.
- An embedded/local database is not encryption: to a same-user or filesystem-read adversary, a secret
  stored in SQLite or similar is plaintext unless the store or the value itself is actually encrypted.

---

## 3. Secure Development Lifecycle

### Static Analysis (SAST)

- Integrate SAST tools into CI/CD (Semgrep, SonarQube, Bandit, Roslyn analyzers).
- Fix critical/high findings before merge.
- Map findings to CWE for consistent categorization.

### Dependency Scanning

- Scan dependencies for known vulnerabilities (Dependabot, Snyk, OWASP Dependency-Check).
- Generate SBOM (Software Bill of Materials) for supply chain visibility.
- Pin dependency versions; review updates before applying.

### Code Review

- Review security-sensitive code changes with extra scrutiny.
- Check for: hardcoded secrets, injection vectors, broken auth, excessive permissions.

---

## 4. Infrastructure Security

- Encrypt data at rest and in transit (TLS 1.2+).
- Network segmentation: isolate workloads, use private endpoints.
- Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options).
- Rate limiting and throttling on public endpoints.
- WAF (Web Application Firewall) for public-facing services.

---

## 5. Monitoring & Incident Response

- Log security-relevant events (auth failures, permission denials, anomalies).
- Never log sensitive data (passwords, tokens, PII).
- Alert on security indicators (brute force, unusual access patterns).
- Have an incident response plan: roles, communication, containment, recovery.
- Conduct post-incident reviews to improve defenses.

---

## 6. Compliance Awareness

- Understand which regulations apply (GDPR, HIPAA, SOC2, PCI-DSS, ISO 27001).
- Data classification: know what data you handle and its sensitivity level.
- Data minimization: collect only what's needed, retain only as long as required.
- Document security decisions and controls for audit readiness.

---

## 7. Threat Modeling

- Use STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation of Privilege) for systematic analysis.
- Model trust boundaries: where does untrusted input enter the system?
- Identify assets worth protecting and their value.
- Prioritize mitigations by risk (probability × impact).
