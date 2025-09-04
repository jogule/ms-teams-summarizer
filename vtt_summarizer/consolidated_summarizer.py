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
from .pdf_generator import PDFGenerator
from .model_statistics import ModelStatisticsTracker
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
        self.stats_tracker = ModelStatisticsTracker()
        self.vtt_parser = VTTParser()
        self.bedrock_client = BedrockClient(config, self.stats_tracker)
        self.global_summarizer = GlobalSummarizer(config, self.stats_tracker)
        self.summary_writer = SummaryWriter()
        
        # Initialize keyframe extractor only if enabled
        if self.enable_keyframes:
            # Use configuration values with CLI overrides
            config_delays = self.config.keyframes_delays
            self.keyframe_extractor = KeyframeExtractor(
                max_frames=max_keyframes,
                min_relevance_score=self.config.keyframes_min_relevance_score,
                custom_delays=config_delays,
                image_max_width=self.config.keyframes_image_max_width,
                image_quality=self.config.keyframes_image_quality
            )
        else:
            self.keyframe_extractor = None
        
        # Initialize PDF generator
        self.pdf_generator = PDFGenerator(config)
            
        self.logger = setup_module_logger(__name__)
        
        self.logger.info("Consolidated Summarizer initialized")
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
            
            # Step 3: Generate comprehensive PDF report
            self.logger.info("=" * 60)
            self.logger.info("STEP 3: GENERATING COMPREHENSIVE PDF REPORT")
            self.logger.info("=" * 60)
            
            pdf_result = self._generate_pdf_report(summaries_path, individual_results["results"], force_overwrite)
        
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
            print(f"   📄 Parsing VTT file: {vtt_file.name}")
            self.logger.info(f"Parsing VTT file: {vtt_file.name}")
            start_time = time.time()
            
            transcript = self.vtt_parser.extract_full_transcript(str(vtt_file))
            segments = self.vtt_parser.parse_file(str(vtt_file))  # Get segments for keyframe extraction
            metadata = self.vtt_parser.get_transcript_metadata(str(vtt_file))
            
            parse_time = time.time() - start_time
            print(f"   ✅ Parsing complete: {metadata['word_count']} words, {metadata['duration_formatted']} duration ({parse_time:.2f}s)")
            self.logger.info(f"VTT parsing completed in {parse_time:.2f}s")
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
                    
                    keyframes = self.keyframe_extractor.extract_keyframes(
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
            print(f"   🤖 Generating summary with Claude...")
            self.logger.info("Generating summary with Claude...")
            start_time = time.time()
            
            summary = self.bedrock_client.generate_summary(transcript, meeting_context, folder_name)
            
            generation_time = time.time() - start_time
            
            # Get model statistics for this call
            model_stats = self.stats_tracker.get_individual_stats(folder_name)
            
            print(f"   ✅ Summary generated ({generation_time:.2f}s)")
            if model_stats:
                print(self.stats_tracker.format_stats_for_display(model_stats))
            
            self.logger.info(f"Summary generation completed in {generation_time:.2f}s")
            
            # Save summary with keyframes
            self.summary_writer.write_individual_summary(summary_path, summary, metadata, folder_name, keyframes)
            
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
    
    def _generate_consolidated_global_summary(self, summaries_path: Path, force_overwrite: bool) -> Dict[str, any]:
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
            print(f"   🤖 Generating global summary with Claude...")
            self.logger.info("Generating global summary with Claude...")
            with ProcessingTimer("Global summary generation") as timer:
                global_content = self.global_summarizer._generate_global_content(summaries)
            
            # Get model statistics for global summary
            global_stats = self.stats_tracker.get_global_stats()
            
            print(f"   ✅ Global summary generated ({timer.duration_rounded}s)")
            if global_stats:
                print(self.stats_tracker.format_stats_for_display(global_stats))
            
            self.logger.info(f"Global summary generation completed in {timer.duration_rounded}s")
            
            # Save global summary
            self.summary_writer.write_global_summary(global_summary_path, global_content, summaries)
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
                # Look for input files using configurable patterns
                vtt_files = []
                for pattern in self.config.input_file_patterns:
                    vtt_files.extend(item.glob(pattern))
                
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
        pdf_result = results.get("pdf_result", {})
        
    def _generate_pdf_report(self, summaries_path: Path, individual_results: List[Dict], force_overwrite: bool) -> Dict[str, any]:
        """
        Generate comprehensive PDF report from all summaries.
        
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
            
            # Filter successful individual summaries for PDF and ensure they have folder_name
            successful_summaries = []
            for result in individual_results:
                if result.get('status') == 'success':
                    # Ensure the result has folder_name (use 'folder' if 'folder_name' is missing)
                    if 'folder_name' not in result and 'folder' in result:
                        result['folder_name'] = result['folder']
                    successful_summaries.append(result)
            
            if not successful_summaries:
                self.logger.warning("No successful individual summaries found for PDF generation")
                return {
                    "status": "no_summaries",
                    "message": "No individual summaries available for PDF generation",
                    "timestamp": get_iso_timestamp()
                }
            
            self.logger.info(f"Generating PDF with {len(successful_summaries)} individual summaries")
            
            # Generate PDF
            return self.pdf_generator.generate_comprehensive_pdf(
                summaries_path,
                global_summary_path,
                successful_summaries,
                force_overwrite
            )
            
        except Exception as e:
            self.logger.error(f"Error during PDF generation: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": get_iso_timestamp()
            }
    
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
        self.logger.info("")
        self.logger.info("PDF REPORT:")
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
