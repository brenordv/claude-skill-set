## OS diagnostics (Windows)

There is a system-diagnostics MCP server registered as `os-doctor`. Use its structured tools for all
local machine inspection instead of shelling out to PowerShell/WMI/`Get-*` cmdlets for anything they cover.

### Use these instead of shell probing

| Instead of                                                    | Use                                            |
|---------------------------------------------------------------|------------------------------------------------|
| `Get-ComputerInfo`, `systeminfo`                              | `get_system_info`                              |
| `Get-Service`, `sc query`                                     | `get_service_status`                           |
| `Get-Process \| Sort CPU`, Task Manager                       | `list_top_processes`                           |
| `Get-WinEvent`, `Get-EventLog`                                | `query_system_log` (list sources first)        |
| GPU/driver checks (`dxdiag`, vendor tools)                    | `get_gpu_info`, `get_directx_info`             |
| temps / fan / voltage sensors                                 | `get_sensor_data`, `start_sensor_monitoring`   |
| uptime / boot times                                           | `get_boot_history`                             |

### Rules

- Call `get_capabilities` first when unsure what this machine exposes; not every sensor/source exists on
  every box. Call `list_log_sources` before `query_system_log`.
- Reach for `os-doctor` whenever a task involves diagnosing this machine (performance, a failing service,
  a hardware/thermal question, driver/GPU issues, or "why is X slow/broken") before proposing manual
  commands the user has to run.
- For continuous readings use `start_sensor_monitoring` / `stop_sensor_monitoring` rather than polling
  `get_sensor_data` in a loop.
- These tools are read-only diagnostics. They don't change system state; pair them with explicit,
  user-approved commands when a fix is actually needed.
