import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import subprocess
import os
import threading
import time
import psutil
from datetime import datetime
import sys

import inactive_process_monitor

class AutoTerminatorManager:
    def __init__(self, master):
        self.master = master
        master.title("🚀 Auto-Terminator Dashboard")
        master.geometry("1000x800")
        master.configure(bg='#2b2b2b')
        
        # Configure style
        self.setup_styles()

        self.ps_process = None
        self.psutil_process = None
        self.log_file_path = os.path.join(os.environ["TEMP"], "auto_terminator.log")
        
        # Auto-execution flag
        self.auto_execute_ai = tk.BooleanVar(value=False)
        

        
        # Inactive process monitoring
        self.inactive_process_monitor = None
        self.inactive_monitor_enabled = tk.BooleanVar(value=False)
        self.inactive_timeout_var = tk.IntVar(value=30)
        
        # Process monitoring process
        self.process_monitor_process = None
        
        # Process library to track all PIDs
        self.process_library = {}
        self.current_session_start_time = None
        
        # Active/Inactive processes tracking
        self.active_processes = {}
        self.inactive_processes = {}

        self.create_widgets()
        self.update_log_thread = None
        self.stop_update_log = threading.Event()
        self.update_resources_id = None # To store after method ID for cancellation

    def setup_styles(self):
        """Configure modern styling"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure colors
        self.colors = {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'accent': '#4CAF50',
            'danger': '#f44336',
            'warning': '#ff9800',
            'info': '#2196F3',
            'card_bg': '#3c3c3c'
        }
        
        # Configure ttk styles
        self.style.configure('Title.TLabel', 
                           background=self.colors['bg'], 
                           foreground=self.colors['fg'],
                           font=('Segoe UI', 16, 'bold'))
        
        self.style.configure('Card.TFrame',
                           background=self.colors['card_bg'],
                           relief='flat',
                           borderwidth=1)
        
        self.style.configure('Success.TButton',
                           background=self.colors['accent'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'))
        
        self.style.configure('Danger.TButton',
                           background=self.colors['danger'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'))

    def create_widgets(self):
        # Main container with padding
        main_frame = tk.Frame(self.master, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="🖥️ Terminal Auto-Terminator", style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = tk.Label(header_frame, text="AI-Enhanced Terminal Session Manager", 
                                bg=self.colors['bg'], fg=self.colors['info'], 
                                font=('Segoe UI', 10))
        subtitle_label.pack()
        
        # Control Panel
        control_frame = ttk.Frame(main_frame, style='Card.TFrame', padding=15)
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        control_title = tk.Label(control_frame, text="⚙️ Control Panel", 
                               bg=self.colors['card_bg'], fg=self.colors['fg'],
                               font=('Segoe UI', 12, 'bold'))
        control_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Timeout settings with modern styling
        timeout_frame = tk.Frame(control_frame, bg=self.colors['card_bg'])
        timeout_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Main timeout setting
        self.timeout_label = tk.Label(timeout_frame, text="⏱️ Idle Timeout:", 
                                    bg=self.colors['card_bg'], fg=self.colors['fg'],
                                    font=('Segoe UI', 10))
        self.timeout_label.pack(side=tk.LEFT)
        
        self.timeout_entry = tk.Entry(timeout_frame, font=('Segoe UI', 10), width=10,
                                    bg='#4a4a4a', fg='white', insertbackground='white',
                                    relief='flat', bd=5)
        self.timeout_entry.insert(0, "30")
        self.timeout_entry.pack(side=tk.LEFT, padx=(10, 5))
        
        tk.Label(timeout_frame, text="seconds", bg=self.colors['card_bg'], 
                fg=self.colors['fg'], font=('Segoe UI', 10)).pack(side=tk.LEFT)
        
        # Inactive process monitoring settings
        inactive_frame = tk.Frame(control_frame, bg=self.colors['card_bg'])
        inactive_frame.pack(fill=tk.X, pady=(10, 10))
        
        # Inactive monitoring checkbox
        self.inactive_monitor_checkbox = tk.Checkbutton(
            inactive_frame,
            text="Monitor inactive processes",
            variable=self.inactive_monitor_enabled,
            bg=self.colors['card_bg'],
            fg=self.colors['fg'],
            selectcolor=self.colors['card_bg'],
            activebackground=self.colors['card_bg'],
            activeforeground=self.colors['fg'],
            font=('Segoe UI', 10),
            highlightthickness=0
        )
        self.inactive_monitor_checkbox.pack(side=tk.LEFT)
        
        # Inactive timeout setting
        tk.Label(inactive_frame, text="Timeout:", bg=self.colors['card_bg'], 
                fg=self.colors['fg'], font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(10, 5))
        
        self.inactive_timeout_entry = tk.Entry(inactive_frame, font=('Segoe UI', 10), width=8,
                                              bg='#4a4a4a', fg='white', insertbackground='white',
                                              relief='flat', bd=5)
        self.inactive_timeout_entry.insert(0, "30")
        self.inactive_timeout_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Label(inactive_frame, text="seconds", bg=self.colors['card_bg'], 
                fg=self.colors['fg'], font=('Segoe UI', 10)).pack(side=tk.LEFT)
        
        # Auto-execution checkbox
        self.auto_exec_checkbox = tk.Checkbutton(
            control_frame,
            text="Auto-execute AI commands",
            variable=self.auto_execute_ai,
            bg=self.colors['card_bg'],
            fg=self.colors['fg'],
            selectcolor=self.colors['card_bg'],
            activebackground=self.colors['card_bg'],
            activeforeground=self.colors['fg'],
            font=('Segoe UI', 10),
            highlightthickness=0
        )
        self.auto_exec_checkbox.pack(anchor=tk.W, pady=(10, 0))
        
        # Buttons with modern styling
        button_frame = tk.Frame(control_frame, bg=self.colors['card_bg'])
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_button = tk.Button(button_frame, text="🚀 Start Terminal", 
                                    command=self.start_terminal,
                                    bg=self.colors['accent'], fg='white',
                                    font=('Segoe UI', 10, 'bold'),
                                    relief='flat', bd=0, padx=20, pady=8,
                                    cursor='hand2')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = tk.Button(button_frame, text="🛑 Stop Terminal", 
                                   command=self.stop_terminal, state=tk.DISABLED,
                                   bg=self.colors['danger'], fg='white',
                                   font=('Segoe UI', 10, 'bold'),
                                   relief='flat', bd=0, padx=20, pady=8,
                                   cursor='hand2')
        self.stop_button.pack(side=tk.LEFT)

        # Status indicator
        self.status_label = tk.Label(button_frame, text="● Stopped", 
                                   bg=self.colors['card_bg'], fg=self.colors['danger'],
                                   font=('Segoe UI', 10, 'bold'))
        self.status_label.pack(side=tk.RIGHT)

        # Resource Dashboard with cards
        dashboard_frame = ttk.Frame(main_frame, style='Card.TFrame', padding=15)
        dashboard_frame.pack(fill=tk.X, pady=(0, 15))
        
        dashboard_title = tk.Label(dashboard_frame, text="📊 System Resources", 
                                 bg=self.colors['card_bg'], fg=self.colors['fg'],
                                 font=('Segoe UI', 12, 'bold'))
        dashboard_title.pack(anchor=tk.W, pady=(0, 15))
        
        # Resource cards in grid
        resources_grid = tk.Frame(dashboard_frame, bg=self.colors['card_bg'])
        resources_grid.pack(fill=tk.X)
        
        # CPU Card
        cpu_card = tk.Frame(resources_grid, bg='#4a4a4a', relief='flat', bd=1)
        cpu_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(cpu_card, text="🔥 CPU", bg='#4a4a4a', fg=self.colors['warning'],
                font=('Segoe UI', 9, 'bold')).pack(pady=(8, 2))
        self.cpu_label = tk.Label(cpu_card, text="--%", bg='#4a4a4a', fg='white',
                                font=('Segoe UI', 14, 'bold'))
        self.cpu_label.pack(pady=(0, 8))
        
        # Memory Card
        mem_card = tk.Frame(resources_grid, bg='#4a4a4a', relief='flat', bd=1)
        mem_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(mem_card, text="💾 Memory", bg='#4a4a4a', fg=self.colors['info'],
                font=('Segoe UI', 9, 'bold')).pack(pady=(8, 2))
        self.memory_label = tk.Label(mem_card, text="-- MB", bg='#4a4a4a', fg='white',
                                   font=('Segoe UI', 14, 'bold'))
        self.memory_label.pack(pady=(0, 8))
        
        # Network Card
        net_card = tk.Frame(resources_grid, bg='#4a4a4a', relief='flat', bd=1)
        net_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(net_card, text="🌐 Network", bg='#4a4a4a', fg=self.colors['accent'],
                font=('Segoe UI', 9, 'bold')).pack(pady=(8, 2))
        self.network_label = tk.Label(net_card, text="--", bg='#4a4a4a', fg='white',
                                    font=('Segoe UI', 14, 'bold'))
        self.network_label.pack(pady=(0, 8))
        
        # Power Card
        power_card = tk.Frame(resources_grid, bg='#4a4a4a', relief='flat', bd=1)
        power_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(power_card, text="⚡ Power", bg='#4a4a4a', fg='#9C27B0',
                font=('Segoe UI', 9, 'bold')).pack(pady=(8, 2))
        self.battery_label = tk.Label(power_card, text="--", bg='#4a4a4a', fg='white',
                                    font=('Segoe UI', 14, 'bold'))
        self.battery_label.pack(pady=(0, 8))

        # Active/Inactive Processes Section
        processes_frame = ttk.Frame(main_frame, style='Card.TFrame', padding=15)
        processes_frame.pack(fill=tk.X, pady=(0, 15))
        
        processes_title = tk.Label(processes_frame, text="📋 Active/Inactive Processes", 
                                 bg=self.colors['card_bg'], fg=self.colors['fg'],
                                 font=('Segoe UI', 12, 'bold'))
        processes_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Create a frame for the process lists
        process_lists_frame = tk.Frame(processes_frame, bg=self.colors['card_bg'])
        process_lists_frame.pack(fill=tk.X)
        
        # Active processes
        active_frame = tk.Frame(process_lists_frame, bg=self.colors['card_bg'])
        active_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(active_frame, text="🟢 Active Processes", bg=self.colors['card_bg'], 
                fg=self.colors['accent'], font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        
        self.active_processes_text = scrolledtext.ScrolledText(active_frame, width=40, height=8,
                                                              state=tk.DISABLED,
                                                              bg='#1e1e1e', fg='#00ff00',
                                                              font=('Consolas', 9),
                                                              relief='flat', bd=0,
                                                              insertbackground='#00ff00')
        self.active_processes_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Inactive processes
        inactive_frame = tk.Frame(process_lists_frame, bg=self.colors['card_bg'])
        inactive_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(inactive_frame, text="🔴 Inactive Processes", bg=self.colors['card_bg'], 
                fg=self.colors['danger'], font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        
        self.inactive_processes_text = scrolledtext.ScrolledText(inactive_frame, width=40, height=8,
                                                                state=tk.DISABLED,
                                                                bg='#1e1e1e', fg='#ff9999',
                                                                font=('Consolas', 9),
                                                                relief='flat', bd=0,
                                                                insertbackground='#ff9999')
        self.inactive_processes_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Log Display with modern styling
        log_frame = ttk.Frame(main_frame, style='Card.TFrame', padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        log_header = tk.Frame(log_frame, bg=self.colors['card_bg'])
        log_header.pack(fill=tk.X, pady=(0, 10))
        
        log_title = tk.Label(log_header, text="📋 Terminal Logs", 
                           bg=self.colors['card_bg'], fg=self.colors['fg'],
                           font=('Segoe UI', 12, 'bold'))
        log_title.pack(side=tk.LEFT)
        
        # Report and clear buttons
        button_frame_right = tk.Frame(log_header, bg=self.colors['card_bg'])
        button_frame_right.pack(side=tk.RIGHT)
        
        # Library viewer button
        library_btn = tk.Button(button_frame_right, text="📚 View Library", command=self.view_library,
                             bg='#9C27B0', fg='white', font=('Segoe UI', 8),
                             relief='flat', bd=0, padx=10, pady=4, cursor='hand2')
        library_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Download all logs button
        download_logs_btn = tk.Button(button_frame_right, text="📥 Download All Logs", command=self.download_all_logs,
                             bg=self.colors['info'], fg='white', font=('Segoe UI', 8),
                             relief='flat', bd=0, padx=10, pady=4, cursor='hand2')
        download_logs_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        clear_btn = tk.Button(button_frame_right, text="🗑️ Clear", command=self.clear_log_display,
                            bg='#666666', fg='white', font=('Segoe UI', 8),
                            relief='flat', bd=0, padx=10, pady=4, cursor='hand2')
        clear_btn.pack(side=tk.RIGHT)

        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=10, 
                                                state=tk.DISABLED,
                                                bg='#1e1e1e', fg='#00ff00',
                                                font=('Consolas', 9),
                                                relief='flat', bd=0,
                                                insertbackground='#00ff00')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Start the process update thread
        self.start_process_update_thread()

    def start_process_update_thread(self):
        """Start a thread to periodically update process information"""
        self.process_update_thread = threading.Thread(target=self._update_process_display, daemon=True)
        self.process_update_thread.start()

    def _update_process_display(self):
        """Update the active/inactive process displays"""
        while True:
            try:
                # Update active processes display
                self.active_processes_text.config(state=tk.NORMAL)
                self.active_processes_text.delete(1.0, tk.END)
                
                active_text = ""
                for pid, info in self.active_processes.items():
                    active_text += f"PID: {pid} - {info.get('name', 'Unknown')}\n"
                    active_text += f"  CPU: {info.get('cpu', '--')}%, Mem: {info.get('memory', '--')} MB\n"
                    active_text += f"  Last Active: {info.get('last_active', '--')}\n\n"
                
                self.active_processes_text.insert(tk.END, active_text if active_text else "No active processes\n")
                self.active_processes_text.config(state=tk.DISABLED)
                
                # Update inactive processes display
                self.inactive_processes_text.config(state=tk.NORMAL)
                self.inactive_processes_text.delete(1.0, tk.END)
                
                inactive_text = ""
                for pid, info in self.inactive_processes.items():
                    inactive_text += f"PID: {pid} - {info.get('name', 'Unknown')}\n"
                    inactive_text += f"  CPU: {info.get('cpu', '--')}%, Mem: {info.get('memory', '--')} MB\n"
                    inactive_text += f"  Inactive for: {info.get('inactive_time', '--')}s\n\n"
                
                self.inactive_processes_text.insert(tk.END, inactive_text if inactive_text else "No inactive processes\n")
                self.inactive_processes_text.config(state=tk.DISABLED)
                
            except Exception as e:
                print(f"Error updating process display: {e}")
            
            time.sleep(2)  # Update every 2 seconds

    def update_process_status(self, pid, is_active, process_info):
        """Update the status of a process"""
        if is_active:
            self.active_processes[pid] = process_info
            if pid in self.inactive_processes:
                del self.inactive_processes[pid]
        else:
            self.inactive_processes[pid] = process_info
            if pid in self.active_processes:
                del self.active_processes[pid]
        
        # Add new child processes to the process library for separate reporting
        if pid not in self.process_library and pid != (self.ps_process.pid if self.ps_process else None):
            self.add_child_process_to_library(pid, process_info)
        elif pid in self.process_library and pid != (self.ps_process.pid if self.ps_process else None):
            # Update existing child process in library
            self.update_child_process_in_library(pid, process_info, is_active)

    def start_terminal(self):
        if self.ps_process and self.ps_process.poll() is None:
            # Process is already running
            return

        # Ensure log file is clean or created
        if os.path.exists(self.log_file_path):
            os.remove(self.log_file_path)

        # Get timeout value from entry
        try:
            timeout_value = int(self.timeout_entry.get())
            if timeout_value <= 0:
                raise ValueError("Timeout must be a positive integer.")
        except ValueError as e:
            messagebox.showerror("Invalid Timeout", str(e))
            return

        # Get inactive timeout value
        try:
            inactive_timeout_value = int(self.inactive_timeout_entry.get())
            if inactive_timeout_value <= 0:
                raise ValueError("Inactive timeout must be a positive integer.")
        except ValueError as e:
            messagebox.showerror("Invalid Inactive Timeout", str(e))
            return

        # Use subprocess.Popen to launch the PowerShell script in a new window
        try:
            script_path = os.path.join(os.getcwd(), "auto-terminator.ps1")
            
            # Build command with auto-execute flag if enabled
            cmd = [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-NoExit",
                "-File", script_path,
                "-Timeout", str(timeout_value)
            ]
            
            # Add auto-execute flag if enabled
            if self.auto_execute_ai.get():
                cmd.append("-AutoExecute")
            
            self.ps_process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE  # Opens in a new console window
            )
            
            # Process monitoring is handled by auto-terminator.ps1 and inactive_process_monitor.py
            # self.start_process_monitor(timeout_value)  # Disabled - process_monitor.ps1 doesn't exist
            
            # Start inactive process monitoring if enabled
            if self.inactive_monitor_enabled.get():
                self.start_inactive_process_monitor(inactive_timeout_value)
            
            # Get the psutil process object
            try:
                self.psutil_process = psutil.Process(self.ps_process.pid)
            except psutil.NoSuchProcess:
                self.psutil_process = None
                print("Could not get psutil process object. Resource monitoring will be limited.")

            # Add to process library
            self.current_session_start_time = datetime.now()
            self.process_library[self.ps_process.pid] = {
                'start_time': self.current_session_start_time,
                'end_time': None,
                'status': 'Running',
                'auto_execute': self.auto_execute_ai.get(),
                'timeout': timeout_value,
                'logs': [],  # Will store log entries for this process
                'dashboard_data': {
                    'cpu': '--%',
                    'memory': '-- MB',
                    'network': '--',
                    'power': '--'
                }
            }
            print(f"Added PID {self.ps_process.pid} to process library. Total processes: {len(self.process_library)}")

            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="● Running", fg=self.colors['accent'])
            self.start_log_updater()
            self.update_resource_dashboard()
            print(f"Launched auto-terminator.ps1 with PID: {self.ps_process.pid} and Timeout: {timeout_value}s")
            if self.auto_execute_ai.get():
                print("Auto-execution of AI commands is ENABLED")
        except Exception as e:
            print(f"Error launching PowerShell: {e}")
            self.stop_button.config(state=tk.DISABLED)
            self.start_button.config(state=tk.NORMAL)

    def start_process_monitor(self, termination_delay):
        """Start the separate process monitor"""
        try:
            script_path = os.path.join(os.getcwd(), "process_monitor.ps1")
            
            # Build command for process monitor
            cmd = [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-NoExit",
                "-File", script_path,
                "-Timeout", str(termination_delay)
            ]
            
            self.process_monitor_process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE  # Opens in a new console window
            )
            
            print(f"Launched process monitor with PID: {self.process_monitor_process.pid} and Termination Delay: {termination_delay}s")
        except Exception as e:
            print(f"Error launching process monitor: {e}")

    def start_inactive_process_monitor(self, timeout_seconds):
        """Start the inactive process monitor"""
        try:
            self.inactive_process_monitor = inactive_process_monitor.InactiveProcessMonitor(timeout_seconds)
            # Set the callback for process status updates
            self.inactive_process_monitor.set_process_status_callback(self.update_process_status)
            # Set the callback for process termination
            self.inactive_process_monitor.set_process_termination_callback(self.mark_child_process_terminated)
            # Set the terminal PID to exclude from termination
            if self.ps_process:
                self.inactive_process_monitor.set_terminal_pid(self.ps_process.pid)
            self.inactive_process_monitor.start_monitoring()
            print(f"Inactive process monitor started with timeout: {timeout_seconds}s")
        except Exception as e:
            print(f"Error starting inactive process monitor: {e}")

    def stop_terminal(self):
        if self.ps_process and self.ps_process.poll() is None:
            print(f"Terminating auto-terminator process (PID: {self.ps_process.pid})...")
            self.stop_log_updater()
            self.cancel_resource_updates()
            try:
                # Use taskkill for graceful termination on Windows
                subprocess.run(["taskkill", "/PID", str(self.ps_process.pid), "/T", "/F"], check=True)
                print("Process terminated.")
            except subprocess.CalledProcessError as e:
                print(f"Error terminating process: {e}")
            
            # Process monitor stopping is handled by auto-terminator.ps1 and inactive_process_monitor.py
            # self.stop_process_monitor()  # Disabled - process_monitor.ps1 doesn't exist
            
            # Stop inactive process monitor
            self.stop_inactive_process_monitor()
            
            # Update process library with final dashboard data
            if self.ps_process.pid in self.process_library:
                self.process_library[self.ps_process.pid]['end_time'] = datetime.now()
                self.process_library[self.ps_process.pid]['status'] = 'Terminated'
                # Capture final dashboard data
                self.process_library[self.ps_process.pid]['dashboard_data'] = {
                    'cpu': self.cpu_label.cget("text"),
                    'memory': self.memory_label.cget("text"),
                    'network': self.network_label.cget("text"),
                    'power': self.battery_label.cget("text")
                }
                print(f"Updated PID {self.ps_process.pid} in process library as Terminated")

            self.ps_process = None
            self.psutil_process = None

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="● Stopped", fg=self.colors['danger'])
        self.clear_log_display()
        self.reset_resource_dashboard()
        
        # Clear process displays
        self.active_processes = {}
        self.inactive_processes = {}

    def add_child_process_to_library(self, pid, process_info):
        """Add a child process to the process library for separate reporting"""
        try:
            if pid not in self.process_library:
                self.process_library[pid] = {
                    'start_time': datetime.now(),
                    'end_time': None,
                    'status': 'Running (Child Process)',
                    'auto_execute': False,  # Child processes don't have auto-execute
                    'timeout': self.inactive_timeout_var.get() if hasattr(self, 'inactive_timeout_var') else 30,
                    'logs': [],  # Will store log entries for this child process
                    'dashboard_data': {
                        'cpu': f"{process_info.get('cpu', 0)}%",
                        'memory': f"{process_info.get('memory', 0)} MB",
                        'network': '--',
                        'power': '--'
                    },
                    'process_name': process_info.get('name', 'Unknown'),
                    'parent_pid': self.ps_process.pid if self.ps_process else None
                }
                print(f"Added child process PID {pid} ({process_info.get('name', 'Unknown')}) to process library. Total processes: {len(self.process_library)}")
        except Exception as e:
            print(f"Error adding child process {pid} to library: {e}")

    def update_child_process_in_library(self, pid, process_info, is_active):
        """Update child process information in the library"""
        try:
            if pid in self.process_library:
                # Update dashboard data
                self.process_library[pid]['dashboard_data'] = {
                    'cpu': f"{process_info.get('cpu', 0)}%",
                    'memory': f"{process_info.get('memory', 0)} MB",
                    'network': '--',
                    'power': '--'
                }
                
                # Update status based on activity
                if is_active:
                    self.process_library[pid]['status'] = 'Running (Child Process)'
                else:
                    inactive_time = process_info.get('inactive_time', 0)
                    self.process_library[pid]['status'] = f'Inactive (Child Process) - {inactive_time}s'
                
                # Add log entry for significant status changes
                if not is_active and process_info.get('inactive_time', 0) > 10:
                    log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] Child process {pid} ({process_info.get('name', 'Unknown')}) inactive for {process_info.get('inactive_time', 0)}s\n"
                    self.process_library[pid]['logs'].append(log_entry)
        except Exception as e:
            print(f"Error updating child process {pid} in library: {e}")

    def mark_child_process_terminated(self, pid):
        """Mark a child process as terminated in the library"""
        try:
            if pid in self.process_library:
                self.process_library[pid]['end_time'] = datetime.now()
                
                # Check if it was terminated due to inactivity or naturally
                current_status = self.process_library[pid].get('status', '')
                if 'Inactive' in current_status:
                    self.process_library[pid]['status'] = 'Terminated (Child Process - Inactivity)'
                    log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] Child process {pid} terminated due to inactivity\n"
                else:
                    self.process_library[pid]['status'] = 'Terminated (Child Process - Natural)'
                    log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] Child process {pid} terminated naturally\n"
                
                self.process_library[pid]['logs'].append(log_entry)
                print(f"Marked child process PID {pid} as terminated in process library")
        except Exception as e:
            print(f"Error marking child process {pid} as terminated: {e}")

    def stop_process_monitor(self):
        """Stop the process monitor"""
        if self.process_monitor_process and self.process_monitor_process.poll() is None:
            print(f"Terminating process monitor (PID: {self.process_monitor_process.pid})...")
            try:
                # Use taskkill for graceful termination on Windows
                subprocess.run(["taskkill", "/PID", str(self.process_monitor_process.pid), "/T", "/F"], check=True)
                print("Process monitor terminated.")
            except subprocess.CalledProcessError as e:
                print(f"Error terminating process monitor: {e}")
            
            self.process_monitor_process = None

    def stop_inactive_process_monitor(self):
        """Stop the inactive process monitor"""
        if self.inactive_process_monitor:
            self.inactive_process_monitor.stop_monitoring()
            self.inactive_process_monitor = None
            print("Inactive process monitor stopped.")

    def start_log_updater(self):
        self.stop_update_log.clear()
        self.update_log_thread = threading.Thread(target=self._update_log_display)
        self.update_log_thread.daemon = True  # Allows the thread to exit with the main program
        self.update_log_thread.start()

    def stop_log_updater(self):
        self.stop_update_log.set()
        if self.update_log_thread and self.update_log_thread.is_alive():
            self.update_log_thread.join(timeout=1) # Wait for thread to finish

    def _update_log_display(self):
        last_read_position = 0
        while not self.stop_update_log.is_set():
            try:
                if os.path.exists(self.log_file_path):
                    with open(self.log_file_path, "r", encoding="utf-8") as f:
                        f.seek(last_read_position)
                        new_content = f.read()
                        if new_content:
                            self.log_text.config(state=tk.NORMAL)
                            self.log_text.insert(tk.END, new_content)
                            self.log_text.see(tk.END) # Scroll to the end
                            self.log_text.config(state=tk.DISABLED)
                            last_read_position = f.tell()
                            
                            # Store log content for the current process
                            if self.ps_process and self.ps_process.pid in self.process_library:
                                self.process_library[self.ps_process.pid]['logs'].append(new_content)
                                
                                # Update dashboard data for running process
                                self.process_library[self.ps_process.pid]['dashboard_data'] = {
                                    'cpu': self.cpu_label.cget("text"),
                                    'memory': self.memory_label.cget("text"),
                                    'network': self.network_label.cget("text"),
                                    'power': self.battery_label.cget("text")
                                }
            except FileNotFoundError:
                pass # Log file might not be created yet
            except Exception as e:
                print(f"Error reading log file: {e}")
            
            time.sleep(0.5) # Check every 500ms

    # Child process monitoring is now handled by the PowerShell script

    def update_resource_dashboard(self):
        cpu_percent = "--"
        memory_mb = "--"
        network_connections = "--"
        battery_status = "--"

        if self.psutil_process and self.psutil_process.is_running():
            try:
                cpu_percent = self.psutil_process.cpu_percent(interval=0.1) # Non-blocking
                mem_info = self.psutil_process.memory_info()
                memory_mb = f"{(mem_info.rss / (1024 * 1024)):.2f}"

                # Get all child processes
                children = self.psutil_process.children(recursive=True)
                all_procs = [self.psutil_process] + children
                total_connections = 0
                for proc in all_procs:
                    try:
                        total_connections += len(proc.connections(kind="inet"))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                network_connections = str(total_connections)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.psutil_process = None # Process might have just ended or access denied

        # Terminal Power Consumption
        power_consumption = "--"
        if self.psutil_process and self.psutil_process.is_running():
            try:
                # Get CPU usage and estimate power consumption
                # Rough estimation: Base consumption + CPU factor + Memory factor
                base_power = 0.5  # Base power consumption in watts
                cpu_power = (float(cpu_percent) if cpu_percent != "--" else 0) * 2.0  # CPU can consume up to 2W
                memory_power = (float(memory_mb) if memory_mb != "--" else 0) / 1000 * 0.1  # Memory factor
                
                total_power = base_power + cpu_power + memory_power
                power_consumption = f"{total_power:.2f}W"
                
                # Get all child processes for total consumption
                children = self.psutil_process.children(recursive=True)
                if children:
                    child_power = 0
                    for child in children:
                        try:
                            child_cpu = child.cpu_percent(interval=0.1)
                            child_power += (child_cpu / 100) * 0.5  # Child processes consume less
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    total_power += child_power
                    power_consumption = f"{total_power:.2f}W"
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                power_consumption = "N/A"
        
        battery_status = power_consumption

        self.cpu_label.config(text=f"{cpu_percent}%")
        self.memory_label.config(text=f"{memory_mb} MB")
        self.network_label.config(text=f"{network_connections}")
        self.battery_label.config(text=f"{battery_status}")

        self.update_resources_id = self.master.after(1000, self.update_resource_dashboard) # Update every 1 second

    def cancel_resource_updates(self):
        if self.update_resources_id:
            self.master.after_cancel(self.update_resources_id)
            self.update_resources_id = None

    def reset_resource_dashboard(self):
        self.cpu_label.config(text="--%")
        self.memory_label.config(text="-- MB")
        self.network_label.config(text="--")
        self.battery_label.config(text="--")

    def clear_log_display(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def download_all_logs(self):
        """Download all logs from the current session"""
        try:
            # Get current log content
            log_content = self.log_text.get(1.0, tk.END)
            
            if not log_content.strip():
                messagebox.showinfo("No Logs", "No logs available to download.")
                return
            
            # Ask user where to save the logs
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save All Logs As",
                initialfile=f"auto_terminator_all_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(log_content)
                messagebox.showinfo("Logs Downloaded", f"All logs saved successfully to:\n{file_path}")
            else:
                print("Logs download cancelled by user")
                
        except Exception as e:
            error_msg = f"Error downloading logs: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)

    def view_library(self):
        """Open a new window to view the library of PID reports"""
        try:
            print(f"Opening library with {len(self.process_library)} processes")
            for pid, info in self.process_library.items():
                print(f"  PID {pid}: {info['status']} - Started: {info['start_time']}")
            # Create library viewer window
            library_window = tk.Toplevel(self.master)
            library_window.title("📚 Process Library")
            library_window.geometry("800x600")
            library_window.configure(bg='#2b2b2b')
            
            # Header
            header_frame = tk.Frame(library_window, bg='#2b2b2b')
            header_frame.pack(fill=tk.X, padx=20, pady=20)
            
            title_label = tk.Label(header_frame, text="Process Library", 
                                 bg='#2b2b2b', fg='white',
                                 font=('Segoe UI', 16, 'bold'))
            title_label.pack()
            
            subtitle_label = tk.Label(header_frame, text=f"Total processes: {len(self.process_library)}", 
                                    bg='#2b2b2b', fg='#2196F3',
                                    font=('Segoe UI', 10))
            subtitle_label.pack()
            
            # Download all reports button
            download_all_btn = tk.Button(header_frame, text="📥 Download All Reports", 
                                       command=lambda: self.download_all_pid_reports(library_window),
                                       bg='#4CAF50', fg='white', font=('Segoe UI', 10, 'bold'),
                                       relief='flat', bd=0, padx=20, pady=8, cursor='hand2')
            download_all_btn.pack(pady=10)
            
            # Create a frame for the process list
            list_frame = tk.Frame(library_window, bg='#3c3c3c')
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
            
            # Create a canvas and scrollbar for the process list
            canvas = tk.Canvas(list_frame, bg='#3c3c3c', highlightthickness=0)
            scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg='#3c3c3c')
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Add process cards
            if not self.process_library:
                no_processes_label = tk.Label(scrollable_frame, text="No processes in library", 
                                            bg='#3c3c3c', fg='white', font=('Segoe UI', 12))
                no_processes_label.pack(pady=50)
            else:
                for pid, info in self.process_library.items():
                    # Create a card for each process
                    card_frame = tk.Frame(scrollable_frame, bg='#4a4a4a', relief='flat', bd=1)
                    card_frame.pack(fill=tk.X, padx=10, pady=5)
                    
                    # Process info
                    pid_label = tk.Label(card_frame, text=f"PID: {pid}", 
                                       bg='#4a4a4a', fg='white', font=('Segoe UI', 12, 'bold'))
                    pid_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
                    
                    status_label = tk.Label(card_frame, text=f"Status: {info['status']}", 
                                          bg='#4a4a4a', fg='white', font=('Segoe UI', 10))
                    status_label.pack(anchor=tk.W, padx=10)
                    
                    start_label = tk.Label(card_frame, text=f"Started: {info['start_time'].strftime('%Y-%m-%d %H:%M:%S') if info['start_time'] else 'Unknown'}", 
                                         bg='#4a4a4a', fg='white', font=('Segoe UI', 10))
                    start_label.pack(anchor=tk.W, padx=10)
                    
                    if info['end_time']:
                        end_label = tk.Label(card_frame, text=f"Ended: {info['end_time'].strftime('%Y-%m-%d %H:%M:%S')}", 
                                           bg='#4a4a4a', fg='white', font=('Segoe UI', 10))
                        end_label.pack(anchor=tk.W, padx=10)
                    
                    auto_exec_label = tk.Label(card_frame, text=f"Auto-execute AI: {'Yes' if info['auto_execute'] else 'No'}", 
                                             bg='#4a4a4a', fg='white', font=('Segoe UI', 10))
                    auto_exec_label.pack(anchor=tk.W, padx=10)
                    
                    # Buttons frame
                    buttons_frame = tk.Frame(card_frame, bg='#4a4a4a')
                    buttons_frame.pack(fill=tk.X, padx=10, pady=10)
                    
                    # View report button
                    view_btn = tk.Button(buttons_frame, text="👁️ View Report", 
                                       command=lambda p=pid: self.view_pid_report(p),
                                       bg='#2196F3', fg='white', font=('Segoe UI', 9),
                                       relief='flat', bd=0, padx=15, pady=5, cursor='hand2')
                    view_btn.pack(side=tk.LEFT, padx=(0, 10))
                    
                    # Download report button
                    download_btn = tk.Button(buttons_frame, text="📥 Download Report", 
                                           command=lambda p=pid: self.download_pid_report(p),
                                           bg='#4CAF50', fg='white', font=('Segoe UI', 9),
                                           relief='flat', bd=0, padx=15, pady=5, cursor='hand2')
                    download_btn.pack(side=tk.LEFT, padx=(0, 10))
                    
                    # Delete report button
                    delete_btn = tk.Button(buttons_frame, text="🗑️ Delete Report", 
                                         command=lambda p=pid: self.delete_pid_report(p, card_frame, library_window),
                                         bg='#f44336', fg='white', font=('Segoe UI', 9),
                                         relief='flat', bd=0, padx=15, pady=5, cursor='hand2')
                    delete_btn.pack(side=tk.LEFT)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            error_msg = f"Error opening library: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)

    def view_pid_report(self, pid):
        """View the report for a specific PID"""
        try:
            if pid not in self.process_library:
                messagebox.showerror("Error", f"No data found for PID {pid}")
                return
            
            info = self.process_library[pid]
            
            # Combine all logs for this process
            log_content = "".join(info.get('logs', []))
            
            # Calculate duration
            duration = "N/A"
            if info['start_time']:
                if info['end_time']:
                    duration = str(info['end_time'] - info['start_time'])
                elif info['status'] == 'Running':
                    duration = str(datetime.now() - info['start_time'])
            
            # Get dashboard data
            dashboard_data = info.get('dashboard_data', {
                'cpu': '--%',
                'memory': '-- MB',
                'network': '--',
                'power': '--'
            })
            
            # Create report content with dashboard information
            report_content = f"""Auto-Terminator Process Report
==============================
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
PID: {pid}

PROCESS INFORMATION
-------------------
PID: {pid}
Status: {info['status']}
Started: {info['start_time'].strftime('%Y-%m-%d %H:%M:%S') if info['start_time'] else 'Unknown'}
Ended: {info['end_time'].strftime('%Y-%m-%d %H:%M:%S') if info['end_time'] else 'N/A'}
Duration: {duration}
Auto-execute AI: {'Yes' if info['auto_execute'] else 'No'}
Timeout: {info['timeout']} seconds

DASHBOARD INFORMATION
---------------------
CPU Usage: {dashboard_data['cpu']}
Memory Usage: {dashboard_data['memory']}
Network Connections: {dashboard_data['network']}
Power Consumption: {dashboard_data['power']}

LOG CONTENT
-----------
{log_content}
"""
            
            # Create report viewer window
            report_window = tk.Toplevel(self.master)
            report_window.title(f"📝 Report for PID {pid}")
            report_window.geometry("800x600")
            report_window.configure(bg='#2b2b2b')
            
            # Create text widget with scrollbar
            text_frame = tk.Frame(report_window, bg='#2b2b2b')
            text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD, bg='#1e1e1e', fg='#00ff00',
                                font=('Consolas', 10), insertbackground='#00ff00')
            text_widget.insert(tk.END, report_content)
            text_widget.config(state=tk.DISABLED)
            
            scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.config(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
        except Exception as e:
            error_msg = f"Error viewing report for PID {pid}: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)

    def download_pid_report(self, pid):
        """Download the report for a specific PID"""
        try:
            if pid not in self.process_library:
                messagebox.showerror("Error", f"No data found for PID {pid}")
                return
            
            info = self.process_library[pid]
            
            # Combine all logs for this process
            log_content = "".join(info.get('logs', []))
            
            # Calculate duration
            duration = "N/A"
            if info['start_time']:
                if info['end_time']:
                    duration = str(info['end_time'] - info['start_time'])
                elif info['status'] == 'Running':
                    duration = str(datetime.now() - info['start_time'])
            
            # Get dashboard data
            dashboard_data = info.get('dashboard_data', {
                'cpu': '--%',
                'memory': '-- MB',
                'network': '--',
                'power': '--'
            })
            
            # Create report content with dashboard information
            report_content = f"""Auto-Terminator Process Report
==============================
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
PID: {pid}

PROCESS INFORMATION
-------------------
PID: {pid}
Status: {info['status']}
Started: {info['start_time'].strftime('%Y-%m-%d %H:%M:%S') if info['start_time'] else 'Unknown'}
Ended: {info['end_time'].strftime('%Y-%m-%d %H:%M:%S') if info['end_time'] else 'N/A'}
Duration: {duration}
Auto-execute AI: {'Yes' if info['auto_execute'] else 'No'}
Timeout: {info['timeout']} seconds

DASHBOARD INFORMATION
---------------------
CPU Usage: {dashboard_data['cpu']}
Memory Usage: {dashboard_data['memory']}
Network Connections: {dashboard_data['network']}
Power Consumption: {dashboard_data['power']}

LOG CONTENT
-----------
{log_content}
"""
            
            # Ask user where to save the report
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title=f"Save Report for PID {pid}",
                initialfile=f"auto_terminator_report_pid_{pid}.txt"
            )
            
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(report_content)
                messagebox.showinfo("Report Downloaded", f"Report for PID {pid} saved successfully to:\n{file_path}")
            else:
                print(f"Report download for PID {pid} cancelled by user")
                
        except Exception as e:
            error_msg = f"Error downloading report for PID {pid}: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)

    def delete_pid_report(self, pid, card_frame, library_window):
        """Delete a PID report from the library"""
        try:
            # Confirm deletion
            result = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete the report for PID {pid}?\n\nThis action cannot be undone.")
            if not result:
                return
            
            # Remove from process library
            if pid in self.process_library:
                del self.process_library[pid]
                # Destroy the card frame
                card_frame.destroy()
                print(f"Deleted report for PID {pid}")
                
                # Update the library window title
                library_window.title(f"📚 Process Library (Total: {len(self.process_library)})")
            else:
                messagebox.showerror("Error", f"No data found for PID {pid}")
                
        except Exception as e:
            error_msg = f"Error deleting report for PID {pid}: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)

    def download_all_pid_reports(self, parent_window=None):
        """Download reports for all PIDs in the library"""
        try:
            if not self.process_library:
                messagebox.showinfo("No Processes", "No processes found in the library.")
                return
            
            # Ask user where to save the reports
            directory = filedialog.askdirectory(title="Select Directory to Save Reports")
            if not directory:
                print("Report download cancelled by user")
                return
            
            reports_generated = 0
            for pid, info in self.process_library.items():
                try:
                    # Combine all logs for this process
                    log_content = "".join(info.get('logs', []))
                    
                    # Calculate duration
                    duration = "N/A"
                    if info['start_time']:
                        if info['end_time']:
                            duration = str(info['end_time'] - info['start_time'])
                        elif info['status'] == 'Running':
                            duration = str(datetime.now() - info['start_time'])
                    
                    # Get dashboard data
                    dashboard_data = info.get('dashboard_data', {
                        'cpu': '--%',
                        'memory': '-- MB',
                        'network': '--',
                        'power': '--'
                    })
                    
                    # Create report content with dashboard information
                    report_content = f"""Auto-Terminator Process Report
==============================
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
PID: {pid}

PROCESS INFORMATION
-------------------
PID: {pid}
Status: {info['status']}
Started: {info['start_time'].strftime('%Y-%m-%d %H:%M:%S') if info['start_time'] else 'Unknown'}
Ended: {info['end_time'].strftime('%Y-%m-%d %H:%M:%S') if info['end_time'] else 'N/A'}
Duration: {duration}
Auto-execute AI: {'Yes' if info['auto_execute'] else 'No'}
Timeout: {info['timeout']} seconds

DASHBOARD INFORMATION
---------------------
CPU Usage: {dashboard_data['cpu']}
Memory Usage: {dashboard_data['memory']}
Network Connections: {dashboard_data['network']}
Power Consumption: {dashboard_data['power']}

LOG CONTENT
-----------
{log_content}
"""
                    
                    # Save report
                    file_path = os.path.join(directory, f"auto_terminator_report_pid_{pid}.txt")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(report_content)
                    reports_generated += 1
                    
                except Exception as e:
                    print(f"Error generating report for PID {pid}: {str(e)}")
                    continue
            
            messagebox.showinfo("Reports Generated", f"Successfully generated {reports_generated} reports in:\n{directory}")
            
            # Close the library window if it was open
            if parent_window:
                parent_window.destroy()
                
        except Exception as e:
            error_msg = f"Error downloading all PID reports: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)

    def on_closing(self):
        self.stop_terminal()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTerminatorManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()