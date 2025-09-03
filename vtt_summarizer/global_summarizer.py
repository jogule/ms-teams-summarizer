"""Global summary aggregation module for creating master summaries from individual meeting summaries."""

from pathlib import Path
from typing import List, Dict, Optional

from .config import Config
from .bedrock_client import BedrockClient
from .summary_writer import SummaryWriter
from .utils import (
    parse_folder_name, 
    extract_summary_info, 
    safe_read_file,
    setup_module_logger,
    ProcessingTimer,
    get_iso_timestamp
)


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
        self.summary_writer = SummaryWriter()
        self.logger = setup_module_logger(__name__)
        
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
            with ProcessingTimer("Global summary generation") as timer:
                global_content = self._generate_global_content(summaries)
            
            self.logger.info(f"Global summary generation completed in {timer.duration_rounded}s")
            
            # Save global summary
            self.summary_writer.write_global_summary(global_summary_path, global_content, summaries)
            
            return {
                "status": "success",
                "global_summary_path": str(global_summary_path),
                "summaries_processed": len(summaries),
                "generation_time": timer.duration_rounded,
                "timestamp": get_iso_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating global summary: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": get_iso_timestamp()
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
                    content = safe_read_file(summary_path)
                    
                    # Extract meeting date and topic from folder name
                    meeting_info = parse_folder_name(folder.name)
                    
                    # Extract key information from summary
                    summary_data = extract_summary_info(content, folder.name)
                    
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
    
