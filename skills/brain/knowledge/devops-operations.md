# DevOps & Operations Best Practices

These guidelines apply to infrastructure, scripting, monitoring, and operational skills.

---

## 1. Scripting Standards

- **Always use a shebang**: `#!/bin/bash` or appropriate interpreter.
- **Quote variables**: Prevent word splitting and glob expansion.
- **Use absolute paths**: Avoid errors from unexpected working directories.
- **Validate inputs**: Check arguments exist and are valid before proceeding.
- **Fail fast**: Use `set -euo pipefail` for strict error handling in bash.
- **Idempotency**: Scripts should be safe to run multiple times without side effects.
- **Test in non-production first**: Always validate in a safe environment.

---

## 2. Monitoring & Observability

### Three Pillars

| Pillar | Purpose | Key Tools |
|--------|---------|-----------|
| **Logs** | Structured event records | ELK, Loki, CloudWatch |
| **Metrics** | Numeric measurements over time | Prometheus, Grafana, Datadog |
| **Traces** | Request flow across services | Jaeger, Tempo, X-Ray |

### SLI/SLO Discipline

- Define Service Level Indicators (measurable signals of user experience).
- Set Service Level Objectives (targets for those indicators).
- Alert on SLO burn rate, not individual errors.
- Maintain error budgets; invest in reliability only when budgets are depleted.

### Alerting Principles

- Alert on symptoms (user-facing impact), not causes.
- Every alert must be actionable; if there's nothing to do, remove it.
- Reduce noise: group, deduplicate, route to the right team.
- Include runbook links in alert notifications.

---

## 3. Troubleshooting Methodology

1. **Gather information**: System state, recent changes, error messages.
2. **Form hypothesis**: Based on evidence, not assumptions.
3. **Test hypothesis**: One change at a time.
4. **Verify resolution**: Confirm the fix, monitor stability.
5. **Document**: Root cause, fix, prevention plan.

---

## 4. Automation Principles

- **Automate repetitive tasks**: Backups, deployments, monitoring checks.
- **Version control scripts**: Treat infrastructure-as-code like application code.
- **Log execution**: Track what ran, when, and the result.
- **Graceful degradation**: Scripts should handle partial failures without leaving systems in broken states.
- **Secrets handling**: Never store credentials in scripts; use secret managers.

---

## 5. Reliability

- **Redundancy**: Eliminate single points of failure.
- **Backups**: Automate, test restores regularly.
- **Change management**: Track what changed, when, and by whom.
- **Rollback plans**: Always have a way to revert changes.
- **Capacity planning**: Monitor trends, plan for growth.

---

## 6. Security in Operations

- **Principle of least privilege**: Minimal permissions for scripts and services.
- **Audit trails**: Log administrative actions.
- **Patch management**: Keep systems updated; automate where possible.
- **Network segmentation**: Isolate sensitive systems.
- **Secure communication**: SSH keys over passwords, TLS for all traffic.
