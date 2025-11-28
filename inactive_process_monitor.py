#!/usr/bin/env python3
"""
Inactive Process Monitor
Monitors processes for inactivity and terminates them after a specified timeout.
"""

import psutil
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Callable
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.environ.get('TEMP', '.'), 'inactive_process_monitor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InactiveProcessMonitor:
    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize the inactive process monitor.
        
        Args:
            timeout_seconds: Time in seconds after which an inactive process should be terminated
        """
        self.timeout_seconds = timeout_seconds
        self.monitored_processes: Dict[int, Dict[str, Any]] = {}
        self.monitoring = False
        self.monitor_thread = None
        # File where PowerShell will write PIDs of child processes to monitor
        self.monitored_children_file = os.path.join(os.environ.get('TEMP', '.'), 'auto_terminator_monitored_children.txt')
        # Callback for process status updates
        self.process_status_callback: Callable = None
        # Callback for process termination
        self.process_termination_callback: Callable = None
        # Terminal PID to exclude from termination
        self.terminal_pid = None
        # Hardcoded processes to never terminate
        self.protected_processes = ['conhost.exe']
        logger.info(f"Inactive Process Monitor initialized with timeout: {timeout_seconds}s")
    
    def set_terminal_pid(self, pid: int):
        """
        Set the terminal PID to exclude from termination.
        
        Args:
            pid: PID of the terminal process to exclude
        """
        self.terminal_pid = pid
        logger.info(f"Terminal PID set to {pid}, will be excluded from termination")
    
    def set_process_status_callback(self, callback: Callable):
        """
        Set a callback function to receive process status updates.
        
        Args:
            callback: Function to call when process status changes
        """
        self.process_status_callback = callback
    
    def set_process_termination_callback(self, callback: Callable):
        """
        Set a callback function to receive process termination notifications.
        
        Args:
            callback: Function to call when a process is terminated
        """
        self.process_termination_callback = callback
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Process monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("Process monitoring stopped")
    
    def is_protected_process(self, process_name: str) -> bool:
        """
        Check if a process is protected and should never be terminated.
        
        Args:
            process_name: Name of the process to check
            
        Returns:
            Boolean indicating if the process is protected
        """
        return process_name.lower() in [p.lower() for p in self.protected_processes]
    
    def add_process(self, pid: int):
        """
        Add a process to be monitored for inactivity.
        
        Args:
            pid: Process ID to monitor
        """
        # Don't monitor the terminal PID itself
        if self.terminal_pid and pid == self.terminal_pid:
            logger.info(f"Skipping terminal PID {pid} from monitoring")
            return
            
        try:
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Don't monitor protected processes
            if self.is_protected_process(process_name):
                logger.info(f"Skipping protected process {process_name} (PID: {pid}) from monitoring")
                return
                
            # Give new processes a grace period by setting their last activity time to now + grace period
            grace_period_seconds = 10  # 10 second grace period for new processes (reduced)
            self.monitored_processes[pid] = {
                'process': process,
                'last_activity_time': datetime.now(),
                'start_time': datetime.now(),
                'last_memory_info': process.memory_info(),
                'last_network_io': self._get_network_io(process),
                'window_focus_check_enabled': self._can_check_window_focus(process),
                'name': process_name,
                'grace_period_seconds': grace_period_seconds,
                'checks_count': 0
            }
            logger.info(f"Added process {pid} ({process_name}) to monitoring. Total monitored: {len(self.monitored_processes)}")
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} does not exist")
        except Exception as e:
            logger.error(f"Error adding process {pid} to monitoring: {e}")
    
    def remove_process(self, pid: int):
        """
        Remove a process from monitoring.
        
        Args:
            pid: Process ID to remove from monitoring
        """
        # Don't remove the terminal PID
        if self.terminal_pid and pid == self.terminal_pid:
            return
            
        if pid in self.monitored_processes:
            process_name = self.monitored_processes[pid]['process'].name()
            # Don't remove protected processes
            if self.is_protected_process(process_name):
                return
            del self.monitored_processes[pid]
            logger.info(f"Removed process {pid} ({process_name}) from monitoring")
    
    def _get_network_io(self, process: psutil.Process) -> Tuple[int, int]:
        """Get network connection count for a process."""
        try:
            connections = process.connections(kind='inet')
            return (len(connections), len(connections))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return (0, 0)
    
    def _can_check_window_focus(self, process: psutil.Process) -> bool:
        """Check if we can determine window focus for this process."""
        return sys.platform == "win32"
    
    def _is_process_active(self, pid: int) -> bool:
        """
        Check if a process is active based on various criteria.
        
        Args:
            pid: Process ID to check
            
        Returns:
            Boolean indicating if process is active
        """
        # Terminal PID is always considered active
        if self.terminal_pid and pid == self.terminal_pid:
            return True
            
        if pid not in self.monitored_processes:
            return False
            
        process_info = self.monitored_processes[pid]
        process = process_info['process']
        process_name = process_info['name']
        
        # Protected processes are always considered active
        if self.is_protected_process(process_name):
            return True
            
        try:
            # Check if process is still running
            if not process.is_running():
                return False
            
            # Get current CPU usage percentage (this is more reliable than CPU times)
            current_cpu_percent = process.cpu_percent(interval=0.1)
            
            # Check CPU activity - if CPU usage is above 1%, consider it active
            cpu_active = current_cpu_percent > 1.0
            
            # Check memory activity (significant change indicates activity)
            current_memory_info = process.memory_info()
            memory_active = (
                abs(current_memory_info.rss - process_info['last_memory_info'].rss) > 512 * 1024  # 512KB threshold (lowered)
            )
            
            # Check network activity
            current_network_io = self._get_network_io(process)
            network_active = (
                current_network_io[0] != process_info['last_network_io'][0] or
                current_network_io[1] != process_info['last_network_io'][1]
            )
            
            # Update last known values
            process_info['last_memory_info'] = current_memory_info
            process_info['last_network_io'] = current_network_io
            
            # Process is active if any of these conditions are met
            is_active = cpu_active or memory_active or network_active
            
            # Special handling: if this is the first few checks, consider the process active
            # to give it time to settle
            checks_count = process_info.get('checks_count', 0)
            process_info['checks_count'] = checks_count + 1
            
            if checks_count < 3:  # First 3 checks, consider active
                is_active = True
                logger.debug(f"Process {pid} in initial checks ({checks_count}/3), considering active")
            
            # Debug output for activity detection
            if pid in self.monitored_processes:
                inactive_time = (datetime.now() - process_info['last_activity_time']).total_seconds()
                logger.info(f"Process {pid} ({process_name}): CPU={current_cpu_percent:.1f}%, Mem_change={memory_active}, Net={network_active}, Active={is_active}, Inactive={inactive_time:.1f}s")
            
            # Update last activity time if process is active
            if is_active:
                process_info['last_activity_time'] = datetime.now()
                logger.debug(f"Process {pid} is active - resetting activity timer")
            
            return is_active
            
        except psutil.NoSuchProcess:
            # Process no longer exists
            return False
        except Exception as e:
            logger.error(f"Error checking activity for process {pid}: {e}")
            return False
    
    def _terminate_process(self, pid: int):
        """
        Terminate a process forcefully.
        
        Args:
            pid: Process ID to terminate
        """
        # Never terminate the terminal PID
        if self.terminal_pid and pid == self.terminal_pid:
            logger.info(f"Skipping termination of terminal PID {pid}")
            return
            
        try:
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Never terminate protected processes
            if self.is_protected_process(process_name):
                logger.info(f"Skipping termination of protected process {process_name} (PID: {pid})")
                return
            
            # Debug: Check if process should really be terminated
            if pid in self.monitored_processes:
                process_info = self.monitored_processes[pid]
                start_time = process_info.get('start_time', datetime.now())
                last_activity = process_info['last_activity_time']
                time_since_start = (datetime.now() - start_time).total_seconds()
                inactive_time = (datetime.now() - last_activity).total_seconds()
                logger.info(f"Terminating process {pid} ({process_name}): Started {time_since_start:.1f}s ago, inactive for {inactive_time:.1f}s")
            else:
                logger.info(f"Terminating process {pid} ({process_name}) - not in monitored processes")
                
            process.terminate()
            try:
                process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
            except psutil.TimeoutExpired:
                logger.warning(f"Process {pid} did not terminate gracefully, forcing kill")
                process.kill()
            
            # Notify main application about process termination
            if self.process_termination_callback:
                try:
                    self.process_termination_callback(pid)
                except Exception as e:
                    logger.error(f"Error in process termination callback: {e}")
                    
        except psutil.NoSuchProcess:
            logger.info(f"Process {pid} already terminated")
        except Exception as e:
            logger.error(f"Error terminating process {pid}: {e}")
    
    def _check_for_new_processes(self):
        """
        Check for new processes to monitor from the monitored children file.
        """
        try:
            if os.path.exists(self.monitored_children_file):
                # Read all lines from the file
                with open(self.monitored_children_file, 'r') as f:
                    lines = f.readlines()
                
                if lines:
                    logger.info(f"Found {len(lines)} PIDs in monitored children file")
                
                # Process each line (each should be a PID)
                for line in lines:
                    line = line.strip()
                    if line and line.isdigit():
                        pid = int(line)
                        # Add process to monitoring if not already monitored
                        # and it's not the terminal PID and not a protected process
                        if pid not in self.monitored_processes and (not self.terminal_pid or pid != self.terminal_pid):
                            process_name = None
                            try:
                                test_process = psutil.Process(pid)
                                process_name = test_process.name()
                                # Verify process is actually running
                                if not test_process.is_running():
                                    logger.debug(f"Process {pid} is not running, skipping")
                                    continue
                            except psutil.NoSuchProcess:
                                logger.debug(f"Process {pid} does not exist, skipping")
                                continue
                            except Exception as e:
                                logger.debug(f"Error checking process {pid}: {e}, skipping")
                                continue
                            
                            # Check if it's a protected process
                            if process_name and self.is_protected_process(process_name):
                                logger.info(f"Skipping protected process {process_name} (PID: {pid}) from monitoring")
                                continue
                                
                            self.add_process(pid)
                
                # Clear the file after processing
                with open(self.monitored_children_file, 'w') as f:
                    f.write('')
            else:
                # File doesn't exist, log this occasionally
                if hasattr(self, '_last_file_check') and time.time() - self._last_file_check > 10:
                    logger.debug(f"Monitored children file does not exist: {self.monitored_children_file}")
                    self._last_file_check = time.time()
                elif not hasattr(self, '_last_file_check'):
                    self._last_file_check = time.time()
                    
        except Exception as e:
            logger.error(f"Error checking for new processes: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        # Check for new processes every second
        last_check_time = time.time()
        
        while self.monitoring:
            try:
                current_time = datetime.now()
                
                # Check for new processes from PowerShell every second
                if time.time() - last_check_time >= 1:
                    self._check_for_new_processes()
                    last_check_time = time.time()
                
                # Check each monitored process
                pids_to_remove = []
                for pid in list(self.monitored_processes.keys()):
                    # Terminal PID is never checked for inactivity
                    if self.terminal_pid and pid == self.terminal_pid:
                        continue
                        
                    process_name = self.monitored_processes[pid]['name']
                    # Protected processes are never checked for inactivity
                    if self.is_protected_process(process_name):
                        continue
                        
                    is_active = self._is_process_active(pid)
                    
                    # Prepare process info for callback
                    process_info = self.monitored_processes[pid]
                    cpu_percent = 0
                    try:
                        cpu_percent = process_info['process'].cpu_percent()
                    except:
                        pass
                    
                    memory_mb = 0
                    try:
                        memory_mb = process_info['process'].memory_info().rss / (1024 * 1024)
                    except:
                        pass
                    
                    process_data = {
                        'name': process_info['name'],
                        'cpu': round(cpu_percent, 2),
                        'memory': round(memory_mb, 2),
                        'last_active': process_info['last_activity_time'].strftime('%H:%M:%S'),
                        'inactive_time': round((current_time - process_info['last_activity_time']).total_seconds(), 2)
                    }
                    
                    # Call status callback if set
                    if self.process_status_callback:
                        try:
                            self.process_status_callback(pid, is_active, process_data)
                        except Exception as e:
                            logger.error(f"Error in process status callback: {e}")
                    
                    if not is_active:
                        # Check if timeout has been reached, but respect grace period for new processes
                        last_activity = process_info['last_activity_time']
                        start_time = process_info.get('start_time', last_activity)
                        grace_period = process_info.get('grace_period_seconds', 0)
                        
                        # Calculate time since process started
                        time_since_start = (current_time - start_time).total_seconds()
                        
                        # Only check for inactivity after grace period has passed
                        if time_since_start > grace_period:
                            inactive_duration = current_time - last_activity
                            
                            if inactive_duration.total_seconds() >= self.timeout_seconds:
                                logger.info(f"Process {pid} ({process_info['name']}) has been inactive for {inactive_duration.total_seconds():.1f}s (started {time_since_start:.1f}s ago), terminating")
                                self._terminate_process(pid)
                                pids_to_remove.append(pid)
                            else:
                                # Show countdown for processes approaching termination
                                remaining_time = self.timeout_seconds - inactive_duration.total_seconds()
                                if remaining_time <= 5:
                                    logger.info(f"Process {pid} ({process_info['name']}) will be terminated in {remaining_time:.1f}s")
                        else:
                            # Still in grace period
                            remaining_grace = grace_period - time_since_start
                            if remaining_grace <= 2:  # Only log when grace period is almost over
                                logger.info(f"Process {pid} ({process_info['name']}) still in grace period ({remaining_grace:.1f}s remaining)")
                
                # Remove terminated processes
                for pid in pids_to_remove:
                    # Notify main application about process termination if it wasn't already notified
                    if self.process_termination_callback and pid in self.monitored_processes:
                        try:
                            self.process_termination_callback(pid)
                        except Exception as e:
                            logger.error(f"Error in process termination callback for PID {pid}: {e}")
                    self.remove_process(pid)
                
                # Sleep for a short interval before next check
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)

def main():
    """Main function for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor and terminate inactive processes")
    parser.add_argument("--timeout", type=int, default=30, help="Inactivity timeout in seconds (default: 30)")
    parser.add_argument("--pid", type=int, help="PID of process to monitor")
    
    args = parser.parse_args()
    
    monitor = InactiveProcessMonitor(timeout_seconds=args.timeout)
    monitor.start_monitoring()
    
    if args.pid:
        monitor.add_process(args.pid)
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        monitor.stop_monitoring()
        sys.exit(0)

if __name__ == "__main__":
    main()