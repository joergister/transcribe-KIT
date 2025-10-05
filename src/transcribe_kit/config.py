"""Centralized configuration for transcribe_kit."""

import os
from pathlib import Path

def get_log_dir() -> Path:
    """Get the centralized log directory for transcription jobs.

    Returns:
        Path to the log directory (creates it if it doesn't exist)
    """
    # Use user's home directory for cross-platform compatibility
    log_dir = Path.home() / ".transcribe_kit"
    log_dir.mkdir(exist_ok=True)
    return log_dir
