"""Specialized file writer for summary files to eliminate duplication."""

from pathlib import Path
from typing import Dict, List, Any, Optional

from .utils import (
    safe_write_file, 
    format_timestamp, 
    calculate_total_transcript_words
)
from .keyframe_extractor import ExtractedKeyframe


class SummaryWriter:
    """Handles writing both individual and global summary files."""
    
    def write_individual_summary(self, summary_path: Path, summary: str, 
                                metadata: Dict, folder_name: str,
                                keyframes: Optional[List[ExtractedKeyframe]] = None) -> None:
        """
        Write an individual meeting summary to a markdown file.
        
        Args:
            summary_path: Path where to save the summary
            summary: Generated summary text
            metadata: VTT metadata
            folder_name: Name of the walkthrough folder
            keyframes: Optional list of extracted keyframes to embed
        """
        content_parts = [
            f"# {folder_name.replace('_', ' ').title()} - Meeting Summary\n",
            "## Meeting Information\n",
            f"- **Date Generated**: {format_timestamp()}",
            f"- **Duration**: {metadata['duration_formatted']}",
            f"- **Transcript Words**: {metadata['word_count']:,}",
            f"- **Source File**: {Path(metadata['file_path']).name}\n"
        ]
        
        # Add keyframes section if available
        if keyframes:
            content_parts.extend([
                "## Meeting Screenshots\n",
                self._generate_keyframes_section(keyframes),
                ""
            ])
        
        content_parts.extend([
            "## Summary\n",
            summary
        ])
        
        content = "\n".join(content_parts)
        safe_write_file(summary_path, content)
    
    def _generate_keyframes_section(self, keyframes: List[ExtractedKeyframe]) -> str:
        """
        Generate markdown content for keyframes section.
        
        Args:
            keyframes: List of extracted keyframes
            
        Returns:
            Formatted markdown content for keyframes
        """
        keyframe_parts = []
        
        keyframe_parts.append("*Key visual moments from the meeting:*\n")
        
        for i, frame in enumerate(keyframes, 1):
            # Get relative path for the image (assuming images are in images/ subdirectory)
            image_filename = Path(frame.image_path).name
            image_relative_path = f"images/{image_filename}"
            
            # Format timestamp for display
            timestamp_display = f"At {frame.timestamp_formatted}"
            
            # Create markdown for this keyframe
            keyframe_parts.extend([
                f"### Screenshot {i}: {timestamp_display}\n",
                f"![{timestamp_display}]({image_relative_path})\n",
                f"*Context: {frame.context_text.strip()}*\n"
            ])
        
        return "\n".join(keyframe_parts)
    
    def write_global_summary(self, global_summary_path: Path, content: str, 
                           summaries: List[Dict]) -> None:
        """
        Write a global summary file.
        
        Args:
            global_summary_path: Path where to save the global summary
            content: Generated summary content
            summaries: List of individual summaries for metadata
        """
        # Calculate metadata
        total_transcript_words = calculate_total_transcript_words(summaries)
        meeting_topics = [s.get('meeting_topic', 'Unknown') for s in summaries]
        
        # Get date range
        dates = [s.get('meeting_date') for s in summaries if s.get('meeting_date')]
        date_range_text = ""
        if dates:
            date_range_text = f"- **Date Range**: {min(dates)} to {max(dates)}\n"
        
        content_parts = [
            "# Global Walkthrough Series Summary\n",
            "## Series Information\n",
            f"- **Date Generated**: {format_timestamp()}",
            f"- **Total Meetings**: {len(summaries)}",
            f"- **Total Transcript Words Analyzed**: {total_transcript_words:,}",
            f"- **Meeting Topics**: {', '.join(meeting_topics)}",
            date_range_text,
            "## Analysis\n",
            content
        ]
        
        # Filter out empty parts and join
        final_content = "\n".join(part for part in content_parts if part.strip())
        safe_write_file(global_summary_path, final_content)
