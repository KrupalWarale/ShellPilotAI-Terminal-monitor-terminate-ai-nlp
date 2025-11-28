# =============================================================================
# AUTO-TERMINATOR FOR WINDOWS: Idle Terminal Session Manager
# =============================================================================
# Monitors terminal command activity and auto-terminates after timeout
# Author: AI Assistant
# Version: 2.0 (Windows - Fully Fixed)
# Compatible: PowerShell 5.1+, Windows 10/11
# =============================================================================

param(
    [switch]$Install,
    [switch]$Help,
    [switch]$AutoExecute,
    [int]$Timeout = 30
    # Removed ChildTimeout parameter since automatic killing is removed
)

# Force UTF-8 encoding for proper character display
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Configuration
$script:IDLE_TIMEOUT = $Timeout
# Removed $script:CHILD_TIMEOUT since automatic killing is removed
$script:AUTO_EXECUTE = $AutoExecute
$script:TIMESTAMP_FILE = Join-Path $env:TEMP "auto_terminator_$PID.txt"
$script:LOG_FILE = Join-Path $env:TEMP "auto_terminator.log"
$script:SESSION_ACTIVE = $true
$script:LAST_COMMAND_TIME = [int][double]::Parse((Get-Date -UFormat %s))

# AI Configuration
$script:AI_AVAILABLE = $false
$script:HF_TOKEN = $null

# Child process monitoring
$script:CHILD_PROCESSES = @{}
$script:MONITORED_CHILDREN_FILE = Join-Path $env:TEMP "auto_terminator_monitored_children.txt"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try {
        "[$timestamp] $Message" | Out-File -FilePath $script:LOG_FILE -Append -Encoding UTF8
    } catch {
        # Ignore logging errors
    }
}

function Write-ColoredText {
    param(
        [string]$Text,
        [string]$Color = 'White'
    )
    
    $colorMap = @{
        'Red' = 'Red'
        'Green' = 'Green'
        'Yellow' = 'Yellow'
        'Blue' = 'Blue'
        'Cyan' = 'Cyan'
        'Magenta' = 'Magenta'
        'White' = 'White'
        'Gray' = 'Gray'
        'DarkGray' = 'DarkGray'
    }
    
    $consoleColor = $colorMap[$Color]
    if (-not $consoleColor) {
        $consoleColor = 'White'
    }
    
    try {
        Write-Host $Text -ForegroundColor $consoleColor
    } catch {
        Write-Host $Text
    }
}

function Show-Banner {
    Write-ColoredText "+============================================================+" Blue
    Write-ColoredText "|                  AUTO-TERMINATOR v2.0                     |" Blue
    Write-ColoredText "|            Windows Terminal Session Manager               |" Blue
    Write-ColoredText "+============================================================+" Blue
    Write-ColoredText "Main Timer: $script:IDLE_TIMEOUT seconds of inactivity" Yellow
    Write-ColoredText "Countdown: Last 3 seconds before termination" Yellow
    Write-ColoredText "Log file: $script:LOG_FILE" Yellow
    Write-ColoredText "Enhanced PowerShell ready!" Green
    if ($script:AUTO_EXECUTE) {
        Write-ColoredText "Auto-execute AI commands: ENABLED" Green
    } else {
        Write-ColoredText "Auto-execute AI commands: DISABLED" Yellow
    }
    Write-Host ""
}

function Record-CommandTime {
    $script:LAST_COMMAND_TIME = [int][double]::Parse((Get-Date -UFormat %s))
    $script:LAST_COMMAND_TIME | Out-File -FilePath $script:TIMESTAMP_FILE -Encoding ASCII
    Write-Log "Command executed at timestamp: $script:LAST_COMMAND_TIME"
}

function Get-IdleTime {
    $currentTime = [int][double]::Parse((Get-Date -UFormat %s))
    return $currentTime - $script:LAST_COMMAND_TIME
}

function Get-RemainingTime {
    return $script:IDLE_TIMEOUT - (Get-IdleTime)
}

function Show-Status {
    Write-ColoredText "Auto-Terminator Status" Blue
    Write-ColoredText "======================" Blue
    
    $idleTime = Get-IdleTime
    $remainingTime = Get-RemainingTime
    
    Write-Host "Idle time: ${idleTime}s"
    
    if ($remainingTime -gt 0) {
        Write-ColoredText "Time remaining: ${remainingTime}s" Green
    } else {
        Write-ColoredText "Warning: Should have terminated!" Red
    }
    
    Write-Host "Main timeout threshold: $($script:IDLE_TIMEOUT)s"
    Write-Host "Session PID: $PID"
    Write-Host "PowerShell Version: $($PSVersionTable.PSVersion)"
    Write-Host "Auto-execute AI commands: $(if ($script:AUTO_EXECUTE) { 'Enabled' } else { 'Disabled' })"
    
    # Show child processes being monitored
    if ($script:CHILD_PROCESSES.Count -gt 0) {
        Write-Host "Monitored child processes: $($script:CHILD_PROCESSES.Count)"
        foreach ($childPid in $script:CHILD_PROCESSES.Keys) {
            $childInfo = $script:CHILD_PROCESSES[$childPid]
            $elapsed = [int]([double]::Parse((Get-Date -UFormat %s)) - $childInfo.LastActive)
            Write-Host "  PID $childPid - Inactive for ${elapsed}s"
        }
    } else {
        Write-Host "No child processes currently monitored"
    }
}

function Initialize-AI {
    # Try to load HF token from .env file
    $envFile = Join-Path (Get-Location) ".env"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile
        foreach ($line in $envContent) {
            if ($line -match '^HF_TOKEN\s*=\s*"?([^"]+)"?') {
                $script:HF_TOKEN = $matches[1]
                $script:AI_AVAILABLE = $true
                Write-Log "AI functionality enabled with HF token"
                break
            }
        }
    }
    
    if (-not $script:AI_AVAILABLE) {
        Write-Log "No HF token found - AI features disabled"
    }
}

function Convert-ToCommand {
    param([string]$NaturalText)
    
    if (-not $script:AI_AVAILABLE) {
        return "AI not available - check HF token in .env file"
    }
    
    try {
        # Use the dedicated AI converter
        $prompt = "Convert this natural language request to a Windows command line command. Only return the command, nothing else. Request: $NaturalText"
        
        # Call the dedicated AI converter
        $pythonResult = & python "ai_convert.py" $NaturalText 2>$null
        
        if ($pythonResult -and $pythonResult.Trim()) {
            $command = $pythonResult.Trim()
            # Clean up the response - extract just the command
            if ($command -match '(mkdir|dir|del|copy|type|cd|rmdir|move|ren|echo|cls)\s*.*') {
                return $matches[0]
            }
            # If no direct match, try to extract command from response
            $lines = $command -split '\n'
            foreach ($line in $lines) {
                $line = $line.Trim()
                if ($line -match '^(mkdir|dir|del|copy|type|cd|rmdir|move|ren|echo|cls)\s*.*') {
                    return $line
                }
            }
            return $command
        }
        
        # Fallback: Simple pattern matching for common commands
        return Get-FallbackCommand $NaturalText
    }
    catch {
        Write-Log "Python AI converter failed: $($_.Exception.Message)"
        # Fallback: Simple pattern matching for common commands
        return Get-FallbackCommand $NaturalText
    }
}

function Get-FallbackCommand {
    param([string]$Text)
    
    $Text = $Text.ToLower()
    
    # Handle common typos and variations
    $Text = $Text -replace "detlet|delet|deleet", "delete"
    $Text = $Text -replace "creat|mak", "make"
    $Text = $Text -replace "directry|dirctory", "directory"
    $Text = $Text -replace "fil", "file"
    
    # Simple pattern matching for common commands
    if ($Text -match "(make|create).*directory.*(\w+)" -or $Text -match "(make|create).*folder.*(\w+)") {
        return "mkdir $($matches[2])"
    }
    elseif ($Text -match "(delete|remove).*directory.*(\w+)" -or $Text -match "(delete|remove).*folder.*(\w+)") {
        return "rmdir /s $($matches[2])"
    }
    elseif ($Text -match "list.*file" -or $Text -match "show.*file" -or $Text -match "dir" -or $Text -match "ls") {
        return "dir"
    }
    elseif ($Text -match "(delete|remove).*file.*(\w+\.\w+)" -or $Text -match "(delete|remove).*(\w+\.\w+)") {
        return "del $($matches[2])"
    }
    elseif ($Text -match "copy.*(\w+\.\w+).*(\w+\.\w+)") {
        return "copy $($matches[1]) $($matches[2])"
    }
    elseif ($Text -match "(show|read).*content.*(\w+\.\w+)" -or $Text -match "(show|read).*file.*(\w+\.\w+)") {
        return "type $($matches[2])"
    }
    elseif ($Text -match "current.*directory" -or $Text -match "where.*am.*i" -or $Text -match "pwd") {
        return "cd"
    }
    else {
        return "Error: Could not convert '$Text' to command. Try: 'make directory name', 'list files', 'delete directory name'"
    }
}

function Show-Help {
    Write-ColoredText "Auto-Terminator Commands:" Blue
    Write-Host "  status    - Show current session status"
    Write-Host "  help      - Show this help message"
    Write-Host "  cls       - Clear screen"
    Write-Host "  exit      - Manually exit the session"
    Write-Host "  ai <text> - Convert natural language to command using AI"
    Write-Host ""
    Write-ColoredText "AI Examples:" Yellow
    Write-Host "  ai make directory hello"
    Write-Host "  ai list all files"
    Write-Host "  ai delete file test.txt"
    Write-Host ""
    Write-ColoredText "Regular PowerShell commands work normally and reset the timer" Yellow
}

function Start-ChildProcessMonitoring {
    # This function would be called when child processes are launched
    # For now, we'll monitor child processes in the main loop
    Write-Log "Child process monitoring started (automatic termination removed)"
    
    # Create or clear the monitored children file
    try {
        "" | Out-File -FilePath $script:MONITORED_CHILDREN_FILE -Encoding ASCII -Force
    } catch {
        Write-Log "Warning: Could not create monitored children file: $($_.Exception.Message)"
    }
}

function Notify-MonitoredChild {
    param([int]$ChildPid)
    
    # Notify the Python monitor about this child process
    try {
        "$ChildPid" | Out-File -FilePath $script:MONITORED_CHILDREN_FILE -Append -Encoding ASCII
        Write-Log "Notified Python monitor about child process: $ChildPid"
    } catch {
        Write-Log ("Warning: Could not notify Python monitor about child process {0}: {1}" -f $ChildPid, $_.Exception.Message)
    }
}

function Check-ChildProcesses {
    # Get all child processes of this PowerShell session
    $currentChildren = Get-WmiObject Win32_Process -Filter "ParentProcessId=$PID"
    
    # Track current child PIDs
    $currentChildPids = @()
    
    $terminatedPids = @()
    
    foreach ($child in $currentChildren) {
        $childPid = $child.ProcessId
        $currentChildPids += $childPid
        
        # Check if this is a new child process
        if (-not $script:CHILD_PROCESSES.ContainsKey($childPid)) {
            Write-Log "Monitoring new child process: $($child.Name) (PID: $childPid)"
            $script:CHILD_PROCESSES[$childPid] = @{
                Name = $child.Name
                StartTime = [double]::Parse((Get-Date -UFormat %s))
                LastActive = [double]::Parse((Get-Date -UFormat %s))
                LastCPU = 0
                LastMemory = 0
            }
            
            # Notify Python monitor about this new child process
            Notify-MonitoredChild $childPid
        } else {
            # Check if existing child process is active
            try {
                $childProcess = Get-Process -Id $childPid -ErrorAction Stop
                $cpuUsage = $childProcess.CPU
                $memoryUsage = $childProcess.WorkingSet64
                
                # Check for resource activity
                $hasCPUActivity = $cpuUsage -gt $script:CHILD_PROCESSES[$childPid].LastCPU
                $hasMemoryActivity = $memoryUsage -gt $script:CHILD_PROCESSES[$childPid].LastMemory
                
                # Update resource usage
                $script:CHILD_PROCESSES[$childPid].LastCPU = $cpuUsage
                $script:CHILD_PROCESSES[$childPid].LastMemory = $memoryUsage
                
                # Consider active if:
                # 1. Has CPU activity
                # 2. Has memory activity
                # 3. Currently consuming CPU (> 0)
                if ($hasCPUActivity -or $hasMemoryActivity -or $cpuUsage -gt 0) {
                    $script:CHILD_PROCESSES[$childPid].LastActive = [double]::Parse((Get-Date -UFormat %s))
                }
            } catch {
                # Process may have terminated, collect for removal
                Write-Log "Child process terminated: $($script:CHILD_PROCESSES[$childPid].Name) (PID: $childPid)"
                $terminatedPids += $childPid
            }
        }
    }
    
    # Remove terminated processes
    foreach ($terminatedPid in $terminatedPids) {
        $script:CHILD_PROCESSES.Remove($terminatedPid)
    }
    
    # Remove tracking for processes that no longer exist
    $pidsToRemove = @()
    foreach ($trackedPid in $script:CHILD_PROCESSES.Keys) {
        if ($currentChildPids -notcontains $trackedPid) {
            $pidsToRemove += $trackedPid
        }
    }
    
    # Now safely remove the PIDs
    foreach ($pidToRemove in $pidsToRemove) {
        Write-Log "Stopped monitoring child process: $($script:CHILD_PROCESSES[$pidToRemove].Name) (PID: $pidToRemove)"
        $script:CHILD_PROCESSES.Remove($pidToRemove)
    }
    
    # Child process monitoring is kept for dashboard purposes but automatic killing is removed
}

function Execute-Command {
    param(
        [string]$CommandLine
    )
    
    if ([string]::IsNullOrWhiteSpace($CommandLine)) {
        return
    }
    
    # Parse command and arguments
    $parts = $CommandLine.Trim() -split '\s+', 2
    $command = $parts[0]
    $args = if ($parts.Length -gt 1) { $parts[1] } else { "" }
    
    # Handle built-in auto-terminator commands
    switch ($command.ToLower()) {
        "status" {
            Show-Status
            return
        }
        "help" {
            Show-Help
            return
        }
        "cls" {
            Clear-Host
            Show-Banner
            return
        }
        "ai" {
            if ([string]::IsNullOrWhiteSpace($args)) {
                Write-ColoredText "Usage: ai <natural language request>" Yellow
                Write-ColoredText "Example: ai make directory hello" Yellow
                return
            }
            
            Write-ColoredText "Converting: $args" Cyan
            Write-Log "AI Request: $args"
            $convertedCommand = Convert-ToCommand $args
            
            if ($convertedCommand.StartsWith("Error:")) {
                Write-ColoredText $convertedCommand Red
                Write-Log "AI Error: $convertedCommand"
                return
            }
            
            Write-ColoredText "Generated command: $convertedCommand" Green
            Write-Log "AI Generated Command: $convertedCommand"
            
            # Check if auto-execute is enabled
            if ($script:AUTO_EXECUTE) {
                Write-ColoredText "Auto-executing command..." Yellow
                Write-Log "Auto-executing command: $convertedCommand"
                try {
                    Invoke-Expression $convertedCommand
                    Write-Log "Command executed successfully: $convertedCommand"
                } catch {
                    Write-ColoredText "Error executing command: $_" Red
                    Write-Log "Error executing command '$convertedCommand': $_"
                }
                return
            }
            
            Write-Host "Press Enter to execute, 'e' to edit, or any other key to cancel: " -NoNewline -ForegroundColor Yellow
            
            $response = $null
            while ($null -eq $response) {
                if ([Console]::KeyAvailable) {
                    $key = [Console]::ReadKey($true)
                    $response = $key.KeyChar
                    
                    if ([int]$response -eq 13) {  # Enter key
                        Write-Host "Enter"
                        Write-ColoredText "Executing: $convertedCommand" Green
                        Write-Log "User confirmed execution of command: $convertedCommand"
                        try {
                            Invoke-Expression $convertedCommand
                            Write-Log "Command executed successfully: $convertedCommand"
                        } catch {
                            Write-ColoredText "Error executing command: $_" Red
                            Write-Log "Error executing command '$convertedCommand': $_"
                        }
                        break
                    }
                    elseif ($response.ToString().ToLower() -eq "e") {
                        Write-Host "e"
                        Write-Host "Edit command: " -NoNewline -ForegroundColor Yellow
                        Write-Host $convertedCommand
                        Write-Host "Enter edited command: " -NoNewline -ForegroundColor Yellow
                        $editedCommand = Read-Host
                        if (-not [string]::IsNullOrWhiteSpace($editedCommand)) {
                            Write-ColoredText "Executing: $editedCommand" Green
                            Write-Log "User edited and executing command: $editedCommand"
                            try {
                                Invoke-Expression $editedCommand
                                Write-Log "Command executed successfully: $editedCommand"
                            } catch {
                                Write-ColoredText "Error executing command: $_" Red
                                Write-Log "Error executing command '$editedCommand': $_"
                            }
                        }
                        break
                    }
                    else {
                        Write-Host $response
                        Write-ColoredText "Command cancelled" Yellow
                        Write-Log "User cancelled command execution: $convertedCommand"
                        break
                    }
                }
                Start-Sleep -Milliseconds 50
            }
            return
        }
        "exit" {
            Write-ColoredText "Goodbye!" Yellow
            $script:SESSION_ACTIVE = $false
            return
        }
        "quit" {
            Write-ColoredText "Goodbye!" Yellow
            $script:SESSION_ACTIVE = $false
            return
        }
    }
    
    # Execute regular PowerShell commands
    try {
        if ($args) {
            $fullCommand = "$command $args"
        } else {
            $fullCommand = $command
        }
        
        Write-Log "Executing PowerShell command: $fullCommand"
        # Use Invoke-Expression for full PowerShell compatibility
        Invoke-Expression $fullCommand
        Write-Log "PowerShell command executed successfully: $fullCommand"
    }
    catch {
        Write-ColoredText "Error: $_" Red
        Write-Log "Error executing PowerShell command '$fullCommand': $_"
    }
}

function Show-CountdownWarning {
    param([int]$SecondsRemaining)
    
    $message = ">>> AUTO-TERMINATION WARNING: $SecondsRemaining seconds remaining! Press any key or type command..."
    
    switch ($SecondsRemaining) {
        3 { Write-Host $message -ForegroundColor Yellow -BackgroundColor DarkRed }
        2 { Write-Host $message -ForegroundColor Yellow -BackgroundColor DarkRed }
        1 { Write-Host $message -ForegroundColor White -BackgroundColor Red }
        default { Write-Host $message -ForegroundColor Yellow -BackgroundColor DarkRed }
    }
}

function Test-KeyAvailable {
    try {
        if ([Console]::KeyAvailable) {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Read-KeyIfAvailable {
    try {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            return $key.KeyChar
        }
        return $null
    } catch {
        return $null
    }
}

# =============================================================================
# MAIN EXECUTION LOOP
# =============================================================================

function Start-AutoTerminator {
    # Initialize
    Initialize-AI
    Show-Banner
    Start-ChildProcessMonitoring
    
    if ($script:AI_AVAILABLE) {
        Write-ColoredText "AI Command Converter: ENABLED" Green
        Write-ColoredText "Type 'ai <request>' to convert natural language to commands" Cyan
    } else {
        Write-ColoredText "AI Command Converter: DISABLED (no HF token)" Yellow
    }
    Write-Host ""
    
    Write-Log "Auto-terminator session started (PID: $PID)"
    Write-Log "Main timeout: $($script:IDLE_TIMEOUT)s"
    
    # Record initial timestamp
    Record-CommandTime
    
    $inputBuffer = ""
    $promptShown = $false
    $lastCountdownSecond = -1
    $lastChildCheck = [double]::Parse((Get-Date -UFormat %s))
    
    try {
        while ($script:SESSION_ACTIVE) {
            $remainingTime = Get-RemainingTime
            
            # Check if we should terminate
            if ($remainingTime -le 0) {
                Write-Host ""
                Write-ColoredText "Session terminated due to inactivity timeout!" Red
                Write-ColoredText "Total idle time exceeded: $script:IDLE_TIMEOUT seconds" Yellow
                Write-ColoredText "Terminal window will close in 2 seconds..." Yellow
                Start-Sleep -Seconds 2
                
                # Force close the terminal window
                try {
                    # Method 1: Use taskkill to force close this process
                    $currentPID = $PID
                    & taskkill /PID $currentPID /F
                } catch {
                    try {
                        # Method 2: Stop the process directly
                        Stop-Process -Id $PID -Force
                    } catch {
                        # Method 3: Just exit
                        [Environment]::Exit(0)
                    }
                }
            }
            
            # Check child processes every 2 seconds
            $currentTime = [double]::Parse((Get-Date -UFormat %s))
            if (($currentTime - $lastChildCheck) -gt 2) {
                Check-ChildProcesses
                $lastChildCheck = $currentTime
            }
            
            # Show countdown warning in last 3 seconds (only once per second)
            if ($remainingTime -le 3 -and $remainingTime -gt 0) {
                if ($remainingTime -ne $lastCountdownSecond) {
                    if ($lastCountdownSecond -eq -1) {
                        Write-Host ""  # Add space before first countdown
                    }
                    Show-CountdownWarning $remainingTime
                    $lastCountdownSecond = $remainingTime
                    $promptShown = $false  # Reset prompt flag during countdown
                }
            } else {
                $lastCountdownSecond = -1
            }
            
            # Show prompt only once when not in countdown mode and no input buffer
            if ($remainingTime -gt 3 -and -not $promptShown -and [string]::IsNullOrEmpty($inputBuffer)) {
                try {
                    $currentPath = (Get-Location).Path -replace [regex]::Escape($env:USERPROFILE), "~"
                    Write-Host "auto-term:" -ForegroundColor Green -NoNewline
                    Write-Host $currentPath -ForegroundColor Blue -NoNewline
                    Write-Host "PS> " -NoNewline
                    $promptShown = $true
                } catch {
                    Write-Host "auto-term> " -NoNewline
                    $promptShown = $true
                }
            }
            
            # If we have an input buffer but no prompt shown, we need to show the prompt
            if (-not [string]::IsNullOrEmpty($inputBuffer) -and -not $promptShown) {
                try {
                    $currentPath = (Get-Location).Path -replace [regex]::Escape($env:USERPROFILE), "~"
                    Write-Host "auto-term:" -ForegroundColor Green -NoNewline
                    Write-Host $currentPath -ForegroundColor Blue -NoNewline
                    Write-Host "PS> " -NoNewline
                    # Don't set $promptShown = $true here because we want to be able to show it again
                    # This fixes the issue where the prompt disappears after backspace
                } catch {
                    Write-Host "auto-term> " -NoNewline
                }
            }
            
            # Check for keyboard input
            $keyPressed = Read-KeyIfAvailable
            
            if ($null -ne $keyPressed) {
                # Reset timer and counters on any key press
                Record-CommandTime
                $lastCountdownSecond = -1
                
                # Handle special keys
                if ([int]$keyPressed -eq 13) {  # Enter key
                    Write-Host ""  # New line
                    
                    if (-not [string]::IsNullOrWhiteSpace($inputBuffer)) {
                        Write-Log "User entered command: $inputBuffer"
                        Execute-Command $inputBuffer
                    }
                    $inputBuffer = ""
                    $promptShown = $false  # Reset prompt for next command
                } elseif ([int]$keyPressed -eq 8) {  # Backspace
                    if ($inputBuffer.Length -gt 0) {
                        $inputBuffer = $inputBuffer.Substring(0, $inputBuffer.Length - 1)
                        Write-Host "`b `b" -NoNewline  # Erase character
                    }
                    # Don't reset $promptShown for backspace, keep the prompt visible
                } elseif ([int]$keyPressed -eq 3) {  # Ctrl+C
                    Write-Host "^C"
                    $inputBuffer = ""
                    $promptShown = $false
                } elseif ([int]$keyPressed -eq 27) {  # Escape key
                    # Clear current input
                    for ($i = 0; $i -lt $inputBuffer.Length; $i++) {
                        Write-Host "`b `b" -NoNewline
                    }
                    $inputBuffer = ""
                    $promptShown = $false
                } elseif ([int]$keyPressed -ge 32 -and [int]$keyPressed -le 126) {  # Printable ASCII characters only
                    $inputBuffer += $keyPressed
                    Write-Host $keyPressed -NoNewline
                    # Don't reset $promptShown for typing, keep the prompt visible
                }
                # Ignore arrow keys and other special keys (they cause issues)
            }
            
            # Small delay to prevent high CPU usage
            Start-Sleep -Milliseconds 100
        }
    }
    finally {
        # Cleanup
        Write-Log "Auto-terminator session ended (PID: $PID)"
        Remove-Item $script:TIMESTAMP_FILE -Force -ErrorAction SilentlyContinue
        Remove-Item $script:MONITORED_CHILDREN_FILE -Force -ErrorAction SilentlyContinue
        Write-ColoredText "`nAuto-terminator session ended" Red
    }
}

# =============================================================================
# INSTALLATION FUNCTIONS
# =============================================================================

function Install-AutoTerminator {
    $installDir = "$env:USERPROFILE\.local\bin"
    $scriptName = "auto-terminator.ps1"
    $scriptPath = Join-Path $installDir $scriptName
    
    Write-ColoredText "Installing Auto-Terminator for Windows..." Blue
    
    # Create directory if it doesn't exist
    if (-not (Test-Path $installDir)) {
        New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    }
    
    # Copy script
    Copy-Item $PSCommandPath $scriptPath -Force
    
    # Create batch wrapper for easy execution
    $batchPath = Join-Path $installDir "auto-terminator.bat"
    @"
@echo off
powershell.exe -ExecutionPolicy Bypass -File "$scriptPath" %*
"@ | Out-File -FilePath $batchPath -Encoding ASCII
    
    # Add to PATH if not already there
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -notlike "*$installDir*") {
        $newPath = "$currentPath;$installDir"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-ColoredText "Added $installDir to user PATH" Yellow
        Write-ColoredText "Restart your terminal to use the new PATH" Yellow
    }
    
    Write-ColoredText "Installed to: $scriptPath" Green
    Write-ColoredText "Batch wrapper: $batchPath" Green
    Write-ColoredText "Run 'auto-terminator' to start monitoring" Green
}

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if ($Install) {
    Install-AutoTerminator
    exit 0
}

if ($Help) {
    Write-Host "Auto-Terminator for Windows: Idle Terminal Session Manager"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\auto-terminator.ps1                    - Start monitored terminal session"
    Write-Host "  .\auto-terminator.ps1 -Install           - Install to user profile"
    Write-Host "  .\auto-terminator.ps1 -Help              - Show this help"
    Write-Host "  .\auto-terminator.ps1 -Timeout 10        - Set custom timeout (seconds)"
    Write-Host "  .\auto-terminator.ps1 -AutoExecute       - Enable auto-execution of AI commands"
    Write-Host ""
    Write-Host "Features:"
    Write-Host "  - Automatically terminates after specified seconds of inactivity"
    Write-Host "  - Visual countdown in last 3 seconds"
    Write-Host "  - Full PowerShell command compatibility"
    Write-Host "  - Real-time activity monitoring"
    Write-Host "  - Built-in commands: status, help, exit, cls"
    Write-Host "  - AI command conversion with optional auto-execution"
    Write-Host "  - Child process monitoring for dashboard (automatic termination removed)"
    exit 0
}

# Check PowerShell execution policy
try {
    $executionPolicy = Get-ExecutionPolicy
    if ($executionPolicy -eq "Restricted") {
        Write-ColoredText "PowerShell execution policy is Restricted" Yellow
        Write-ColoredText "Run this command as Administrator to allow script execution:" Yellow
        Write-ColoredText "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" Cyan
        exit 1
    }
} catch {
    Write-Log "Error checking execution policy: $($_.Exception.Message)"
}

# Default: start the auto-terminator
Write-Log "Starting Auto-Terminator with timeout: $script:IDLE_TIMEOUT seconds"
if ($script:AUTO_EXECUTE) {
    Write-Log "Auto-execution of AI commands: ENABLED"
} else {
    Write-Log "Auto-execution of AI commands: DISABLED"
}
Start-AutoTerminator