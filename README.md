# transcribe-KIT

A simple CLI tool for transcribing audio and video files using KIT's diarization API. Automatically monitors jobs in the background and sends desktop notifications when complete.

**API Documentation:**
- API Endpoints: https://diarization-01-hubii.k8s.iism.kit.edu/docs
- OpenAPI Spec: https://diarization-01-hubii.k8s.iism.kit.edu/openapi.json
- Provided by: [Wirtschaftsinformatik und Informationsmanagement (WIN)](https://www.win.kit.edu/), KIT

## Features

- <� Transcribe audio/video files with speaker diarization
- = Background monitoring with automatic result downloads
- =� Easy status checking for all jobs
- = Desktop notifications (macOS)
- =� Supports multiple output formats (VTT, CSV)
- < Multi-language support (EN, FR, DE, ES, IT, JA, ZH, NL, UK, PT)

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Installing uv

If you don't have uv installed yet:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Installation

Install transcribe-KIT globally using uv:

```bash
uv tool install git+https://github.com/joergister/transcribe-KIT.git
```

Or install from a local clone:

```bash
git clone https://github.com/joergister/transcribe-KIT.git
cd transcribe-KIT
uv tool install -e .
```

## Usage

### Transcribe an audio file

```bash
transcribe audio.mp3
```

### With options

```bash
# Specify language and number of speakers
transcribe interview.wav --language de --speakers 2

# Choose output format
transcribe meeting.mp4 --format csv

# Custom output location
transcribe podcast.mp3 --output ~/Documents/transcript.vtt
```

### Check status of all jobs

```bash
transcribe status
```

## Available Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--language` | `-l` | Audio language (en, fr, de, es, it, ja, zh, nl, uk, pt) | `en` |
| `--speakers` | `-s` | Number of speakers (0 for default behavior) | `0` |
| `--format` | `-f` | Output format (vtt, csv) | `vtt` |
| `--output` | `-o` | Custom output file path | Same as input file |

## Supported File Formats

- `.mp3`
- `.aac`
- `.ogg`
- `.mp4`
- `.wav`
- `.m4a`

## How it Works

1. **Upload**: The tool uploads your audio/video file to KIT's diarization API
2. **Monitor**: A background process monitors the transcription job every 30 seconds
3. **Download**: When complete, results are automatically downloaded in both VTT and CSV formats
4. **Notify**: You receive a desktop notification when the job completes (or fails)

### File Locations

- **Transcription results**: Saved in the same directory as your input file
  - Example: `audio.mp3` � `transcription_39bc9ffa.vtt` and `transcription_39bc9ffa.csv`
- **Log files**: Stored in `~/.transcribe_kit/`
  - Example: `~/.transcribe_kit/transcription_39bc9ffa.log`

## Examples

```bash
# Basic transcription (English, auto-detect speakers)
transcribe lecture.mp3

# German interview with 2 speakers
transcribe interview.wav --language de --speakers 2

# French meeting, save as CSV
transcribe meeting.mp4 --language fr --format csv --speakers 3

# Check status of all running jobs
transcribe status
```

## Troubleshooting

### Command not found

After installation, you may need to restart your terminal or run:

```bash
# Add uv tools to your PATH
uv tool update-shell
```

Then restart your terminal.

### Check job status

If you're unsure whether your job is still running:

```bash
transcribe status
```

This shows all jobs with their current status (Running, Completed, Failed, etc.)

### View detailed logs

```bash
# List log files
ls ~/.transcribe_kit/

# Follow a specific job's log
tail -f ~/.transcribe_kit/transcription_JOBID.log
```

## Updating

To update to the latest version:

```bash
uv tool upgrade transcribe-KIT
```

## Uninstalling

```bash
uv tool uninstall transcribe-KIT
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this tool for your studies!

## Support

If you encounter any issues, please [open an issue](https://github.com/joergister/transcribe-KIT/issues) on GitHub.
