"""Consolidated summarizer that handles both individual and global summaries in one workflow."""

import os
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import time

from .config import Config
from .vtt_parser import VTTParser
from .bedrock_client import BedrockClient
from .global_summarizer import GlobalSummarizer


class ConsolidatedSummarizer:
    """Handles both individual VTT processing and global summary generation."""
    
    def __init__(self, config: Config):
        """
        Initialize the Consolidated Summarizer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.vtt_parser = VTTParser()
        self.bedrock_client = BedrockClient(config)
        self.global_summarizer = GlobalSummarizer(config)
        self.logger = self._setup_logging()
        
        self.logger.info("Consolidated Summarizer initialized")
        self.logger.info(f"Input folder: {self.config.input_folder}")
        self.logger.info(f"Using model: {self.config.bedrock_model_id}")
    
    def summarize_all(self, force_overwrite: bool = False, summaries_folder: str = "summaries") -> Dict[str, any]:
        """
        Complete workflow: process all VTT files and generate global summary.
        
        Args:
            force_overwrite: Whether to overwrite existing summary files
            summaries_folder: Name of the summaries output folder
            
        Returns:
            Dictionary with complete processing results
        """
        start_time = datetime.now()
        
        # Create summaries directory
        summaries_path = Path(summaries_folder)
        summaries_path.mkdir(exist_ok=True)
        
        self.logger.info(f"Created summaries directory: {summaries_path}")
        
        # Step 1: Process individual VTT files
        self.logger.info("=" * 60)
        self.logger.info("STEP 1: PROCESSING INDIVIDUAL VTT FILES")
        self.logger.info("=" * 60)
        
        individual_results = self._process_individual_summaries(summaries_path, force_overwrite)
        
        # Check if we need to generate global summary (even if individual files were skipped)
        if individual_results["processed"] == 0 and individual_results["skipped"] == 0:
            return {
                "status": "no_files",
                "message": "No VTT files found",
                "individual_results": individual_results,
                "global_result": None,
                "timestamp": datetime.now().isoformat()
            }
        
        # Step 2: Generate global summary
        self.logger.info("=" * 60)
        self.logger.info("STEP 2: GENERATING GLOBAL SUMMARY")
        self.logger.info("=" * 60)
        
        global_result = self._generate_consolidated_global_summary(summaries_path, force_overwrite)
        
        # Calculate total time
        total_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "individual_results": individual_results,
            "global_result": global_result,
            "total_time": round(total_time, 2),
            "summaries_folder": str(summaries_path),
            "timestamp": datetime.now().isoformat()
        }
        
        self._log_final_consolidated_results(result)
        
        return result
    
    def _process_individual_summaries(self, summaries_path: Path, force_overwrite: bool) -> Dict[str, any]:
        """
        Process individual VTT files and save to summaries folder.
        
        Args:
            summaries_path: Path to summaries output directory
            force_overwrite: Whether to overwrite existing files
            
        Returns:
            Dictionary with individual processing results
        """
        walkthroughs_path = Path(self.config.input_folder)
        
        if not walkthroughs_path.exists():
            raise FileNotFoundError(f"Walkthroughs directory not found: {walkthroughs_path}")
        
        # Find all subdirectories with VTT files
        vtt_folders = self._find_vtt_folders(walkthroughs_path)
        
        if not vtt_folders:
            self.logger.warning("No VTT files found in walkthroughs directory")
            return {"processed": 0, "errors": 0, "skipped": 0, "results": []}
        
        self.logger.info(f"Found {len(vtt_folders)} folders with VTT files")
        
        results = {
            "processed": 0,
            "errors": 0,
            "skipped": 0,
            "results": [],
            "start_time": datetime.now().isoformat(),
            "total_folders": len(vtt_folders)
        }
        
        # Process each folder
        for folder_path, vtt_file in vtt_folders:
            try:
                result = self._process_single_vtt(folder_path, vtt_file, summaries_path, force_overwrite)
                results["results"].append(result)
                
                if result["status"] == "success":
                    results["processed"] += 1
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                else:
                    results["errors"] += 1
                    
            except Exception as e:
                self.logger.error(f"Unexpected error processing {folder_path}: {str(e)}")
                results["errors"] += 1
                results["results"].append({
                    "folder": str(folder_path),
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        results["end_time"] = datetime.now().isoformat()
        
        return results
    
    def _process_single_vtt(self, folder_path: Path, vtt_file: Path, summaries_path: Path, 
                           force_overwrite: bool) -> Dict[str, any]:
        """
        Process a single VTT file and save summary to summaries folder.
        
        Args:
            folder_path: Path to the walkthrough folder
            vtt_file: Path to the VTT file
            summaries_path: Path to summaries output directory
            force_overwrite: Whether to overwrite existing files
            
        Returns:
            Dictionary with processing result
        """
        folder_name = folder_path.name
        summary_filename = f"{folder_name}_summary.md"
        summary_path = summaries_path / summary_filename
        
        self.logger.info(f"Processing: {folder_name}")
        
        # Check if summary already exists
        if summary_path.exists() and not force_overwrite:
            self.logger.info(f"Summary already exists for {folder_name}, skipping")
            return {
                "folder": folder_name,
                "status": "skipped",
                "message": "Summary file already exists",
                "summary_path": str(summary_path),
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Extract transcript
            self.logger.info(f"Parsing VTT file: {vtt_file.name}")
            start_time = time.time()
            
            transcript = self.vtt_parser.extract_full_transcript(str(vtt_file))
            metadata = self.vtt_parser.get_transcript_metadata(str(vtt_file))
            
            parse_time = time.time() - start_time
            self.logger.info(f"VTT parsing completed in {parse_time:.2f}s")
            self.logger.info(f"Transcript stats: {metadata['word_count']} words, "
                           f"{metadata['duration_formatted']} duration")
            
            # Generate meeting context
            meeting_context = self._extract_meeting_context(folder_name, metadata)
            
            # Generate summary
            self.logger.info("Generating summary with Claude...")
            start_time = time.time()
            
            summary = self.bedrock_client.generate_summary(transcript, meeting_context)
            
            generation_time = time.time() - start_time
            self.logger.info(f"Summary generation completed in {generation_time:.2f}s")
            
            # Save summary
            self._save_individual_summary(summary_path, summary, metadata, folder_name)
            
            self.logger.info(f"Successfully processed {folder_name}")
            
            return {
                "folder": folder_name,
                "status": "success",
                "summary_path": str(summary_path),
                "transcript_stats": metadata,
                "processing_time": {
                    "parse_time": round(parse_time, 2),
                    "generation_time": round(generation_time, 2),
                    "total_time": round(parse_time + generation_time, 2)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing {folder_name}: {str(e)}")
            return {
                "folder": folder_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_consolidated_global_summary(self, summaries_path: Path, force_overwrite: bool) -> Dict[str, any]:
        """
        Generate global summary from individual summaries in the summaries folder.
        
        Args:
            summaries_path: Path to summaries directory
            force_overwrite: Whether to overwrite existing global summary
            
        Returns:
            Dictionary with global summary generation result
        """
        global_summary_path = summaries_path / "global_summary.md"
        
        # Check if global summary already exists
        if global_summary_path.exists() and not force_overwrite:
            self.logger.info("Global summary already exists, skipping")
            return {
                "status": "skipped",
                "message": "Global summary file already exists",
                "global_summary_path": str(global_summary_path),
                "timestamp": datetime.now().isoformat()
            }
        
        # Collect individual summaries from summaries folder
        summaries = self._collect_summaries_from_folder(summaries_path)
        
        if not summaries:
            self.logger.warning("No individual summaries found for global summary")
            return {
                "status": "no_summaries",
                "message": "No individual summaries to aggregate",
                "timestamp": datetime.now().isoformat()
            }
        
        self.logger.info(f"Found {len(summaries)} individual summaries to aggregate")
        
        try:
            self.logger.info("Generating global summary with Claude...")
            start_time = time.time()
            
            global_content = self.global_summarizer._generate_global_content(summaries)
            
            generation_time = time.time() - start_time
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
    
    def _collect_summaries_from_folder(self, summaries_path: Path) -> List[Dict[str, any]]:
        """
        Collect all individual summary files from the summaries folder.
        
        Args:
            summaries_path: Path to summaries directory
            
        Returns:
            List of summary information dictionaries
        """
        summaries = []
        
        # Look for all *_summary.md files
        for summary_file in summaries_path.glob("*_summary.md"):
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract folder name from filename (remove _summary.md)
                folder_name = summary_file.stem.replace('_summary', '')
                
                # Extract meeting date and topic from folder name
                meeting_info = self.global_summarizer._parse_folder_name(folder_name)
                
                # Extract key information from summary
                summary_data = self.global_summarizer._extract_summary_info(content, folder_name)
                
                summaries.append({
                    "folder_name": folder_name,
                    "meeting_date": meeting_info.get("date"),
                    "meeting_topic": meeting_info.get("topic"),
                    "summary_path": str(summary_file),
                    "content": content,
                    "word_count": len(content.split()),
                    **summary_data
                })
                
            except Exception as e:
                self.logger.warning(f"Could not read summary from {summary_file}: {str(e)}")
                continue
        
        # Sort by date if available, otherwise by folder name
        summaries.sort(key=lambda x: x.get("meeting_date") or x["folder_name"])
        
        return summaries
    
    def _find_vtt_folders(self, walkthroughs_path: Path) -> List[Tuple[Path, Path]]:
        """
        Find all folders containing VTT files.
        
        Args:
            walkthroughs_path: Path to walkthroughs directory
            
        Returns:
            List of tuples (folder_path, vtt_file_path)
        """
        vtt_folders = []
        
        for item in walkthroughs_path.iterdir():
            if item.is_dir():
                # Look for VTT files in this directory
                vtt_files = list(item.glob("*.vtt"))
                
                if vtt_files:
                    # Use the first VTT file found (there should typically be only one)
                    vtt_file = vtt_files[0]
                    vtt_folders.append((item, vtt_file))
                    
                    if len(vtt_files) > 1:
                        self.logger.warning(f"Multiple VTT files found in {item.name}, using {vtt_file.name}")
        
        return vtt_folders
    
    def _extract_meeting_context(self, folder_name: str, metadata: Dict) -> str:
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
        if "_" in folder_name:
            parts = folder_name.split("_", 1)
            if len(parts) == 2:
                date_part, topic_part = parts
                context_parts.append(f"Meeting Date: {date_part}")
                context_parts.append(f"Topic: {topic_part.replace('_', ' ').title()}")
        else:
            context_parts.append(f"Meeting: {folder_name.replace('_', ' ').title()}")
        
        # Add metadata
        context_parts.append(f"Duration: {metadata['duration_formatted']}")
        context_parts.append(f"Transcript Length: {metadata['word_count']} words")
        
        if metadata['estimated_speakers'] > 0:
            context_parts.append(f"Estimated Speakers: {metadata['estimated_speakers']}")
        
        return "\n".join(context_parts)
    
    def _save_individual_summary(self, summary_path: Path, summary: str, 
                                metadata: Dict, folder_name: str) -> None:
        """
        Save the generated summary to a markdown file.
        
        Args:
            summary_path: Path where to save the summary
            summary: Generated summary text
            metadata: VTT metadata
            folder_name: Name of the walkthrough folder
        """
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"# {folder_name.replace('_', ' ').title()} - Meeting Summary\n\n")
                
                # Write metadata
                f.write("## Meeting Information\n\n")
                f.write(f"- **Date Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- **Duration**: {metadata['duration_formatted']}\n")
                f.write(f"- **Transcript Words**: {metadata['word_count']:,}\n")
                f.write(f"- **Source File**: {Path(metadata['file_path']).name}\n\n")
                
                # Write the summary
                f.write("## Summary\n\n")
                f.write(summary)
                
                # Add footer
                f.write("\n\n---\n")
                f.write("*This summary was generated automatically using AWS Bedrock and Claude AI.*\n")
            
            self.logger.info(f"Summary saved to: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save summary to {summary_path}: {str(e)}")
            raise
    
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
                for summary in summaries:
                    # Try to extract word count
                    words_str = summary.get('transcript_words', '0')
                    import re
                    words_match = re.search(r'([\d,]+)', str(words_str).replace(',', ''))
                    if words_match:
                        try:
                            total_transcript_words += int(words_match.group(1))
                        except ValueError:
                            pass  # Skip if can't parse
                
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
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
            
        logger.setLevel(getattr(logging, self.config.logging_level))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.logging_level))
        
        # Formatter
        formatter = logging.Formatter(self.config.logging_format)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
        return logger
    
    def _log_final_consolidated_results(self, results: Dict) -> None:
        """Log final consolidated processing results."""
        individual = results["individual_results"]
        global_result = results["global_result"]
        
        self.logger.info("="*80)
        self.logger.info("CONSOLIDATED SUMMARIZATION COMPLETE")
        self.logger.info("="*80)
        self.logger.info(f"Total processing time: {results['total_time']}s")
        self.logger.info(f"Summaries folder: {results['summaries_folder']}")
        self.logger.info("")
        self.logger.info("INDIVIDUAL SUMMARIES:")
        self.logger.info(f"  Total folders found: {individual['total_folders']}")
        self.logger.info(f"  Successfully processed: {individual['processed']}")
        self.logger.info(f"  Skipped (already exist): {individual['skipped']}")
        self.logger.info(f"  Errors encountered: {individual['errors']}")
        self.logger.info("")
        self.logger.info("GLOBAL SUMMARY:")
        if global_result['status'] == 'success':
            self.logger.info(f"  ✅ Generated successfully")
            self.logger.info(f"  📊 Processed {global_result['summaries_processed']} summaries")
            self.logger.info(f"  ⏱️  Generation time: {global_result['generation_time']}s")
        else:
            self.logger.info(f"  ❌ {global_result.get('message', 'Failed')}")
        
        if individual['errors'] > 0:
            self.logger.warning("Some folders had errors - check logs above for details")
        
        self.logger.info("="*80)
