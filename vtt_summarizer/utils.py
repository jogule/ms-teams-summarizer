"""Shared utilities for VTT Summarizer to eliminate code duplication."""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


def parse_folder_name(folder_name: str) -> Dict[str, str]:
    """
    Parse folder name to extract date and topic.
    
    Args:
        folder_name: Name of the folder (e.g., "20250821_mulesoft")
        
    Returns:
        Dictionary with parsed information
    """
    if "_" in folder_name:
        parts = folder_name.split("_", 1)
        if len(parts) == 2:
            date_part, topic_part = parts
            return {
                "date": date_part,
                "topic": topic_part.replace("_", " ").title()
            }
    
    return {"date": None, "topic": folder_name.replace("_", " ").title()}


def extract_summary_info(content: str, folder_name: str) -> Dict[str, Any]:
    """
    Extract key information from a summary.
    
    Args:
        content: Summary content
        folder_name: Name of the folder
        
    Returns:
        Dictionary with extracted information
    """
    # Extract duration
    duration_match = re.search(r'- \*\*Duration\*\*: ([^\n]+)', content)
    duration = duration_match.group(1) if duration_match else "Unknown"
    
    # Extract transcript word count
    words_match = re.search(r'- \*\*Transcript Words\*\*: ([^\n]+)', content)
    transcript_words = words_match.group(1) if words_match else "Unknown"
    
    # Extract participants (simple extraction)
    participants_section = re.search(r'## Participants\s*\n(.*?)\n\n', content, re.DOTALL)
    participants = []
    if participants_section:
        participant_text = participants_section.group(1)
        # Extract names from bullet points
        participant_matches = re.findall(r'- ([^\n]+)', participant_text)
        participants = [p.strip() for p in participant_matches]
    
    # Extract main topics
    topics_section = re.search(r'## Main Topics\s*\n(.*?)\n\n', content, re.DOTALL)
    main_topics = []
    if topics_section:
        topics_text = topics_section.group(1)
        topic_matches = re.findall(r'(?:\d+\.|-)\s*([^\n]+)', topics_text)
        main_topics = [t.strip() for t in topic_matches]
    
    # Extract action items
    action_section = re.search(r'## Action Items\s*\n(.*?)(?:\n\n|\n## |\n---|\nTimeline)', content, re.DOTALL)
    action_items = []
    if action_section:
        action_text = action_section.group(1)
        action_matches = re.findall(r'(?:\d+\.|-)\s*([^\n]+)', action_text)
        action_items = [a.strip() for a in action_matches]
    
    return {
        "duration": duration,
        "transcript_words": transcript_words,
        "participants": participants,
        "main_topics": main_topics,
        "action_items": action_items
    }


def time_to_seconds(time_str: str) -> float:
    """Convert VTT time format to seconds."""
    try:
        # Format: HH:MM:SS.mmm or MM:SS.mmm
        parts = time_str.split(':')
        if len(parts) == 3:  # HH:MM:SS.mmm
            hours, minutes, seconds = parts
            return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        elif len(parts) == 2:  # MM:SS.mmm
            minutes, seconds = parts
            return float(minutes) * 60 + float(seconds)
        else:
            return 0.0
    except (ValueError, IndexError):
        return 0.0


def seconds_to_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def ensure_directory(directory: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        The directory path
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_write_file(file_path: Path, content: str, encoding: str = 'utf-8') -> None:
    """
    Safely write content to a file with error handling.
    
    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding
        
    Raises:
        IOError: If writing fails
    """
    try:
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        raise IOError(f"Failed to write file {file_path}: {str(e)}")


def safe_read_file(file_path: Path, encoding: str = 'utf-8') -> str:
    """
    Safely read content from a file with error handling.
    
    Args:
        file_path: Path to the file
        encoding: File encoding
        
    Returns:
        File content
        
    Raises:
        IOError: If reading fails
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        raise IOError(f"Failed to read file {file_path}: {str(e)}")


def calculate_total_transcript_words(summaries: List[Dict[str, Any]]) -> int:
    """
    Calculate total transcript words from summaries.
    
    Args:
        summaries: List of summary dictionaries
        
    Returns:
        Total word count
    """
    total_words = 0
    for summary in summaries:
        words_str = summary.get('transcript_words', '0')
        words_match = re.search(r'([\d,]+)', str(words_str).replace(',', ''))
        if words_match:
            try:
                total_words += int(words_match.group(1))
            except ValueError:
                continue  # Skip if can't parse
    return total_words


def format_timestamp() -> str:
    """Get formatted timestamp for metadata."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_iso_timestamp() -> str:
    """Get ISO formatted timestamp."""
    return datetime.now().isoformat()


def setup_module_logger(module_name: str, level: str = "INFO") -> logging.Logger:
    """
    Set up a logger for a module with consistent configuration.
    
    Args:
        module_name: Name of the module
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(module_name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Check if logging has been configured globally
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return logger
    
    # Configure logger if needed
    logger.setLevel(getattr(logging, level.upper()))
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


class ProcessingTimer:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name: str = "Operation"):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
    
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def duration_rounded(self) -> float:
        """Get rounded duration in seconds."""
        return round(self.duration_seconds, 2)


def extract_meeting_context(folder_name: str, metadata: Dict) -> str:
    """
    Extract context information about the meeting from folder name and metadata.
    
    Args:
        folder_name: Name of the walkthrough folder
        metadata: VTT metadata dictionary
        
    Returns:
        Formatted meeting context string
    """
    context_parts = []
    
    # Parse folder name for date and topic
    parsed = parse_folder_name(folder_name)
    if parsed["date"]:
        context_parts.append(f"Meeting Date: {parsed['date']}")
        context_parts.append(f"Topic: {parsed['topic']}")
    else:
        context_parts.append(f"Meeting: {parsed['topic']}")
    
    # Add metadata
    context_parts.append(f"Duration: {metadata['duration_formatted']}")
    context_parts.append(f"Transcript Length: {metadata['word_count']} words")
    
    if metadata['estimated_speakers'] > 0:
        context_parts.append(f"Estimated Speakers: {metadata['estimated_speakers']}")
    
    return "\n".join(context_parts)
