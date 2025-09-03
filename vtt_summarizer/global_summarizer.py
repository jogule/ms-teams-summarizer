"""Global summary aggregation module for creating master summaries from individual meeting summaries."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re

from .config import Config
from .bedrock_client import BedrockClient


class GlobalSummarizer:
    """Creates global summaries from individual meeting summaries."""
    
    def __init__(self, config: Config):
        """
        Initialize the Global Summarizer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.bedrock_client = BedrockClient(config)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Global Summarizer initialized")
    
    def generate_global_summary(self, output_filename: str = "GLOBAL_SUMMARY.md") -> Dict[str, any]:
        """
        Generate a global summary from all individual meeting summaries.
        
        Args:
            output_filename: Name for the global summary file
            
        Returns:
            Dictionary with generation results
        """
        walkthroughs_path = Path(self.config.input_folder)
        global_summary_path = walkthroughs_path / output_filename
        
        if not walkthroughs_path.exists():
            raise FileNotFoundError(f"Walkthroughs directory not found: {walkthroughs_path}")
        
        # Collect all individual summaries
        summaries = self._collect_summaries(walkthroughs_path)
        
        if not summaries:
            self.logger.warning("No individual summaries found")
            return {"status": "no_summaries", "message": "No individual summaries to aggregate"}
        
        self.logger.info(f"Found {len(summaries)} individual summaries to aggregate")
        
        # Generate global summary content
        try:
            self.logger.info("Generating global summary with Claude...")
            start_time = datetime.now()
            
            global_content = self._generate_global_content(summaries)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Global summary generation completed in {generation_time:.2f}s")
            
            # Save global summary
            self._save_global_summary(global_summary_path, global_content, summaries)
            
            return {
                "status": "success",
                "global_summary_path": str(global_summary_path),
                "summaries_processed": len(summaries),
                "generation_time": round(generation_time, 2),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating global summary: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _collect_summaries(self, walkthroughs_path: Path) -> List[Dict[str, any]]:
        """
        Collect all individual summary files.
        
        Args:
            walkthroughs_path: Path to walkthroughs directory
            
        Returns:
            List of summary information dictionaries
        """
        summaries = []
        
        for folder in walkthroughs_path.iterdir():
            if not folder.is_dir():
                continue
                
            summary_path = folder / self.config.output_filename
            
            if summary_path.exists():
                try:
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract meeting date and topic from folder name
                    meeting_info = self._parse_folder_name(folder.name)
                    
                    # Extract key information from summary
                    summary_data = self._extract_summary_info(content, folder.name)
                    
                    summaries.append({
                        "folder_name": folder.name,
                        "meeting_date": meeting_info.get("date"),
                        "meeting_topic": meeting_info.get("topic"),
                        "summary_path": str(summary_path),
                        "content": content,
                        "word_count": len(content.split()),
                        **summary_data
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Could not read summary from {folder.name}: {str(e)}")
                    continue
        
        # Sort by date if available, otherwise by folder name
        summaries.sort(key=lambda x: x.get("meeting_date") or x["folder_name"])
        
        return summaries
    
    def _parse_folder_name(self, folder_name: str) -> Dict[str, str]:
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
    
    def _extract_summary_info(self, content: str, folder_name: str) -> Dict[str, any]:
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
            topic_matches = re.findall(r'(?:\d+\.|-)([^\n]+)', topics_text)
            main_topics = [t.strip() for t in topic_matches]
        
        # Extract action items
        action_section = re.search(r'## Action Items\s*\n(.*?)(?:\n\n|\n## |\n---|\nTimeline)', content, re.DOTALL)
        action_items = []
        if action_section:
            action_text = action_section.group(1)
            action_matches = re.findall(r'(?:\d+\.|-)([^\n]+)', action_text)
            action_items = [a.strip() for a in action_matches]
        
        return {
            "duration": duration,
            "transcript_words": transcript_words,
            "participants": participants,
            "main_topics": main_topics,
            "action_items": action_items
        }
    
    def _generate_global_content(self, summaries: List[Dict]) -> str:
        """
        Generate global summary content using Claude.
        
        Args:
            summaries: List of individual summary data
            
        Returns:
            Generated global summary content
        """
        # Build the prompt for global summary
        prompt = self._build_global_summary_prompt(summaries)
        
        # Use Claude to generate the global summary
        return self.bedrock_client.generate_summary(prompt, "Global Walkthrough Series Analysis")
    
    def _build_global_summary_prompt(self, summaries: List[Dict]) -> str:
        """
        Build the prompt for global summary generation.
        
        Args:
            summaries: List of individual summary data
            
        Returns:
            Formatted prompt string
        """
        # Create overview of all meetings
        meetings_overview = []
        for i, summary in enumerate(summaries, 1):
            overview = f"{i}. **{summary['meeting_topic']}** ({summary.get('meeting_date', 'Date unknown')})"
            overview += f"\n   - Duration: {summary['duration']}"
            overview += f"\n   - Participants: {len(summary.get('participants', []))} people"
            overview += f"\n   - Key Topics: {len(summary.get('main_topics', []))} main areas"
            meetings_overview.append(overview)
        
        # Combine all summary contents for analysis
        combined_summaries = "\n\n" + "="*80 + "\n\n".join([
            f"MEETING: {summary['meeting_topic']} ({summary.get('meeting_date', 'Unknown date')})\n" + 
            summary['content'] for summary in summaries
        ])
        
        prompt_parts = [
            "Please analyze the following series of technical walkthrough meetings and create a comprehensive global summary.",
            "",
            "You should provide:",
            "- **Executive Summary**: High-level overview of the entire walkthrough series",
            "- **Meeting Series Overview**: List of all meetings with key details",
            "- **Cross-Meeting Themes**: Common themes and patterns across all sessions",
            "- **Technical Architecture Overview**: Overall technical landscape discussed",
            "- **Key Stakeholders**: People involved across multiple sessions",
            "- **Strategic Initiatives**: Major projects and initiatives identified",
            "- **Technology Stack**: Technologies, platforms, and tools discussed",
            "- **Migration & Transformation**: Any migration or modernization efforts",
            "- **Outstanding Issues**: Common problems and challenges across meetings",
            "- **Action Items Summary**: Consolidated action items and next steps",
            "- **Recommendations**: Strategic recommendations based on all meetings",
            "",
            "Format the output in clear Markdown with appropriate headers and bullet points.",
            "Focus on strategic insights and cross-meeting connections rather than individual meeting details.",
            "",
            f"**Meeting Series Overview:**",
            *meetings_overview,
            "",
            "**Individual Meeting Summaries for Analysis:**",
            combined_summaries
        ]
        
        return "\n".join(prompt_parts)
    
    def _save_global_summary(self, global_summary_path: Path, content: str, summaries: List[Dict]) -> None:
        """
        Save the global summary to a file.
        
        Args:
            global_summary_path: Path where to save the global summary
            content: Generated summary content
            summaries: List of individual summaries for metadata
        """
        try:
            with open(global_summary_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write("# Global Walkthrough Series Summary\n\n")
                
                # Write metadata
                f.write("## Series Information\n\n")
                f.write(f"- **Date Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- **Total Meetings**: {len(summaries)}\n")
                
                # Calculate total duration and words
                total_transcript_words = 0
                durations = []
                for summary in summaries:
                    # Try to extract word count
                    words_str = summary.get('transcript_words', '0')
                    words_match = re.search(r'([\d,]+)', words_str.replace(',', ''))
                    if words_match:
                        total_transcript_words += int(words_match.group(1))
                
                f.write(f"- **Total Transcript Words Analyzed**: {total_transcript_words:,}\n")
                f.write(f"- **Meeting Topics**: {', '.join([s['meeting_topic'] for s in summaries])}\n")
                
                # Date range
                dates = [s.get('meeting_date') for s in summaries if s.get('meeting_date')]
                if dates:
                    f.write(f"- **Date Range**: {min(dates)} to {max(dates)}\n")
                
                f.write("\n")
                
                # Write the AI-generated content
                f.write("## Analysis\n\n")
                f.write(content)
                
                # Add footer
                f.write("\n\n---\n")
                f.write("*This global summary was generated automatically by analyzing all individual meeting summaries using AWS Bedrock and Claude AI.*\n")
            
            self.logger.info(f"Global summary saved to: {global_summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save global summary to {global_summary_path}: {str(e)}")
            raise
