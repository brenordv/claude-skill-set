# Security Best Practices

These guidelines apply to all security-related skills, covering application security, DevSecOps, and operational security.

## ⛔ Hard Rules: threat model first

These bind every security review, audit, finding, and proposed control, in every context: the main
conversation, subagents, the Stage 1 panel, branch-review. They beat "be thorough", a request for a
"full" review, the checklists in the security skill's knowledge files, and any lesson from the
vault. None of those admits a finding these rules leave out, and a lesson applies only where its
precondition holds in the model in front of you.

1. **State the model before the first finding.** Answer "What are we working on?", the first of the
   four questions in the [Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/), in a
   few lines at the top of the output:
   - what the system is and where it runs (one user's machine, a shared server, a multi-tenant
     service), with the assumptions the model leans on (authentication done upstream, TLS ending at
     a gateway);
   - the assets worth protecting;
   - the entry points and trust boundaries, where input or a caller with less trust crosses in;
   - the attackers considered, and what each one already holds (a network position, an account,
     privileges, access to the machine);
   - what is out of model, and why.

   When the repo documents its threat model (a `SECURITY.md`, a threat-model document, an ADR), read
   it, use it, and check it against the code in front of you. When it doesn't, write the model from
   the code and the ask, and say that you wrote it.
2. **Every finding names its path**: the attacker (one from the model), the entry point, the
   precondition (what the attacker must already hold, or what must already be true), the asset
   harmed, and where in the code or plan it happens. State the precondition in the terms
   [CVSS v4.0](https://www.first.org/cvss/v4.0/specification-document) uses: the privileges "an
   attacker must possess prior to successfully exploiting the vulnerability", the attack
   requirements (a race to win, an on-path position), the attack vector (network, adjacent, local,
   physical), and whether a user has to act. Those terms are vocabulary; no CVSS score is required.
   A concern that can't fill the path goes to the user as a question.
3. **A precondition that already grants the asset is out of model.** When the attack needs the
   attacker to already run code as the user, be logged in as them, hold administrator or root rights
   on the operating system (Windows, macOS, or Linux alike), or have changed the machine's binaries, environment, or configuration, and
   that position already gives them what the attack would gain, no boundary is crossed. Chromium
   puts such attacks outside its threat model "because there is no way for Chrome (or any
   application) to defend against a malicious user who has managed to log into your device as you,
   or who can run software with the privileges of your operating system user account"
   ([Chromium security FAQ](https://chromium.googlesource.com/chromium/src/+/main/docs/security/faq.md)).
   Microsoft services a report only when it violates "the goal or intent of a security boundary or
   a security feature"
   ([Windows servicing criteria](https://www.microsoft.com/en-us/msrc/windows-security-servicing-criteria)).
   Judge the precondition by what the attacker holds before the attack, never by what the attacked
   code runs as. An attacker who supplies only data (a file, a repository, an archive, a web page,
   a tool result, a request from a browser on the same machine) holds no position, and code
   execution that such data causes is in model. The rule covers the same account on the same
   machine: another local user, a service account, and an application's own admin role are
   separate positions. Read what a position grants from the platform's own documentation, and
   don't carry the answer over from another platform. On macOS, "System Integrity Protection
   restricts the root user account"
   ([Apple](https://support.apple.com/en-us/102149)), and the system works to "help prevent apps
   from accessing a user's personal information without permission"
   ([Apple Platform Security](https://support.apple.com/guide/security/protecting-app-access-to-user-data-secc01781f46/web)).
   On Ubuntu, AppArmor "restricts applications' capabilities and permissions with profiles that
   are set per-program"
   ([Ubuntu Server documentation](https://ubuntu.com/server/docs/how-to/security/apparmor/)). A
   Raspberry Pi OS install from before version 6.2 asks for no `sudo` password, and without one
   "any person or program that can run commands as your user can take full control of your
   Raspberry Pi"
   ([Raspberry Pi documentation](https://www.raspberrypi.com/documentation/computers/configuration.html#disable-sudo-password)).
   The same account can hold less than the user on one machine and as much as root on another.
   List an out-of-model concern once, under "Out of model", with its
   precondition. It never blocks and gets no control.
4. **A boundary the product promises is in the model.** Rule 3 doesn't excuse a product whose job
   is to hold against that position: a sandbox, a guardrail that confines an agent running as the
   user, a tool built to open untrusted files or repositories, a service that separates privileges.
   Name that boundary in the model. An attack across it is in model whatever position the attacker
   starts from.
5. **Rate likelihood and impact, coarsely.** Risk is "a function of: (i) the adverse impacts that
   would arise if the circumstance or event occurs; and (ii) the likelihood of occurrence"
   ([NIST glossary, from SP 800-30 Rev. 1](https://csrc.nist.gov/glossary/term/risk)). Rate each
   low, medium, or high: "It is not necessary to be over-precise in this estimate"
   ([OWASP Risk Rating Methodology](https://community.owasp.org/OWASP_Risk_Rating_Methodology)).
   Rate a chain of steps as one path, by its end result.
   - Likelihood is high when an attacker in the model can do it with what they already hold. It is
     medium when the attack also needs a condition that holds some of the time (a user's click on
     something unusual, a non-default setting). It is low when the attack needs a condition that
     rarely holds (a race won, an on-path position) or several such conditions at once. A condition
     the product's normal use satisfies (a logged-in user opening a page, a user opening a file
     with the tool built for it) doesn't count against likelihood.
   - Impact is high for code execution, a credential or secret, another user's or tenant's data, an
     authentication bypass or a gain in privilege, or data lost or corrupted beyond recovery. It is
     medium for disclosure or change limited to the attacker's own scope, or an outage a person has
     to recover. It is low for a nuisance that clears by itself (a process that hangs or restarts,
     an error shown).
6. **The rating decides what blocks.** This threshold is this skill set's own rule; the sources
   above give the rating and no cut-off. A finding blocks when it is in model and either impact is
   high with likelihood at least medium, or impact is medium with likelihood high. High impact with
   low likelihood doesn't block: put it to the user as a fix-or-accept decision. Every other
   in-model finding is a suggestion.
7. **Every in-model threat gets one of four responses**: mitigate, eliminate, transfer, or accept
   ([OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)).
   Accept is a real answer: "not all risks are worth fixing, and some loss is not only expected, but
   justifiable based upon the cost of fixing the issue" (OWASP Risk Rating Methodology). Accepting
   a blocking finding is the user's decision. Accepting a suggestion is yours; record it with the
   reason.
8. **A control pays for itself inside the model.** Before proposing a control, state what it costs:
   the code, a prompt or a step it adds for the user, a new way to fail. A second layer goes only on
   an in-model path. A way around one layer never blocks by itself while another control still
   holds the path: record it as a suggestion, since such a bypass "by itself does not pose a direct
   risk because an attacker must also have found a vulnerability that affects a security boundary"
   (Windows servicing criteria). It is a full finding when that layer is the only control on the
   path, or when the change under review removes or weakens it.
9. **The model changes on purpose, never to admit a finding.** A model you drafted is corrected
   when the code shows an entry point, asset, or boundary it missed: state the correction. A
   documented or user-confirmed model changes only through the user. Never add an attacker whose
   starting position already grants the asset. Revisit the model when a change adds an entry
   point, an asset, or a trust boundary: a threat model "should be maintained, updated and refined
   alongside the system" (OWASP Threat Modeling Cheat Sheet).

**What the model never excuses.** These have an in-model path in nearly every model, so "out of
model" needs a stated reason for each: a credential in source, a log, or a URL; injection through an
entry point that exists; untrusted data that steers code or an agent running with the user's
authority; a missing authorization check on an operation exposed to the attacker; a dependency with
a known vulnerability on a path the attacker reaches. Standing Hard Rules elsewhere
(`coding-general.md` ⛔ Hard Rule 11 on credentials, the secret-file rule in
`text-search-operations.md`) hold under every model.

**Size never gates this.** The model for a small change is three or four lines, and the trigger is
the topic: any security review, finding, or proposed control. A full data-flow diagram is for a
design that needs one.

**Self-check** before sending a security finding: can I name the attacker, the entry point, the
precondition, the asset, and the place in the code? Does the attacker hold that precondition
without already holding the asset? What are the two ratings, and what do they make it under rule 6?
If any answer is missing, the finding isn't ready.

---

## 1. Core Mindset

- **Threat model first**: no finding and no control before the model is stated (⛔ Hard Rules above).
- **Defense in depth**: layer controls on the paths the threat model names (⛔ Hard Rule 8).
- **Least privilege**: Grant only the minimum permissions needed for the task.
- **Zero trust**: authenticate and authorize every request that crosses a trust boundary in the
  model.
- **Assume breach**: design for containment across the model's boundaries. Limit blast radius.
- **Shift left**: integrate security into development as well as deployment.

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
- An embedded/local database is not encryption: to an adversary who can read the file (a backup, a
  synced folder, another account on the machine), a secret stored in SQLite or similar is plaintext
  unless the store or the value itself is actually encrypted.
- Attach credentials where the client is configured: a static key as a default header (or the SDK
  client's credential argument) from secret-store-backed configuration, an expiring or per-user
  token from an auth handler on the client's pipeline. Never pass one as a call parameter and never
  put one in a URL or query string, where it lands in web logs, browser history, and Referer
  headers even over HTTPS
  ([OWASP](https://community.owasp.org/vulnerabilities/Information_exposure_through_query_strings_in_url)).
  Full rule: `coding-general.md` ⛔ Hard Rule 11.
- A credential that reached a URL, a log, or source control is exposed. Rotating it is the
  owner's act, and the handoff tells them to ("explicitly rotate the affected keys", per
  [Azure Functions access keys](https://learn.microsoft.com/en-us/azure/azure-functions/function-keys-how-to)).
- Hold the narrowest credential: a function key for the one function a client calls, never a host
  or master key. A credential shipped in browser or native-client code is not a secret (same page:
  "don't distribute shared secrets in a public app").

---

## 3. Secure Development Lifecycle

### Static Analysis (SAST)

- Integrate SAST tools into CI/CD (Semgrep, SonarQube, Bandit, Roslyn analyzers).
- Fix in-model findings rated blocking before merge (⛔ Hard Rule 6); a scanner's severity is input
  to the rating.
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

The ⛔ Hard Rules at the top of this file are the binding part. The method behind them is the four
questions of the [Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/):

1. **What are we working on?** The model: the system, its assets, entry points, trust boundaries,
   and attackers.
2. **What can go wrong?** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial
   of Service, Elevation of Privilege) and the OWASP Top 10 are prompts for finding threats inside
   the model.
3. **What are we going to do about it?** One response per threat: mitigate, eliminate, transfer,
   accept.
4. **Did we do a good enough job?** Every in-model threat has a response, and the model still
   matches the system.

The Manifesto lists the habit these rules exist to stop among its anti-patterns: "Avoid
exaggerating attention on adversaries, assets, or techniques."
