"""Meeting analysis module for creating comprehensive analysis from individual meeting summaries."""

from pathlib import Path
from typing import List, Dict, Optional

from .config import Config
from .ai_client import AIClient
from .file_writer import FileWriter
from .performance_tracker import PerformanceTracker
from .template_builder import TemplateBuilder
from .utils import (
    parse_folder_name, 
    extract_summary_info, 
    safe_read_file,
    setup_module_logger,
    ProcessingTimer,
    get_iso_timestamp
)


class MeetingAnalyzer:
    """Creates comprehensive analysis from individual meeting summaries."""
    
    def __init__(self, config: Config, performance_tracker: PerformanceTracker = None):
        """
        Initialize the Meeting Analyzer.
        
        Args:
            config: Configuration object
            performance_tracker: Optional tracker for monitoring model performance
        """
        self.config = config
        self.performance_tracker = performance_tracker
        self.ai_client = AIClient(config, performance_tracker)
        self.file_writer = FileWriter()
        self.template_builder = TemplateBuilder(config)
        self.logger = setup_module_logger(__name__)
        
        self.logger.info("Meeting Analyzer initialized")
    
    def create_global_analysis(self, output_filename: str = "GLOBAL_ANALYSIS.md") -> Dict[str, any]:
        """
        Create a global analysis from all individual meeting summaries.
        
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
        
        # Generate global analysis content
        try:
            self.logger.info("Creating global analysis with AI...")
            with ProcessingTimer("Global analysis creation") as timer:
                global_content = self._create_global_content(summaries)
            
            self.logger.info(f"Global analysis creation completed in {timer.duration_rounded}s")
            
            # Save global analysis
            self.file_writer.write_global_summary(global_summary_path, global_content, summaries)
            
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
    
    
    
    def _create_global_content(self, summaries: List[Dict]) -> str:
        """
        Create global analysis content using AI models.
        
        Args:
            summaries: List of individual summary data
            
        Returns:
            Generated global summary content
        """
        # Build the prompt for global analysis
        prompt = self._build_global_analysis_prompt(summaries)
        
        # Use AI to generate the global analysis
        return self.ai_client.create_summary(prompt, "Global Meeting Series Analysis", "global_analysis")
    
    def _build_global_analysis_prompt(self, summaries: List[Dict]) -> str:
        """
        Build the prompt for global analysis generation using configurable templates.
        
        Args:
            summaries: List of individual summary data
            
        Returns:
            Formatted prompt string
        """
        return self.template_builder.build_global_summary_prompt(summaries)
    
