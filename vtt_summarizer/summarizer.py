"""Main summarizer module for processing VTT files and generating summaries."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import time

from .config import Config
from .vtt_parser import VTTParser
from .bedrock_client import BedrockClient


class VTTSummarizer:
    """Main class for processing VTT files and generating summaries."""
    
    def __init__(self, config: Config):
        """
        Initialize the VTT Summarizer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.vtt_parser = VTTParser()
        self.bedrock_client = BedrockClient(config)
        self.logger = self._setup_logging()
        
        self.logger.info("VTT Summarizer initialized")
        self.logger.info(f"Input folder: {self.config.input_folder}")
        self.logger.info(f"Using model: {self.config.bedrock_model_id}")
    
    def process_all_walkthroughs(self) -> Dict[str, any]:
        """
        Process all VTT files in the walkthroughs directory.
        
        Returns:
            Dictionary with processing results and statistics
        """
        walkthroughs_path = Path(self.config.input_folder)
        
        if not walkthroughs_path.exists():
            raise FileNotFoundError(f"Walkthroughs directory not found: {walkthroughs_path}")
        
        # Find all subdirectories with VTT files
        vtt_folders = self._find_vtt_folders(walkthroughs_path)
        
        if not vtt_folders:
            self.logger.warning("No VTT files found in walkthroughs directory")
            return {"processed": 0, "errors": 0, "results": []}
        
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
                result = self.process_single_walkthrough(folder_path, vtt_file)
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
        self._log_final_results(results)
        
        return results
    
    def process_single_walkthrough(self, folder_path: Path, vtt_file: Path, 
                                 force_overwrite: bool = False) -> Dict[str, any]:
        """
        Process a single walkthrough folder and generate summary.
        
        Args:
            folder_path: Path to the walkthrough folder
            vtt_file: Path to the VTT file
            force_overwrite: Whether to overwrite existing summary files
            
        Returns:
            Dictionary with processing result
        """
        folder_name = folder_path.name
        summary_path = folder_path / self.config.output_filename
        
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
            self._save_summary(summary_path, summary, metadata, folder_name)
            
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
        
        return "\\n".join(context_parts)
    
    def _save_summary(self, summary_path: Path, summary: str, 
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
                f.write(f"# {folder_name.replace('_', ' ').title()} - Meeting Summary\\n\\n")
                
                # Write metadata
                f.write("## Meeting Information\\n\\n")
                f.write(f"- **Date Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
                f.write(f"- **Duration**: {metadata['duration_formatted']}\\n")
                f.write(f"- **Transcript Words**: {metadata['word_count']:,}\\n")
                f.write(f"- **Source File**: {Path(metadata['file_path']).name}\\n\\n")
                
                # Write the summary
                f.write("## Summary\\n\\n")
                f.write(summary)
                
                # Add footer
                f.write("\\n\\n---\\n")
                f.write("*This summary was generated automatically using AWS Bedrock and Claude 3.5 Sonnet.*\\n")
            
            self.logger.info(f"Summary saved to: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save summary to {summary_path}: {str(e)}")
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
    
    def _log_final_results(self, results: Dict) -> None:
        """Log final processing results summary."""
        self.logger.info("="*60)
        self.logger.info("PROCESSING COMPLETE")
        self.logger.info("="*60)
        self.logger.info(f"Total folders found: {results['total_folders']}")
        self.logger.info(f"Successfully processed: {results['processed']}")
        self.logger.info(f"Skipped (already exist): {results['skipped']}")
        self.logger.info(f"Errors encountered: {results['errors']}")
        
        if results['errors'] > 0:
            self.logger.warning("Some folders had errors - check logs above for details")
        
        self.logger.info("="*60)
