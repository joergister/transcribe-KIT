"""Convert CSV and VTT transcription files to clean dialogue format."""

import csv
import re
import sys
from pathlib import Path


def clean_text(text: str) -> str:
    """Remove quotation marks and extra whitespace from text."""
    # Remove leading/trailing whitespace
    text = text.strip()
    # Remove surrounding quotes if present
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    # Clean up any extra whitespace
    text = ' '.join(text.split())
    return text


def convert_csv_to_txt(input_file: str, output_file: str) -> None:
    """Convert CSV transcription to dialogue format."""
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        current_speaker = None
        current_text = []
        output_lines = []

        for row in reader:
            speaker = row['speaker'].strip()
            text = clean_text(row['text'])

            # Skip empty text or empty speaker entries
            if not text or not speaker:
                continue

            # If same speaker, accumulate text
            if speaker == current_speaker:
                current_text.append(text)
            else:
                # Write previous speaker's block if exists
                if current_speaker is not None and current_text:
                    combined_text = ' '.join(current_text)
                    output_lines.append(f"{current_speaker}: {combined_text}\n")

                # Start new speaker block
                current_speaker = speaker
                current_text = [text]

        # Write the last speaker's block
        if current_speaker is not None and current_text:
            combined_text = ' '.join(current_text)
            output_lines.append(f"{current_speaker}: {combined_text}\n")

    # Write to output file with blank lines between speakers
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))


def convert_vtt_to_txt(input_file: str, output_file: str) -> None:
    """Convert VTT transcription to dialogue format.

    Parses VTT files with speaker tags and combines consecutive segments
    from the same speaker into a clean dialogue format.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_speaker = None
    current_text = []
    output_lines = []

    i = 0
    # Skip WEBVTT header and any metadata
    while i < len(lines) and '-->' not in lines[i]:
        i += 1

    # Parse VTT cues
    while i < len(lines):
        line = lines[i].strip()

        # Check if this is a timestamp line
        if '-->' in line:
            i += 1

            # Collect all text lines until we hit an empty line or end of file
            cue_text = ''
            while i < len(lines) and lines[i].strip() != '':
                cue_text += lines[i].strip() + ' '
                i += 1

            cue_text = cue_text.strip()

            # Parse speaker from <v Speaker> tag
            speaker = None
            text = cue_text

            # Match <v SPEAKER_XX> pattern
            speaker_match = re.match(r'<v\s+([^>]+)>\s*(.*)', cue_text)
            if speaker_match:
                speaker = speaker_match.group(1).strip()
                text = speaker_match.group(2).strip()

            # Skip empty text
            if not text:
                i += 1
                continue

            # If we don't have a speaker tag, use "UNKNOWN"
            if not speaker:
                speaker = "UNKNOWN"

            # If same speaker, accumulate text
            if speaker == current_speaker:
                current_text.append(text)
            else:
                # Write previous speaker's block if exists
                if current_speaker is not None and current_text:
                    combined_text = ' '.join(current_text)
                    output_lines.append(f"{current_speaker}: {combined_text}\n")

                # Start new speaker block
                current_speaker = speaker
                current_text = [text]

        i += 1

    # Write the last speaker's block
    if current_speaker is not None and current_text:
        combined_text = ' '.join(current_text)
        output_lines.append(f"{current_speaker}: {combined_text}\n")

    # Write to output file with blank lines between speakers
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))


def main():
    if len(sys.argv) != 3:
        print("Usage: uv run convert_transcription.py <input.csv> <output.txt>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)

    convert_transcription(input_file, output_file)
    print(f"Converted {input_file} -> {output_file}")


if __name__ == "__main__":
    main()
