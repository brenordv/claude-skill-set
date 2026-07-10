---
name: linux-troubleshooting
description: >-
  Linux system troubleshooting workflow for diagnosing and resolving
  system issues, performance problems, and service failures.
---

# Linux Troubleshooting Workflow

> **Shared Knowledge**: This skill builds on the guidelines in `brain/knowledge/devops-operations.md`. Always apply those principles alongside the specific guidance below.

## Overview

Specialized workflow for diagnosing and resolving Linux system issues including performance problems, service failures, network issues, and resource constraints.

## When to Use This Workflow

Use this workflow when:
- Diagnosing system performance issues
- Troubleshooting service failures
- Investigating network problems
- Resolving disk space issues
- Debugging application errors

## Workflow Phases

### Phase 1: Initial Assessment

#### Actions
1. Check system uptime
2. Review recent changes
3. Identify symptoms
4. Gather error messages
5. Document findings

#### Commands
```bash
uptime
hostnamectl
cat /etc/os-release
dmesg | tail -50
```

### Phase 2: Resource Analysis

#### Actions
1. Check CPU usage
2. Analyze memory
3. Review disk space
4. Monitor I/O
5. Check network

#### Commands
```bash
top -bn1 | head -20
free -h
df -h
iostat -x 1 5
```

### Phase 3: Process Investigation

#### Actions
1. List running processes
2. Identify resource hogs
3. Check process status
4. Review process trees
5. Analyze strace output

#### Commands
```bash
ps aux --sort=-%cpu | head -10
pstree -p
lsof -p PID
strace -p PID
```

### Phase 4: Log Analysis

#### Actions
1. Check system logs
2. Review application logs
3. Search for errors
4. Analyze log patterns
5. Correlate events

#### Commands
```bash
journalctl -xe
tail -f /var/log/syslog
grep -i error /var/log/*
```

### Phase 5: Network Diagnostics

#### Actions
1. Check network interfaces
2. Test connectivity
3. Analyze connections
4. Review firewall rules
5. Check DNS resolution

#### Commands
```bash
ip addr show
ss -tulpn
curl -v http://target
dig domain
```

### Phase 6: Service Troubleshooting

#### Actions
1. Check service status
2. Review service logs
3. Test service restart
4. Verify dependencies
5. Check configuration

#### Commands
```bash
systemctl status service
journalctl -u service -f
systemctl restart service
```

### Phase 7: Resolution

Follow the gather -> hypothesize -> test -> verify -> document methodology in `brain/knowledge/devops-operations.md` §3 to implement the fix, verify the resolution, monitor stability, and document root cause plus a prevention plan.

## Troubleshooting Checklist

- [ ] System information gathered
- [ ] Resources analyzed
- [ ] Logs reviewed
- [ ] Network tested
- [ ] Services verified
- [ ] Root cause identified
- [ ] Issue resolved / fix verified
- [ ] Monitoring in place
- [ ] Documentation created
