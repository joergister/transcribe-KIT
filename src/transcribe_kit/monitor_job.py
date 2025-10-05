import os
import time
import argparse
import sys
import subprocess
from pathlib import Path
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_log_dir

console = Console()
API_BASE_URL = "https://diarization-01-hubii.k8s.iism.kit.edu"

def send_notification(title: str, message: str) -> None:
    """Send desktop notification on macOS."""
    try:
        subprocess.run([
            "osascript", "-e", 
            f'display notification "{message}" with title "{title}"'
        ], check=False, capture_output=True)
    except Exception:
        pass  # Notifications are optional

def log_message(log_file: Path, message: str) -> None:
    """Write message to log file with timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Logging is optional

def monitor_and_download(job_id: str, output_dir: str = None, timeout_hours: float = 10.0):
    """Monitor job status and download results when ready."""

    # Use Downloads folder as default output directory
    if output_dir is None:
        output_dir = str(Path.home() / "Downloads")

    start_time = time.time()
    timeout_seconds = timeout_hours * 3600

    # Store log file in centralized location
    log_dir = get_log_dir()
    log_file = log_dir / f"transcription_{job_id[:8]}.log"
    
    # Log start with PID for tracking
    pid = os.getpid()
    log_message(log_file, f"Started monitoring job {job_id} (PID: {pid})")
    send_notification("Transcription Monitor", f"Started monitoring job {job_id[:8]}...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Monitoring job {job_id} (timeout: {timeout_hours}h)...", total=None)
        
        while True:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                timeout_msg = f"Timeout reached after {timeout_hours} hours. Job {job_id[:8]} may still be processing."
                console.print(f"[yellow]{timeout_msg}[/yellow]")
                console.print(f"[yellow]You can check status manually: curl -s {API_BASE_URL}/diarization/{job_id}/status/[/yellow]")
                log_message(log_file, timeout_msg)
                send_notification("Transcription Timeout", f"Job {job_id[:8]} timed out after {timeout_hours}h")
                return
            
            try:
                # Check status
                status_response = requests.get(f"{API_BASE_URL}/diarization/{job_id}/status/")
                status_response.raise_for_status()
                status = status_response.json()
                
                remaining_hours = (timeout_seconds - elapsed_time) / 3600
                status_msg = f"Status: {status.get('task_status', 'UNKNOWN')} | Remaining: {remaining_hours:.1f}h"
                console.print(f"[dim]{status_msg}[/dim]")
                
                # Log status every minute (2 checks * 30 seconds = 1 minute)
                if elapsed_time % 60 < 30:  # Log approximately every minute
                    log_message(log_file, f"Still monitoring - {status_msg}")
                
                if status.get('task_status') == 'SUCCESS' or status.get('status') == 'completed':
                    progress.update(task, description="[green]Job completed! Downloading results...[/green]")
                    log_message(log_file, "Job completed successfully")
                    break
                elif status.get('task_status') == 'FAILURE' or status.get('status') == 'failed':
                    failure_msg = f"Job {job_id[:8]} failed: {status}"
                    console.print(f"[red]{failure_msg}[/red]")
                    log_message(log_file, failure_msg)
                    send_notification("Transcription Failed", f"Job {job_id[:8]} failed")
                    return
                
                time.sleep(30)  # Check every 30 seconds
                
            except requests.exceptions.RequestException as e:
                console.print(f"[red]Error checking status: {e}[/red]")
                time.sleep(60)  # Wait longer on error
    
    # Download results
    downloaded_files = []
    
    # Download VTT
    try:
        console.print("[blue]Downloading VTT file...[/blue]")
        vtt_response = requests.get(f"{API_BASE_URL}/diarization/{job_id}/vtt/")
        vtt_response.raise_for_status()
        
        vtt_path = Path(output_dir) / f"transcription_{job_id[:8]}.vtt"
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write(vtt_response.text)
        console.print(f"[green]VTT saved to: {vtt_path}[/green]")
        log_message(log_file, f"VTT file saved: {vtt_path}")
        downloaded_files.append("VTT")
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error downloading VTT: {e}"
        console.print(f"[red]{error_msg}[/red]")
        log_message(log_file, error_msg)
    
    # Download CSV
    try:
        console.print("[blue]Downloading CSV file...[/blue]")
        csv_response = requests.get(f"{API_BASE_URL}/diarization/{job_id}/csv/")
        csv_response.raise_for_status()
        
        csv_path = Path(output_dir) / f"transcription_{job_id[:8]}.csv"
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_response.text)
        console.print(f"[green]CSV saved to: {csv_path}[/green]")
        log_message(log_file, f"CSV file saved: {csv_path}")
        downloaded_files.append("CSV")
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error downloading CSV: {e}"
        console.print(f"[red]{error_msg}[/red]")
        log_message(log_file, error_msg)
    
    # Final notification
    if downloaded_files:
        success_msg = f"Job {job_id[:8]} completed! Downloaded: {', '.join(downloaded_files)}"
        log_message(log_file, success_msg)
        send_notification("Transcription Complete!", f"Job {job_id[:8]} - {', '.join(downloaded_files)} ready")
    else:
        failure_msg = f"Job {job_id[:8]} completed but failed to download results"
        log_message(log_file, failure_msg)
        send_notification("Download Failed", f"Job {job_id[:8]} - Could not download results")

def main():
    parser = argparse.ArgumentParser(description="Monitor transcription job and download results")
    parser.add_argument("job_id", help="The job ID to monitor")
    parser.add_argument("--output-dir", "-o", default=None,
                       help="Output directory for results (default: ~/Downloads)")
    parser.add_argument("--timeout", "-t", type=float, default=10.0,
                       help="Timeout in hours (default: 10.0)")
    
    args = parser.parse_args()
    
    console.print(f"[blue]Starting monitoring for job: {args.job_id}[/blue]")
    console.print(f"[blue]Output directory: {args.output_dir}[/blue]")
    console.print(f"[blue]Timeout: {args.timeout} hours[/blue]")
    
    monitor_and_download(args.job_id, args.output_dir, args.timeout)

if __name__ == "__main__":
    main()