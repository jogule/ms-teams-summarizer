"""Main meeting processor that handles individual summaries and global analysis."""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time

from .config import Config
from .transcript_parser import TranscriptParser
from .ai_client import AIClient
from .meeting_analyzer import MeetingAnalyzer
from .file_writer import FileWriter
from .video_processor import VideoProcessor
from .report_generator import ReportGenerator
from .performance_tracker import PerformanceTracker
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


class MeetingProcessor:
    """Processes meeting transcripts and generates individual summaries and global analysis."""
    
    def __init__(self, config: Config, enable_keyframes: bool = True, max_keyframes: int = 5):
        """
        Initialize the Meeting Processor.
        
        Args:
            config: Configuration object
            enable_keyframes: Whether to enable keyframe extraction
            max_keyframes: Maximum number of keyframes to extract per video
        """
        self.config = config
        self.enable_keyframes = enable_keyframes
        self.max_keyframes = max_keyframes
        self.performance_tracker = PerformanceTracker()
        self.transcript_parser = TranscriptParser()
        self.ai_client = AIClient(config, self.performance_tracker)
        self.meeting_analyzer = MeetingAnalyzer(config, self.performance_tracker)
        self.file_writer = FileWriter()
        
        # Initialize video processor only if enabled
        if self.enable_keyframes:
            # Use configuration values with CLI overrides
            config_delays = self.config.keyframes_delays
            self.video_processor = VideoProcessor(
                max_frames=max_keyframes,
                min_relevance_score=self.config.keyframes_min_relevance_score,
                custom_delays=config_delays,
                image_max_width=self.config.keyframes_image_max_width,
                image_quality=self.config.keyframes_image_quality,
                caption_context_window=self.config.keyframes_caption_context_window
            )
        else:
            self.video_processor = None
        
        # Initialize report generator
        self.report_generator = ReportGenerator(config)
            
        self.logger = setup_module_logger(__name__)
        
        self.logger.info("Meeting Processor initialized")
        self.logger.info(f"Input folder: {self.config.input_folder}")
        self.logger.info(f"Using model: {self.config.bedrock_model_id}")
    
    def _format_filename(self, template: str, **kwargs) -> str:
        """
        Format filename template with provided variables.
        
        Args:
            template: Filename template with placeholders
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted filename string
        """
        import datetime
        
        # Add standard variables
        format_vars = {
            'timestamp': get_iso_timestamp().replace(':', '-').replace('T', '_'),
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            **kwargs
        }
        
        return template.format(**format_vars)
    
    def _extract_folder_name_from_file(self, summary_file: Path) -> str:
        """
        Extract folder name from summary filename using config template.
        
        Args:
            summary_file: Path to summary file
            
        Returns:
            Extracted folder name
        """
        template = self.config.individual_summary_filename
        filename = summary_file.name
        
        # Simple extraction for basic templates like {folder_name}_summary.md
        if '{folder_name}' in template:
            # Find the parts before and after {folder_name}
            parts = template.split('{folder_name}')
            if len(parts) == 2:
                prefix, suffix = parts
                # Remove prefix and suffix to get folder name
                if filename.startswith(prefix):
                    filename = filename[len(prefix):]
                if filename.endswith(suffix):
                    filename = filename[:-len(suffix)] if suffix else filename
                return filename
        
        # Fallback: use stem (filename without extension)
        return summary_file.stem
    
    def process_meetings(self, force_overwrite: bool = False, summaries_folder: str = "summaries") -> Dict[str, any]:
        """
        Complete workflow: process all meeting files and generate analysis.
        
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
            
            # Step 2: Generate global analysis
            self.logger.info("=" * 60)
            self.logger.info("STEP 2: GENERATING GLOBAL ANALYSIS")
            self.logger.info("=" * 60)
            
            global_result = self._create_global_analysis(summaries_path, force_overwrite)
            
            # Step 3: Generate final report
            self.logger.info("=" * 60)
            self.logger.info("STEP 3: GENERATING FINAL REPORT")
            self.logger.info("=" * 60)
            
            pdf_result = self._create_final_report(summaries_path, individual_results["results"], force_overwrite)
        
        result = {
            "status": "success",
            "individual_results": individual_results,
            "global_result": global_result,
            "pdf_result": pdf_result,
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
        
        # Find all subdirectories with meeting files
        meeting_folders = self._find_meeting_folders(walkthroughs_path)
        
        if not meeting_folders:
            self.logger.warning("No meeting files found in input directory")
            return {"processed": 0, "errors": 0, "skipped": 0, "results": []}
        
        self.logger.info(f"Found {len(meeting_folders)} folders with meeting files")
        
        results = {
            "processed": 0,
            "errors": 0,
            "skipped": 0,
            "results": [],
            "start_time": get_iso_timestamp(),
            "total_folders": len(meeting_folders)
        }
        
        # Process each folder
        for folder_path, meeting_file in meeting_folders:
            try:
                result = self._process_single_meeting(folder_path, meeting_file, summaries_path, force_overwrite)
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
    
    def _process_single_meeting(self, folder_path: Path, meeting_file: Path, summaries_path: Path, 
                               force_overwrite: bool) -> Dict[str, any]:
        """
        Process a single meeting file and save summary to summaries folder.
        
        Args:
            folder_path: Path to the meeting folder
            meeting_file: Path to the meeting transcript file
            summaries_path: Path to summaries output directory
            force_overwrite: Whether to overwrite existing files
            
        Returns:
            Dictionary with processing result
        """
        folder_name = folder_path.name
        summary_filename = self._format_filename(self.config.individual_summary_filename, folder_name=folder_name)
        summary_path = summaries_path / summary_filename
        
        # Enhanced output for both verbose and default modes
        print(f"\n📁 Processing: {folder_name}")
        self.logger.info(f"Processing: {folder_name}")
        
        # Check if summary already exists
        if summary_path.exists() and not force_overwrite:
            print(f"   ⏭️  Already exists, skipping")
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
            print(f"   📄 Parsing transcript file: {meeting_file.name}")
            self.logger.info(f"Parsing transcript file: {meeting_file.name}")
            start_time = time.time()
            
            transcript = self.transcript_parser.extract_full_transcript(str(meeting_file))
            segments = self.transcript_parser.parse_file(str(meeting_file))  # Get segments for keyframe extraction
            metadata = self.transcript_parser.get_transcript_metadata(str(meeting_file))
            
            parse_time = time.time() - start_time
            print(f"   ✅ Parsing complete: {metadata['word_count']} words, {metadata['duration_formatted']} duration ({parse_time:.2f}s)")
            self.logger.info(f"Transcript parsing completed in {parse_time:.2f}s")
            self.logger.info(f"Transcript stats: {metadata['word_count']} words, "
                           f"{metadata['duration_formatted']} duration")
            
            # Extract keyframes if enabled and video file exists
            keyframes = []
            keyframe_time = 0
            
            if self.enable_keyframes:
                video_file = self._find_video_file(folder_path)
                
                if video_file:
                    print(f"   🎥 Extracting keyframes from: {video_file.name}")
                    self.logger.info(f"Extracting keyframes from: {video_file.name}")
                    keyframe_start_time = time.time()
                    
                    images_dir = summaries_path / "images"
                    base_filename = f"{folder_name}_summary"
                    
                    keyframes = self.video_processor.extract_keyframes(
                        str(video_file), segments, str(images_dir), base_filename
                    )
                    
                    keyframe_time = time.time() - keyframe_start_time
                    print(f"   ✅ Keyframes extracted: {len(keyframes)} frames ({keyframe_time:.2f}s)")
                    self.logger.info(f"Keyframe extraction completed in {keyframe_time:.2f}s, "
                                   f"extracted {len(keyframes)} frames")
                else:
                    print(f"   🎥 No video file found, skipping keyframes")
                    self.logger.info("No video file found, skipping keyframe extraction")
            else:
                print(f"   🎥 Keyframe extraction disabled")
                self.logger.info("Keyframe extraction disabled")
            
            # Generate meeting context
            meeting_context = extract_meeting_context(folder_name, metadata)
            
            # Generate summary
            print(f"   🤖 Generating summary with Model...")
            self.logger.info("Generating summary with Model...")
            start_time = time.time()
            
            summary = self.ai_client.create_summary(transcript, meeting_context, folder_name)
            
            generation_time = time.time() - start_time
            
            # Get model statistics for this call
            model_stats = self.performance_tracker.get_individual_stats(folder_name)
            
            print(f"   ✅ Summary generated ({generation_time:.2f}s)")
            if model_stats:
                print(self.performance_tracker.format_stats_for_display(model_stats))
            
            self.logger.info(f"Summary generation completed in {generation_time:.2f}s")
            
            # Save summary with keyframes
            self.file_writer.write_individual_summary(summary_path, summary, metadata, folder_name, keyframes)
            
            print(f"   💾 Summary saved: {summary_filename}")
            print(f"   ✅ Processing complete for {folder_name}")
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
                "model_stats": model_stats.__dict__ if model_stats else None,
                "keyframes_extracted": len(keyframes),
                "timestamp": get_iso_timestamp()
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {folder_name}: {str(e)}")
            self.logger.error(f"Error processing {folder_name}: {str(e)}")
            return {
                "folder": folder_name,
                "status": "error",
                "error": str(e),
                "timestamp": get_iso_timestamp()
            }
    
    def _create_global_analysis(self, summaries_path: Path, force_overwrite: bool) -> Dict[str, any]:
        """
        Generate global summary from individual summaries in the summaries folder.
        
        Args:
            summaries_path: Path to summaries directory
            force_overwrite: Whether to overwrite existing global summary
            
        Returns:
            Dictionary with global summary generation result
        """
        global_summary_filename = self._format_filename(self.config.global_summary_filename)
        global_summary_path = summaries_path / global_summary_filename
        
        # Check if global summary already exists
        if global_summary_path.exists() and not force_overwrite:
            print(f"\n🌍 Global summary already exists, skipping")
            self.logger.info("Global summary already exists, skipping")
            return {
                "status": "skipped",
                "message": "Global summary file already exists",
                "global_summary_path": str(global_summary_path),
                "timestamp": get_iso_timestamp()
            }
        
        # Collect individual summaries from summaries folder
        print(f"\n🌍 Generating global summary...")
        summaries = self._collect_summaries_from_folder(summaries_path)
        
        if not summaries:
            print(f"   ⚠️ No individual summaries found")
            self.logger.warning("No individual summaries found for global summary")
            return {
                "status": "no_summaries",
                "message": "No individual summaries to aggregate",
                "timestamp": get_iso_timestamp()
            }
        
        print(f"   📄 Found {len(summaries)} individual summaries to aggregate")
        self.logger.info(f"Found {len(summaries)} individual summaries to aggregate")
        
        try:
            print(f"   🤖 Generating global summary with Model...")
            self.logger.info("Generating global summary with Model...")
            with ProcessingTimer("Global summary generation") as timer:
                global_content = self.meeting_analyzer._create_global_content(summaries)
            
            # Get model statistics for global analysis
            global_stats = self.performance_tracker.get_analysis_stats()
            
            print(f"   ✅ Global summary generated ({timer.duration_rounded}s)")
            if global_stats:
                print(self.performance_tracker.format_stats_for_display(global_stats))
            
            self.logger.info(f"Global summary generation completed in {timer.duration_rounded}s")
            
            # Save global analysis
            self.file_writer.write_global_summary(global_summary_path, global_content, summaries)
            print(f"   💾 Global summary saved: {global_summary_filename}")
            
            return {
                "status": "success",
                "global_summary_path": str(global_summary_path),
                "summaries_processed": len(summaries),
                "generation_time": timer.duration_rounded,
                "timestamp": get_iso_timestamp()
            }
            
        except Exception as e:
            print(f"   ❌ Error generating global summary: {str(e)}")
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
        
        # Look for all individual summary files using config pattern
        # Convert template to glob pattern (simple approach for basic templates)
        pattern = self.config.individual_summary_filename.replace('{folder_name}', '*')
        for summary_file in summaries_path.glob(pattern):
            try:
                content = safe_read_file(summary_file)
                
                # Extract folder name from filename using config template
                folder_name = self._extract_folder_name_from_file(summary_file)
                
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
    
    def _find_meeting_folders(self, input_path: Path) -> List[Tuple[Path, Path]]:
        """
        Find all folders containing meeting transcript files.
        
        Args:
            input_path: Path to input directory
            
        Returns:
            List of tuples (folder_path, meeting_file_path)
        """
        meeting_folders = []
        
        for item in input_path.iterdir():
            if item.is_dir():
                # Look for input files using configurable patterns
                meeting_files = []
                for pattern in self.config.input_file_patterns:
                    meeting_files.extend(item.glob(pattern))
                
                if meeting_files:
                    # Use the first meeting file found (there should typically be only one)
                    meeting_file = meeting_files[0]
                    meeting_folders.append((item, meeting_file))
                    
                    if len(meeting_files) > 1:
                        self.logger.warning(f"Multiple meeting files found in {item.name}, using {meeting_file.name}")
        
        return meeting_folders
    
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
        pdf_result = results.get("pdf_result", {})
        
        self.logger.info("="*80)
        self.logger.info("MEETING PROCESSING COMPLETE")
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
        self.logger.info("GLOBAL ANALYSIS:")
        if global_result and global_result.get('status') == 'success':
            self.logger.info(f"  ✅ Generated successfully")
            self.logger.info(f"  📊 Processed {global_result.get('summaries_processed', 0)} summaries")
            self.logger.info(f"  ⏱️  Generation time: {global_result.get('generation_time', 0)}s")
        else:
            self.logger.info(f"  ❌ {global_result.get('message', 'Failed') if global_result else 'Failed'}")
        self.logger.info("")
        self.logger.info("FINAL REPORT:")
        if pdf_result.get('status') == 'success':
            self.logger.info(f"  ✅ Generated successfully")
            self.logger.info(f"  📄 PDF file: {pdf_result.get('pdf_filename', 'Unknown')}")
            self.logger.info(f"  📊 Summaries included: {pdf_result.get('summaries_included', 0)}")
            self.logger.info(f"  ⏱️  Generation time: {pdf_result.get('generation_time', 0)}s")
        elif pdf_result.get('status') == 'disabled':
            self.logger.info(f"  ⏭️  Disabled in configuration")
        elif pdf_result.get('status') == 'skipped':
            self.logger.info(f"  ⏭️  Already exists")
        elif pdf_result.get('status') == 'no_summaries':
            self.logger.info(f"  ⚠️  No summaries available")
        else:
            self.logger.info(f"  ❌ {pdf_result.get('message', 'Failed')}")
        
        if individual['errors'] > 0:
            self.logger.warning("Some folders had errors - check logs above for details")
        
        self.logger.info("="*80)
    
    def _create_final_report(self, summaries_path: Path, individual_results: List[Dict], force_overwrite: bool) -> Dict[str, any]:
        """
        Create final comprehensive report from all summaries.
        
        Args:
            summaries_path: Path to summaries directory
            individual_results: List of individual processing results
            force_overwrite: Whether to overwrite existing PDF
            
        Returns:
            Dictionary with PDF generation result
        """
        try:
            # Find global summary file
            global_summary_filename = self._format_filename(self.config.global_summary_filename)
            global_summary_path = summaries_path / global_summary_filename
            
            # Filter individual summaries for PDF - include both successful and skipped ones
            # since skipped means they already exist and are available
            available_summaries = []
            for result in individual_results:
                if result.get('status') in ['success', 'skipped']:
                    # Ensure the result has folder_name (use 'folder' if 'folder_name' is missing)
                    if 'folder_name' not in result and 'folder' in result:
                        result['folder_name'] = result['folder']
                    # For skipped files, we need to add the summary_path if missing
                    if result.get('status') == 'skipped' and 'summary_path' not in result:
                        folder_name = result.get('folder_name', result.get('folder', 'unknown'))
                        summary_filename = self._format_filename(self.config.individual_summary_filename, folder_name=folder_name)
                        result['summary_path'] = str(summaries_path / summary_filename)
                    available_summaries.append(result)
            
            if not available_summaries:
                self.logger.warning("No individual summaries found for PDF generation")
                return {
                    "status": "no_summaries",
                    "message": "No individual summaries available for PDF generation",
                    "timestamp": get_iso_timestamp()
                }
            
            self.logger.info(f"Generating PDF with {len(available_summaries)} individual summaries")
            
            # Generate final report
            return self.report_generator.generate_comprehensive_pdf(
                summaries_path,
                global_summary_path,
                available_summaries,
                force_overwrite
            )
            
        except Exception as e:
            self.logger.error(f"Error during PDF generation: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": get_iso_timestamp()
            }
