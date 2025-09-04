"""VTT file parser for extracting transcript content."""

import re
import webvtt
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from .utils import time_to_seconds, seconds_to_time, setup_module_logger


@dataclass
class TranscriptSegment:
    """Represents a segment of transcript with timestamp and content."""
    start_time: str
    end_time: str
    text: str
    duration_seconds: Optional[float] = None
    original_text: Optional[str] = None  # Preserve original VTT text with speaker info


class VTTParser:
    """Parser for WebVTT transcript files."""
    
    def __init__(self):
        """Initialize VTT parser."""
        self.logger = setup_module_logger(__name__)
    
    def parse_file(self, vtt_path: str) -> List[TranscriptSegment]:
        """
        Parse a VTT file and extract transcript segments.
        
        Args:
            vtt_path: Path to the VTT file
            
        Returns:
            List of TranscriptSegment objects
            
        Raises:
            FileNotFoundError: If VTT file doesn't exist
            ValueError: If VTT file is malformed
        """
        vtt_file = Path(vtt_path)
        if not vtt_file.exists():
            raise FileNotFoundError(f"VTT file not found: {vtt_path}")
        
        try:
            captions = webvtt.read(str(vtt_file))
            segments = []
            
            for caption in captions:
                # Store original text before cleaning
                original_text = caption.text.strip()
                
                # Clean the text content
                clean_text = self._clean_text(caption.text)
                
                if clean_text.strip():  # Only add non-empty segments
                    segment = TranscriptSegment(
                        start_time=caption.start,
                        end_time=caption.end,
                        text=clean_text,
                        duration_seconds=time_to_seconds(caption.end) - 
                                       time_to_seconds(caption.start),
                        original_text=original_text
                    )
                    segments.append(segment)
            
            self.logger.info(f"Parsed {len(segments)} segments from {vtt_file.name}")
            return segments
            
        except Exception as e:
            self.logger.error(f"Error parsing VTT file {vtt_path}: {str(e)}")
            raise ValueError(f"Failed to parse VTT file: {str(e)}")
    
    def extract_full_transcript(self, vtt_path: str) -> str:
        """
        Extract the complete transcript text from a VTT file.
        
        Args:
            vtt_path: Path to the VTT file
            
        Returns:
            Complete transcript as a string
        """
        segments = self.parse_file(vtt_path)
        
        # Combine all text segments
        full_text = " ".join([segment.text for segment in segments if segment.text.strip()])
        
        # Clean up extra whitespace
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        return full_text
    
    def extract_transcript_with_timestamps(self, vtt_path: str, 
                                         timestamp_interval: int = 300) -> str:
        """
        Extract transcript with periodic timestamps for reference.
        
        Args:
            vtt_path: Path to the VTT file
            timestamp_interval: Interval in seconds to add timestamps
            
        Returns:
            Transcript with timestamp markers
        """
        segments = self.parse_file(vtt_path)
        
        result = []
        last_timestamp_seconds = 0
        
        for segment in segments:
            segment_start_seconds = time_to_seconds(segment.start_time)
            
            # Add timestamp marker if enough time has passed
            if segment_start_seconds - last_timestamp_seconds >= timestamp_interval:
                result.append(f"\\n[{segment.start_time}]\\n")
                last_timestamp_seconds = segment_start_seconds
            
            result.append(segment.text)
        
        return " ".join(result)
    
    def get_transcript_metadata(self, vtt_path: str) -> Dict[str, any]:
        """
        Extract metadata about the transcript.
        
        Args:
            vtt_path: Path to the VTT file
            
        Returns:
            Dictionary with transcript metadata
        """
        segments = self.parse_file(vtt_path)
        
        if not segments:
            return {"duration_seconds": 0, "segment_count": 0, "word_count": 0}
        
        total_duration = time_to_seconds(segments[-1].end_time)
        total_words = sum(len(segment.text.split()) for segment in segments)
        
        # Try to identify potential speakers (simple heuristic)
        potential_speakers = self._identify_speakers(segments)
        
        return {
            "duration_seconds": total_duration,
            "duration_formatted": seconds_to_time(total_duration),
            "segment_count": len(segments),
            "word_count": total_words,
            "estimated_speakers": len(potential_speakers),
            "file_path": str(vtt_path)
        }
    
    def _clean_text(self, text: str) -> str:
        """
        Clean VTT text content by removing formatting and artifacts.
        
        Args:
            text: Raw text from VTT
            
        Returns:
            Cleaned text
        """
        # Remove VTT formatting tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove speaker labels if they exist (format: "Speaker: text")
        text = re.sub(r'^[A-Za-z\s]+:\s*', '', text)
        
        # Remove multiple spaces and normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common VTT artifacts
        text = re.sub(r'\[.*?\]', '', text)  # Remove [background noise], etc.
        text = re.sub(r'\(.*?\)', '', text)  # Remove (inaudible), etc.
        
        return text.strip()
    
    
    def _identify_speakers(self, segments: List[TranscriptSegment]) -> List[str]:
        """
        Simple heuristic to identify potential speakers.
        
        Args:
            segments: List of transcript segments
            
        Returns:
            List of potential speaker identifiers
        """
        speakers = set()
        
        for segment in segments:
            # Look for speaker patterns at the beginning of segments
            speaker_match = re.match(r'^([A-Za-z\s]+):\s*', segment.text)
            if speaker_match:
                speakers.add(speaker_match.group(1).strip())
        
        return list(speakers)
