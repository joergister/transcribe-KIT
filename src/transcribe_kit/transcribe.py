import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from typing import Optional
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

# PYTHON_ARGCOMPLETE_OK
try:
    import argcomplete
    ARGCOMPLETE_AVAILABLE = True
except ImportError:
    ARGCOMPLETE_AVAILABLE = False

from .config import get_log_dir
from .check_status import check_all_transcriptions
from .convert import convert_csv_to_txt, convert_vtt_to_txt

console = Console()

API_BASE_URL = "https://diarization-01-hubii.k8s.iism.kit.edu"

SUPPORTED_LANGUAGES = ["en", "fr", "de", "es", "it", "ja", "zh", "nl", "uk", "pt"]
# Officially supported formats: mp3, aac, ogg, mp4, wav, m4a
# API uses FFmpeg and may support additional formats
SUPPORTED_EXTENSIONS = [".mp3", ".aac", ".ogg", ".mp4", ".wav", ".m4a"]

def validate_file(file_path: str) -> Path:
    """Validate that the file exists and has a supported extension."""
    path = Path(file_path)
    
    if not path.exists():
        console.print(f"[red]Error: File '{file_path}' does not exist[/red]")
        sys.exit(1)
    
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        console.print(f"[red]Error: Unsupported file extension '{path.suffix}'[/red]")
        console.print(f"[yellow]Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}[/yellow]")
        sys.exit(1)
    
    return path

def upload_file(file_path: Path, language: str, speakers: int) -> str:
    """Upload file to the diarization API and return job_id."""
    console.print(f"[blue]Uploading {file_path.name} to transcription API...[/blue]")

    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/octet-stream')}
        data = {
            'language': language,
            'speaker': speakers
        }

        # Display API request parameters
        console.print(f"[dim]API Request Parameters:[/dim]")
        console.print(f"[dim]  - Endpoint: {API_BASE_URL}/diarization/[/dim]")
        console.print(f"[dim]  - File: {file_path.name}[/dim]")
        console.print(f"[dim]  - language: {language}[/dim]")
        console.print(f"[dim]  - speaker: {speakers}[/dim]")

        try:
            response = requests.post(
                f"{API_BASE_URL}/diarization/",
                files=files,
                data=data,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            console.print(f"[dim]API Response: {result}[/dim]")
            
            # Handle different possible response formats
            if 'job_id' in result:
                job_id = result['job_id']
            elif 'id' in result:
                job_id = result['id']
            elif 'task_id' in result:
                job_id = result['task_id']
            else:
                console.print(f"[red]Unexpected API response format: {result}[/red]")
                sys.exit(1)
                
            console.print(f"[green]Upload successful! Job ID: {job_id}[/green]")
            return job_id
            
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Upload failed: {e}[/red]")
            if hasattr(e, 'response') and e.response is not None:
                console.print(f"[red]Response status: {e.response.status_code}[/red]")

                # Provide helpful message for file size errors
                if e.response.status_code == 413:
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    console.print(f"\n[yellow]File too large: {file_size_mb:.1f}MB[/yellow]")
                    console.print(f"[yellow]The API has rejected this file because it exceeds the maximum upload size.[/yellow]\n")
                    console.print(f"[blue]Solutions:[/blue]")
                    console.print(f"[blue]1. Compress the file to a lower bitrate:[/blue]")
                    console.print(f'[dim]   ffmpeg -i "{file_path}" -b:a 96k "{file_path.stem}_compressed{file_path.suffix}"[/dim]')
                    console.print(f"[blue]2. Split into smaller segments:[/blue]")
                    console.print(f'[dim]   ffmpeg -i "{file_path}" -f segment -segment_time 1800 -c copy "{file_path.stem}_part_%03d{file_path.suffix}"[/dim]')
                else:
                    console.print(f"[red]Response text: {e.response.text}[/red]")
            sys.exit(1)

def check_status(job_id: str) -> dict:
    """Check the status of a transcription job."""
    try:
        response = requests.get(f"{API_BASE_URL}/diarization/{job_id}/status/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Status check failed: {e}[/red]")
        sys.exit(1)

def launch_background_monitor(job_id: str, output_dir: str) -> None:
    """Launch the monitoring script in the background."""
    log_dir = get_log_dir()

    try:
        # Launch monitor in background by calling Python module directly
        subprocess.Popen([
            sys.executable, "-m", "transcribe_kit.monitor_job",
            job_id,
            "--output-dir", output_dir,
            "--timeout", "10.0"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        console.print(f"[green]✓ Background monitor started for job: {job_id[:8]}[/green]")
        console.print(f"[blue]VTT and CSV files will be saved to: {output_dir}/transcription_{job_id[:8]}.{{vtt,csv}}[/blue]")
        console.print(f"[blue]Log file will be saved to: {log_dir}/transcription_{job_id[:8]}.log[/blue]")
        console.print(f"[blue]You'll receive desktop notifications for success/failure/timeout[/blue]")
        console.print(f"[dim]Monitor timeout: 10 hours | Check frequency: 30 seconds[/dim]")

    except Exception as e:
        console.print(f"[yellow]Warning: Could not start background monitor: {e}[/yellow]")
        console.print(f"[yellow]Check status with: status[/yellow]")

def download_results(job_id: str, output_format: str = "vtt") -> str:
    """Download transcription results."""
    endpoint = f"{API_BASE_URL}/diarization/{job_id}/{output_format}/"
    
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        
        if output_format == "vtt":
            return response.text
        else:  # csv
            return response.text
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Download failed: {e}[/red]")
        sys.exit(1)

def save_results(content: str, output_path: Path, format_type: str) -> None:
    """Save results to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    console.print(f"[green]Results saved to: {output_path}[/green]")

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using KIT's diarization API (https://diarization-01-hubii.k8s.iism.kit.edu)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Commands:
  transcribe status                  Check status of all transcription jobs
  transcribe csv-to-txt <input.csv> <output.txt>
                                     Convert CSV transcription to clean dialogue format
  transcribe vtt-to-txt <input.vtt> <output.txt>
                                     Convert VTT transcription to clean dialogue format
  transcribe <file> [options]        Transcribe an audio/video file

Examples:
  transcribe audio.mp3 --language en --speakers 2
  transcribe interview.wav --language de --speakers 3 --format csv
  transcribe meeting.mp4 --language fr
  transcribe status
  transcribe csv-to-txt transcription_abc123.csv dialogue.txt
  transcribe vtt-to-txt transcription_abc123.vtt dialogue.txt

Supported languages: {', '.join(SUPPORTED_LANGUAGES)}

Supported file formats:
  Officially supported: .mp3, .aac, .ogg, .mp4, .wav, .m4a
  Note: API uses FFmpeg and may support additional formats

API Documentation: https://diarization-01-hubii.k8s.iism.kit.edu/docs
        """
    )

    parser.add_argument(
        "file",
        help="Audio/video file to transcribe, 'status' to check jobs, 'csv-to-txt' or 'vtt-to-txt' to convert"
    )

    parser.add_argument(
        "extra_args",
        nargs="*",
        help="Additional arguments for csv-to-txt/vtt-to-txt: <input> <output.txt>"
    )

    parser.add_argument(
        "--language", "-l",
        choices=SUPPORTED_LANGUAGES,
        default="en",
        help="Language of the audio (default: en)"
    )

    parser.add_argument(
        "--speakers", "-s",
        type=int,
        default=0,
        help="Number of speakers (default: 0)"
    )

    parser.add_argument(
        "--format", "-f",
        choices=["vtt", "csv"],
        default="vtt",
        help="Output format (default: vtt)"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: input_filename.{format})"
    )

    parser.add_argument(
        "--output-dir",
        help="Directory containing log files (only for 'status' subcommand)"
    )

    # Enable tab completion
    if ARGCOMPLETE_AVAILABLE:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Check if user wants to see status
    if args.file.lower() == "status":
        check_all_transcriptions(args.output_dir)
        return

    # Check if user wants to convert CSV to text
    if args.file.lower() == "csv-to-txt":
        if len(args.extra_args) != 2:
            console.print("[red]Error: csv-to-txt requires <input.csv> <output.txt>[/red]")
            console.print("[yellow]Usage: transcribe csv-to-txt <input.csv> <output.txt>[/yellow]")
            sys.exit(1)

        input_csv = Path(args.extra_args[0])
        output_txt = Path(args.extra_args[1])

        if not input_csv.exists():
            console.print(f"[red]Error: Input file '{input_csv}' not found[/red]")
            sys.exit(1)

        convert_csv_to_txt(str(input_csv), str(output_txt))
        console.print(f"[green]✓ Converted {input_csv} -> {output_txt}[/green]")
        return

    # Check if user wants to convert VTT to text
    if args.file.lower() == "vtt-to-txt":
        if len(args.extra_args) != 2:
            console.print("[red]Error: vtt-to-txt requires <input.vtt> <output.txt>[/red]")
            console.print("[yellow]Usage: transcribe vtt-to-txt <input.vtt> <output.txt>[/yellow]")
            sys.exit(1)

        input_vtt = Path(args.extra_args[0])
        output_txt = Path(args.extra_args[1])

        if not input_vtt.exists():
            console.print(f"[red]Error: Input file '{input_vtt}' not found[/red]")
            sys.exit(1)

        convert_vtt_to_txt(str(input_vtt), str(output_txt))
        console.print(f"[green]✓ Converted {input_vtt} -> {output_txt}[/green]")
        return

    # Validate input file
    file_path = validate_file(args.file)

    # Set output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = file_path.with_suffix(f".{args.format}")

    # Display job information
    console.print(Panel(
        f"[bold]Transcription Job[/bold]\n"
        f"File: {file_path.name}\n"
        f"Language: {args.language}\n"
        f"Speakers: {args.speakers}\n"
        f"Output formats: VTT and CSV (both will be downloaded)\n"
        f"Output directory: {output_path.parent}",
        title="Job Configuration"
    ))

    # Start transcription process
    job_id = upload_file(file_path, args.language, args.speakers)

    # Launch background monitor
    launch_background_monitor(job_id, str(output_path.parent))

    console.print(f"[green]✓ Transcription job submitted![/green]")
    console.print(f"[blue]Job ID: {job_id}[/blue]")
    console.print(f"[dim]Results will be automatically saved when ready[/dim]")

if __name__ == "__main__":
    main()