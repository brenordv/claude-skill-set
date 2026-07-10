---
name: linux-shell-scripting
description: >-
  Production-ready shell script templates for Linux system administration.
  Backups, monitoring, user management, log analysis, and automation.
---

# Linux Production Shell Scripts

> **Shared Knowledge**: This skill builds on the guidelines in `brain/knowledge/devops-operations.md`. Always apply those principles alongside the specific guidance below.

## Purpose

Provide production-ready shell script templates for common Linux system administration tasks including backups, monitoring, user management, log analysis, and automation. These scripts serve as building blocks for security operations and penetration testing environments.

## Prerequisites

- Linux/Unix system (bash shell) with appropriate permissions for the task
- Required utilities installed (rsync, openssl, etc.)
- Basic bash scripting and Linux system administration knowledge

## Script Index

Each entry links to a companion file under `references/` holding the full, ready-to-use template(s). Open the relevant file when you need the script.

### Backups: `references/backup-scripts.md`
| Script | Purpose |
|--------|---------|
| Basic Directory Backup | Timestamped tar.gz of a source directory |
| Remote Server Backup | rsync files/directories to a remote server |
| Backup Rotation | Delete oldest backups beyond a retention count |
| Database Backup | mysqldump a database and gzip the output |

### Monitoring: `references/monitoring-scripts.md`
| Script | Purpose |
|--------|---------|
| CPU Usage Monitor | Alert when CPU usage exceeds a threshold |
| Disk Space Monitor | Alert when partition usage exceeds a threshold |
| System Health Check | Snapshot uptime, load, memory, disk, top processes to a file |

### User Management: `references/user-mgmt-scripts.md`
| Script | Purpose |
|--------|---------|
| User Account Creation | Create a user if it does not already exist |
| Password Expiry Checker | Report password expiry for bash-shell users |

### Security: `references/security-scripts.md`
| Script | Purpose |
|--------|---------|
| Password Generator | Generate a random password of a given length |
| File Encryption | Encrypt/decrypt a file with openssl AES-256-CBC |

### Log Analysis: `references/log-analysis-scripts.md`
| Script | Purpose |
|--------|---------|
| Error Log Extractor | Extract error/fail/critical lines from a log |
| Web Server Log Analyzer | Top IPs, URLs, and HTTP status distribution |

### Network: `references/network-scripts.md`
| Script | Purpose |
|--------|---------|
| Network Connectivity Checker | Ping a list of hosts and report reachability |
| Website Uptime Checker | curl a list of sites and log up/down status |

### Automation: `references/automation-scripts.md`
| Script | Purpose |
|--------|---------|
| Automated Package Installation | Install a package list, skipping installed ones |
| Task Scheduler (Cron Setup) | Append a job to crontab |
| Service Restart | Restart or start a systemd service |

### File Operations: `references/file-ops-scripts.md`
| Script | Purpose |
|--------|---------|
| Directory Synchronization | rsync mirror one directory to another |
| Data Cleanup | Remove files older than N days |
| Folder Size Checker | Show subdirectory sizes sorted, plus total |

### System Information: `references/sysinfo-scripts.md`
| Script | Purpose |
|--------|---------|
| System Info Collector | Collect host, CPU, memory, disk, network, users to a file |

### Git and Development: `references/git-scripts.md`
| Script | Purpose |
|--------|---------|
| Git Repository Updater | fetch + pull a list of local repositories |
| Remote Script Execution | Run a local script on a remote host via SSH |

## Cron Format

`Minute(0-59) Hour(0-23) Day(1-31) Month(1-12) Weekday(0-7, 0/7=Sun)`
