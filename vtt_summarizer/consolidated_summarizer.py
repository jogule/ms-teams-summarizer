"""Consolidated summarizer that handles both individual and global summaries in one workflow."""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time

from .config import Config
from .vtt_parser import VTTParser
from .bedrock_client import BedrockClient
from .global_summarizer import GlobalSummarizer
from .summary_writer import SummaryWriter
from .keyframe_extractor import KeyframeExtractor
from .utils import (
    parse_folder_name,
    extract_summary_info,
    safe_read_file,
    setup_module_logger,
    ProcessingTimer,
    get_iso_timestamp,
    extract_meeting_context,
    ensure_directory
)


class ConsolidatedSummarizer:
    """Handles both individual VTT processing and global summary generation."""
    
    def __init__(self, config: Config, enable_keyframes: bool = True, max_keyframes: int = 5):
        """
        Initialize the Consolidated Summarizer.
        
        Args:
            config: Configuration object
            enable_keyframes: Whether to enable keyframe extraction
            max_keyframes: Maximum number of keyframes to extract per video
        """
        self.config = config
        self.enable_keyframes = enable_keyframes
        self.max_keyframes = max_keyframes
        self.vtt_parser = VTTParser()
        self.bedrock_client = BedrockClient(config)
        self.global_summarizer = GlobalSummarizer(config)
        self.summary_writer = SummaryWriter()
        
        # Initialize keyframe extractor only if enabled
        if self.enable_keyframes:
            self.keyframe_extractor = KeyframeExtractor(max_frames=max_keyframes, min_relevance_score=0.3)
        else:
            self.keyframe_extractor = None
            
        self.logger = setup_module_logger(__name__)
        
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
        with ProcessingTimer("Complete workflow") as workflow_timer:
            # Create summaries directory
            summaries_path = ensure_directory(Path(summaries_folder))
            
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
                    "timestamp": get_iso_timestamp()
                }
            
            # Step 2: Generate global summary
            self.logger.info("=" * 60)
            self.logger.info("STEP 2: GENERATING GLOBAL SUMMARY")
            self.logger.info("=" * 60)
            
            global_result = self._generate_consolidated_global_summary(summaries_path, force_overwrite)
        
        result = {
            "status": "success",
            "individual_results": individual_results,
            "global_result": global_result,
            "total_time": workflow_timer.duration_rounded,
            "summaries_folder": str(summaries_path),
            "timestamp": get_iso_timestamp()
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
            "start_time": get_iso_timestamp(),
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
                    "timestamp": get_iso_timestamp()
                })
        
        results["end_time"] = get_iso_timestamp()
        
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
                "timestamp": get_iso_timestamp()
            }
        
        try:
            # Extract transcript and segments
            self.logger.info(f"Parsing VTT file: {vtt_file.name}")
            start_time = time.time()
            
            transcript = self.vtt_parser.extract_full_transcript(str(vtt_file))
            segments = self.vtt_parser.parse_file(str(vtt_file))  # Get segments for keyframe extraction
            metadata = self.vtt_parser.get_transcript_metadata(str(vtt_file))
            
            parse_time = time.time() - start_time
            self.logger.info(f"VTT parsing completed in {parse_time:.2f}s")
            self.logger.info(f"Transcript stats: {metadata['word_count']} words, "
                           f"{metadata['duration_formatted']} duration")
            
            # Extract keyframes if enabled and video file exists
            keyframes = []
            keyframe_time = 0
            
            if self.enable_keyframes:
                video_file = self._find_video_file(folder_path)
                
                if video_file:
                    self.logger.info(f"Extracting keyframes from: {video_file.name}")
                    keyframe_start_time = time.time()
                    
                    images_dir = summaries_path / "images"
                    base_filename = f"{folder_name}_summary"
                    
                    keyframes = self.keyframe_extractor.extract_keyframes(
                        str(video_file), segments, str(images_dir), base_filename
                    )
                    
                    keyframe_time = time.time() - keyframe_start_time
                    self.logger.info(f"Keyframe extraction completed in {keyframe_time:.2f}s, "
                                   f"extracted {len(keyframes)} frames")
                else:
                    self.logger.info("No video file found, skipping keyframe extraction")
            else:
                self.logger.info("Keyframe extraction disabled")
            
            # Generate meeting context
            meeting_context = extract_meeting_context(folder_name, metadata)
            
            # Generate summary
            self.logger.info("Generating summary with Claude...")
            start_time = time.time()
            
            summary = self.bedrock_client.generate_summary(transcript, meeting_context)
            
            generation_time = time.time() - start_time
            self.logger.info(f"Summary generation completed in {generation_time:.2f}s")
            
            # Save summary with keyframes
            self.summary_writer.write_individual_summary(summary_path, summary, metadata, folder_name, keyframes)
            
            self.logger.info(f"Successfully processed {folder_name}")
            
            return {
                "folder": folder_name,
                "status": "success",
                "summary_path": str(summary_path),
                "transcript_stats": metadata,
                "processing_time": {
                    "parse_time": round(parse_time, 2),
                    "keyframe_time": round(keyframe_time, 2),
                    "generation_time": round(generation_time, 2),
                    "total_time": round(parse_time + keyframe_time + generation_time, 2)
                },
                "keyframes_extracted": len(keyframes),
                "timestamp": get_iso_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing {folder_name}: {str(e)}")
            return {
                "folder": folder_name,
                "status": "error",
                "error": str(e),
                "timestamp": get_iso_timestamp()
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
                "timestamp": get_iso_timestamp()
            }
        
        # Collect individual summaries from summaries folder
        summaries = self._collect_summaries_from_folder(summaries_path)
        
        if not summaries:
            self.logger.warning("No individual summaries found for global summary")
            return {
                "status": "no_summaries",
                "message": "No individual summaries to aggregate",
                "timestamp": get_iso_timestamp()
            }
        
        self.logger.info(f"Found {len(summaries)} individual summaries to aggregate")
        
        try:
            self.logger.info("Generating global summary with Claude...")
            with ProcessingTimer("Global summary generation") as timer:
                global_content = self.global_summarizer._generate_global_content(summaries)
            
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
                content = safe_read_file(summary_file)
                
                # Extract folder name from filename (remove _summary.md)
                folder_name = summary_file.stem.replace('_summary', '')
                
                # Extract meeting date and topic from folder name
                meeting_info = parse_folder_name(folder_name)
                
                # Extract key information from summary
                summary_data = extract_summary_info(content, folder_name)
                
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
    
    def _find_video_file(self, folder_path: Path) -> Optional[Path]:
        """
        Find video file (MP4) in the given folder.
        
        Args:
            folder_path: Path to the folder to search
            
        Returns:
            Path to video file or None if not found
        """
        # Look for common video file extensions
        video_extensions = ['*.mp4', '*.mov', '*.avi', '*.mkv']
        
        for pattern in video_extensions:
            video_files = list(folder_path.glob(pattern))
            if video_files:
                # Return the first video file found
                return video_files[0]
        
        return None
    
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
