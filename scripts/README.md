# Scripts Overview

| Script | Purpose |
| --- | --- |
| `free_port.ps1` | Lists and optionally terminates any process bound to a given port. Use `-Force` to kill owners automatically. |
| `start_backend_with_logging.ps1` | Launches `dcsm_backend.py`, sets `API_PORT`, and tees output into timestamped log files under `logs/`. |
| `orchestrate_dev.ps1` | One-command helper that clears the backend port, launches the backend with logging, optionally tails the newest backend log, starts the frontend dev server (with optional log tee), and opens the browser. |
| `reset_and_launch_dev.ps1` | Wraps port cleanup (frontend + backend), orchestrator launch, and optional frontend log teeing into a single command so you no longer have to paste large inline scripts. |

## orchestrate_dev.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\orchestrate_dev.ps1 `
	-BackendPort 8100 `
	-FrontendPort 3002 `
	-TailBackendLog `
	-FrontendLogPath .\logs\frontend-dev.log
```

Each major task runs in its own PowerShell window so you can stop/start pieces independently while keeping the parent shell free for git or tooling.

## reset_and_launch_dev.ps1
```
powershell -ExecutionPolicy Bypass -File .\scripts\reset_and_launch_dev.ps1 `
    -FrontendPort 3002 `
    -BackendPort 8100 `
    -TailBackendLog `
    -FrontendLogPath .\logs\frontend-dev.log
```
- Uses `free_port.ps1` to force-close anything on both ports before launching.
- Accepts the same `-SkipFrontend`, `-SkipBrowser`, and `-TailBackendLog` switches as the orchestrator and forwards them automatically.
- `-ProjectRoot` defaults to `F:\DrumTracKAI_v1.1.17`, but you can override it if you move the repo.
- Logs are optional—omit `-FrontendLogPath` to leave the frontend console unteed.
