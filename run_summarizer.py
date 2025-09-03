#!/usr/bin/env python3
"""
VTT Summarizer Runner Script

This script provides an easy way to run the VTT Summarizer CLI application.
"""

import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from vtt_summarizer.main import cli

if __name__ == '__main__':
    cli()
