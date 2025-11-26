# Auto-Terminator Manager (Windows)

A small Windows utility that launches a monitored PowerShell terminal session which auto-terminates after a period of inactivity. It includes:

- A Python Tkinter GUI ([main.py](file:///c%3A/Users/Admin/Desktop/sp_cp/sp_cp/main.py)) to start/stop the monitored terminal and view logs with a resource dashboard (CPU, memory, open network connections, battery).
- A PowerShell script ([auto-terminator.ps1](file:///c%3A/Users/Admin/Desktop/sp_cp/sp_cp/auto-terminator.ps1)) that runs an interactive prompt and terminates itself after a configurable idle timeout, with a visible countdown and basic built-in commands.

## Requirements

- Windows 10/11
- PowerShell 5.1+ (preinstalled on Windows)
- Python 3.8+ for the GUI
- Python package: `psutil`

Install Python dependency:

```bash
pip install psutil
```

Note: Tkinter comes with the standard Windows Python installer. If you use a minimal distribution that lacks Tkinter, install the full Python installer from python.org.

## Project Structure

- [main.py](file:///c%3A/Users/Admin/Desktop/sp_cp/sp_cp/main.py): Tkinter GUI to launch/stop the PowerShell session, tail logs, and show process resource stats.
- [auto-terminator.ps1](file:///c%3A/Users/Admin/Desktop/sp_cp/sp_cp/auto-terminator.ps1): Interactive PowerShell session with idle-timeout auto-termination and helper commands.

Log and temp files (per session):
- Log file: `%TEMP%\auto_terminator.log`
- Timestamp file: `%TEMP%\auto_terminator_<PID>.txt` (cleaned up on exit)

## Usage

### Option A: Use the GUI (recommended)

1. Ensure dependencies are installed: `pip install psutil`.
2. Run the GUI:
   ```bash
   python main.py
   ```
3. In the window:
   - Set Idle Timeout (seconds) as desired.
   - Check "Auto-execute AI commands" if you want AI-generated commands to execute automatically without pressing Enter.
   - Click "Start Terminal" to open the monitored PowerShell session in a new console window.
   - The log output from the session will stream into the GUI.
   - Click "Stop Terminal" to terminate the session.

Resource Dashboard shows for the PowerShell process and its children:
- CPU usage (%)
- Memory usage (MB)
- Count of open network connections
- System battery status

### Option B: Run the PowerShell script directly

From PowerShell, in the project directory:

```powershell
# Start with default 5s timeout
./auto-terminator.ps1

# Start with custom timeout (e.g., 10 seconds)
./auto-terminator.ps1 -Timeout 10

# Start with auto-execution of AI commands
./auto-terminator.ps1 -AutoExecute

# Show help
./auto-terminator.ps1 -Help

# Install to %USERPROFILE%\.local\bin and create a batch wrapper on PATH (user scope)
./auto-terminator.ps1 -Install
# Afterwards, you can run it as:
auto-terminator -Timeout 10
```

Built-in commands inside the auto-terminator session:
- `status`: Show idle time, remaining time, and environment details
- `help`: Show available commands
- `cls`: Clear screen and show banner
- `exit`/`quit`: Exit the session
- `ai <text>`: Convert natural language to command using AI

During the last 3 seconds of inactivity, a countdown warning appears. Any key press or command resets the timer.

When using the AI command converter:
- With auto-execution disabled (default): You'll be prompted to press Enter to execute, 'e' to edit, or any other key to cancel
- With auto-execution enabled: AI-generated commands will execute automatically without user intervention

## Execution Policy Note (PowerShell)

If script execution is restricted, you may see a policy error. To allow local scripts for the current user, run in PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Alternatively, when invoking directly you can use a bypass for that session:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\auto-terminator.ps1 -Timeout 10
```

The GUI launches PowerShell with its own console window and passes the selected timeout.

## Troubleshooting

- If the GUI shows no logs, ensure the PowerShell window is open and `%TEMP%\auto_terminator.log` is writable.
- If resource stats remain `--`, the underlying process may have exited or access was denied; try starting a new session.
- If you get an execution policy error, apply the command in the section above and restart PowerShell.
- If `tkinter` is missing, install a standard Python build from `https://www.python.org/downloads/`.

## License

This project is provided as-is for educational purposes. Add a license of your choice if distributing.