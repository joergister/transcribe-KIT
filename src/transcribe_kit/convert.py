"""Convert CSV and VTT transcription files to clean dialogue format, markdown, and PDF."""

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


def txt_to_markdown(input_file: str, output_file: str, highlight_speaker: str = "INTERVIEWER") -> None:
    """Convert text dialogue format to markdown with highlighted speaker.
    
    Args:
        input_file: Path to input text file with dialogue format (SPEAKER: text)
        output_file: Path to output markdown file
        highlight_speaker: Speaker name to highlight (default: "INTERVIEWER")
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    markdown_lines = []
    markdown_lines.append("# Interview Transcript\n\n")
    markdown_lines.append("<!-- Use ==HIGHLIGHT==text==HIGHLIGHT== to mark text for highlighting in PDF -->\n\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse speaker and text
        if ':' in line:
            parts = line.split(':', 1)
            speaker = parts[0].strip()
            text = parts[1].strip()
            
            # Check if this speaker should be highlighted
            if speaker.upper() == highlight_speaker.upper():
                markdown_lines.append(f"\n==HIGHLIGHT==**{speaker}:** {text}==HIGHLIGHT==\n")
            else:
                markdown_lines.append(f"\n**{speaker}:** {text}\n")
        else:
            # Line without speaker (continuation or other content)
            markdown_lines.append(f"{line}\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(markdown_lines)


def vtt_to_markdown(input_file: str, output_file: str, highlight_speaker: str = "INTERVIEWER") -> None:
    """Convert VTT transcription to markdown with highlighted speaker.
    
    Args:
        input_file: Path to input VTT file
        output_file: Path to output markdown file
        highlight_speaker: Speaker name to highlight (default: "INTERVIEWER")
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_speaker = None
    current_text = []
    markdown_lines = []
    markdown_lines.append("# Interview Transcript\n\n")
    markdown_lines.append("<!-- Use ==HIGHLIGHT==text==HIGHLIGHT== to mark text for highlighting in PDF -->\n\n")

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
                    # Check if speaker should be highlighted
                    if current_speaker.upper() == highlight_speaker.upper():
                        markdown_lines.append(f"\n==HIGHLIGHT==**{current_speaker}:** {combined_text}==HIGHLIGHT==\n")
                    else:
                        markdown_lines.append(f"\n**{current_speaker}:** {combined_text}\n")

                # Start new speaker block
                current_speaker = speaker
                current_text = [text]

        i += 1

    # Write the last speaker's block
    if current_speaker is not None and current_text:
        combined_text = ' '.join(current_text)
        if current_speaker.upper() == highlight_speaker.upper():
            markdown_lines.append(f"\n==HIGHLIGHT==**{current_speaker}:** {combined_text}==HIGHLIGHT==\n")
        else:
            markdown_lines.append(f"\n**{current_speaker}:** {combined_text}\n")

    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(markdown_lines)


def csv_to_markdown(input_file: str, output_file: str, highlight_speaker: str = "INTERVIEWER") -> None:
    """Convert CSV transcription to markdown with highlighted speaker.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output markdown file
        highlight_speaker: Speaker name to highlight (default: "INTERVIEWER")
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        current_speaker = None
        current_text = []
        markdown_lines = []
        markdown_lines.append("# Interview Transcript\n\n")
        markdown_lines.append("<!-- Use ==HIGHLIGHT==text==HIGHLIGHT== to mark text for highlighting in PDF -->\n\n")

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
                    # Check if speaker should be highlighted
                    if current_speaker.upper() == highlight_speaker.upper():
                        markdown_lines.append(f"\n==HIGHLIGHT==**{current_speaker}:** {combined_text}==HIGHLIGHT==\n")
                    else:
                        markdown_lines.append(f"\n**{current_speaker}:** {combined_text}\n")

                # Start new speaker block
                current_speaker = speaker
                current_text = [text]

        # Write the last speaker's block
        if current_speaker is not None and current_text:
            combined_text = ' '.join(current_text)
            if current_speaker.upper() == highlight_speaker.upper():
                markdown_lines.append(f"\n==HIGHLIGHT==**{current_speaker}:** {combined_text}==HIGHLIGHT==\n")
            else:
                markdown_lines.append(f"\n**{current_speaker}:** {combined_text}\n")

    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(markdown_lines)


def markdown_to_pdf(input_file: str, output_file: str) -> None:
    """Convert markdown file to PDF with support for ==HIGHLIGHT== markers.
    
    Text wrapped in ==HIGHLIGHT== markers will be highlighted with a yellow background
    in the PDF output.
    
    Args:
        input_file: Path to the input markdown file
        output_file: Path to the output PDF file
    """
    try:
        import markdown
        from weasyprint import HTML, CSS
        
        # Read markdown file
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert ==HIGHLIGHT== markers to HTML <span> tags before processing
        md_content = re.sub(
            r'==HIGHLIGHT==(.*?)==HIGHLIGHT==',
            r'<span class="highlight">\1</span>',
            md_content,
            flags=re.DOTALL
        )
        
        # Convert markdown to HTML
        html_content = markdown.markdown(md_content, extensions=['extra', 'nl2br'])
        
        # Add CSS styling for better PDF appearance with highlight support
        css = CSS(string='''
            @page {
                margin: 2cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 10pt;
                line-height: 1.4;
                color: #333;
            }
            .highlight {
                background-color: #ffeb3b;
                padding: 2px 4px;
                border-radius: 2px;
            }
            strong {
                color: #000;
                font-weight: 600;
            }
            h1 {
                font-size: 16pt;
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 8px;
                margin-top: 0;
                margin-bottom: 12pt;
            }
            p {
                margin: 6px 0;
                font-size: 10pt;
            }
        ''')
        
        # Create HTML with proper structure
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Interview Transcript</title>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Convert to PDF
        HTML(string=full_html).write_pdf(output_file, stylesheets=[css])
        
    except ImportError as e:
        raise ImportError(
            f"Required libraries not installed: {e}\n"
            "This should not happen with a normal installation. Try reinstalling: uv tool install --force transcribe-KIT"
        )


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
