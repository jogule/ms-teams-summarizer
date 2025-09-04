"""File writer for creating meeting summaries and analysis documents."""

from pathlib import Path
from typing import Dict, List, Any, Optional

from .utils import (
    safe_write_file, 
    format_timestamp, 
    calculate_total_transcript_words
)
from .video_processor import ExtractedKeyframe


class FileWriter:
    """Handles writing meeting summaries and analysis files."""
    
    def write_individual_summary(self, summary_path: Path, summary: str, 
                                metadata: Dict, folder_name: str,
                                video_screenshots: Optional[List[ExtractedKeyframe]] = None) -> None:
        """
        Write an individual meeting summary to a markdown file.
        
        Args:
            summary_path: Path where to save the summary
            summary: Generated summary text
            metadata: VTT metadata
            folder_name: Name of the meeting folder
            video_screenshots: Optional list of extracted video screenshots to embed
        """
        content_parts = [
            f"# {folder_name.replace('_', ' ').title()} - Meeting Summary\n",
            "## Meeting Information\n",
            f"- **Date Generated**: {format_timestamp()}",
            f"- **Duration**: {metadata['duration_formatted']}",
            f"- **Transcript Words**: {metadata['word_count']:,}",
            f"- **Source File**: {Path(metadata['file_path']).name}\n"
        ]
        
        # Add video screenshots section if available
        if video_screenshots:
            content_parts.extend([
                "## Meeting Screenshots\n",
                self._generate_screenshots_section(video_screenshots),
                ""
            ])
        
        content_parts.extend([
            "## Summary\n",
            summary
        ])
        
        content = "\n".join(content_parts)
        safe_write_file(summary_path, content)
    
    def _generate_screenshots_section(self, video_screenshots: List[ExtractedKeyframe]) -> str:
        """
        Generate markdown content for video screenshots section.
        
        Args:
            video_screenshots: List of extracted video screenshots
            
        Returns:
            Formatted markdown content for video screenshots
        """
        screenshot_parts = []
        
        screenshot_parts.append("*Key visual moments from the meeting:*\n")
        
        for i, frame in enumerate(video_screenshots, 1):
            # Get relative path for the image (assuming images are in images/ subdirectory)
            image_filename = Path(frame.image_path).name
            image_relative_path = f"images/{image_filename}"
            
            # Format timestamp for display
            timestamp_display = f"At {frame.timestamp_formatted}"
            
            # Create markdown for this screenshot
            screenshot_parts.extend([
                f"### Screenshot {i}: {timestamp_display}\n",
                f"![{timestamp_display}]({image_relative_path})\n",
                f"*Context: {frame.context_text.strip()}*\n"
            ])
        
        return "\n".join(screenshot_parts)
    
    def write_global_summary(self, global_analysis_path: Path, content: str, 
                            summaries: List[Dict]) -> None:
        """
        Write a global meeting analysis file.
        
        Args:
            global_analysis_path: Path where to save the global analysis
            content: Generated analysis content
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
        safe_write_file(global_analysis_path, final_content)
