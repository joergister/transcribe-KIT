import os
import glob
import time
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import get_log_dir

console = Console()

def check_all_transcriptions(output_dir: str = None):
    """Check status of all running transcriptions by reading log files."""

    # Use centralized log directory
    if output_dir is None:
        output_dir = str(get_log_dir())

    log_files = glob.glob(f"{output_dir}/transcription_*.log")
    
    if not log_files:
        console.print("[yellow]No transcription log files found[/yellow]")
        return
    
    table = Table(title="Transcription Status")
    table.add_column("Job ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Last Update", style="dim")
    table.add_column("Log File", style="blue")
    
    for log_file in log_files:
        log_path = Path(log_file)
        job_id = log_path.stem.replace("transcription_", "")
        
        try:
            # Read last few lines of log file
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            if lines:
                last_line = lines[-1].strip()
                # Extract timestamp and message
                if "] " in last_line:
                    timestamp = last_line.split("] ")[0][1:]
                    message = last_line.split("] ", 1)[1]
                else:
                    timestamp = "Unknown"
                    message = last_line
                
                # Parse timestamp to check if process is alive
                current_time = time.time()
                try:
                    log_time = time.mktime(time.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))
                    minutes_since_update = (current_time - log_time) / 60
                except ValueError:
                    minutes_since_update = float('inf')  # Unknown timestamp = assume old
                
                # Determine status
                if "completed" in message.lower():
                    status = "✅ Completed"
                elif "failed" in message.lower():
                    status = "❌ Failed"
                elif "timeout" in message.lower():
                    status = "⏰ Timeout"
                elif "monitoring" in message.lower():
                    if minutes_since_update > 3:  # No update for >3 minutes = dead
                        status = "💀 Dead (no updates)"
                    else:
                        status = "🔄 Running"
                else:
                    if minutes_since_update > 3:
                        status = "💀 Dead (stale)"
                    else:
                        status = "❓ Unknown"
                
                table.add_row(job_id, status, timestamp, str(log_path.name))
            else:
                table.add_row(job_id, "❓ Empty log", "Never", str(log_path.name))
                
        except Exception as e:
            table.add_row(job_id, f"❌ Error: {e}", "Error", str(log_path.name))
    
    console.print(table)
    console.print(f"\n[dim]Monitoring log directory: {output_dir}[/dim]")
    console.print("[dim]Use 'tail -f /path/to/transcription_*.log' to follow a specific job[/dim]")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check status of all transcription jobs")
    parser.add_argument("--output-dir", "-o", default=None,
                       help="Directory containing log files (default: ~/.transcribe_kit)")

    args = parser.parse_args()
    check_all_transcriptions(args.output_dir)

if __name__ == "__main__":
    main()