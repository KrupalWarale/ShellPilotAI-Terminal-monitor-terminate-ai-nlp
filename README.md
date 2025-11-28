# ShellPilot AI

Windows terminal session manager with AI-enhanced command conversion, idle timeout termination, and comprehensive process monitoring with separate PID reporting.

<img width="1248" height="539" alt="{33EF8DDC-39FF-4378-87E8-E677B8142C25}" src="https://github.com/user-attachments/assets/e57d1ed1-b843-4c6d-a130-4b60165fc316" />


## Core Components

**main.py**: Tkinter GUI with resource dashboard, process library, and separate PID report generation  
**auto-terminator.ps1**: Interactive PowerShell session with idle timeout, AI commands, child process detection  
**inactive_process_monitor.py**: Multi-process monitor with activity detection and termination callbacks  
**ai_convert.py**: HuggingFace LLaMA-based natural language to PowerShell command converter

## Requirements & Setup

```bash
pip install psutil python-dotenv huggingface-hub
```

**Environment**: Windows 10/11, PowerShell 5.1+, Python 3.8+  
**AI Setup**: Set `HF_TOKEN` environment variable for HuggingFace API access

## Technical Implementation

### Process Architecture
- **Main Process**: PowerShell terminal (PID tracked in process library)
- **Child Processes**: Auto-detected via WMI, added to monitoring and library
- **Separate Reporting**: Each PID gets individual report with logs, metrics, lifecycle data

### Monitoring System
**Activity Detection**: CPU usage changes (>1%), memory deltas (>512KB), network connections  
**Grace Period**: 10s for new processes before inactivity checks  
**Protected Processes**: `conhost.exe` excluded from termination  
**Callbacks**: Status updates and termination notifications to main GUI

### File System Integration
```
%TEMP%\auto_terminator.log                    # Main session logs
%TEMP%\auto_terminator_<PID>.txt             # Timestamp tracking
%TEMP%\auto_terminator_monitored_children.txt # Child PID communication
```

### AI Command Processing
**Model**: meta-llama/Llama-3.1-8B-Instruct  
**Conversion**: Natural language → PowerShell commands  
**Execution Modes**: Manual confirmation or auto-execute  
**Command Examples**: "create file test.txt" → "type nul > test.txt"

## Usage Patterns

### GUI Mode
```bash
python main.py
```
**Features**: Resource dashboard, process library viewer, separate PID reports, log streaming

### Direct PowerShell
```powershell
./auto-terminator.ps1 -Timeout 30 -AutoExecute
```

### Built-in Commands
- `status`: System state and monitored processes
- `ai <text>`: Natural language command conversion
- `help`, `cls`, `exit`: Standard utilities

## Process Library Features

**Individual PID Tracking**:
- Start/end timestamps
- Status (Running/Inactive/Terminated)
- Resource metrics (CPU/Memory/Network)
- Complete log history
- Parent-child relationships

**Report Operations**:
- View individual PID reports
- Download single/all reports
- Delete specific PID entries
- Real-time status updates

## Advanced Configuration

**Timeout Settings**: Main session timeout, child process inactivity timeout  
**Monitoring Scope**: Automatic child detection, manual PID addition  
**AI Integration**: Token-based authentication, command validation  
**Resource Tracking**: CPU/Memory/Network/Battery metrics per PID

## Error Handling

**Process Termination**: Graceful → Force kill (5s timeout)  
**File Operations**: Automatic cleanup on session end  
**AI Failures**: Fallback to manual command entry  

**Permission Issues**: Execution policy bypass options
