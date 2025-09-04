#!/usr/bin/env python3
"""
VTT Summarizer - Simple Direct Execution

Just run: python3 main.py

No CLI, no options, just processes all VTT files and generates summaries.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from vtt_summarizer.config import Config
from vtt_summarizer.meeting_processor import MeetingProcessor


def setup_logging(verbose=False):
    """Set up console logging based on verbosity level."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    if verbose:
        # Verbose mode: Show INFO level logs from our modules
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
        # Set our modules to INFO level
        for logger_name in ['vtt_summarizer.meeting_processor', 'vtt_summarizer.ai_client', 'vtt_summarizer.meeting_analyzer']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
        
        # Still suppress AWS SDK logs
        for logger_name in ['botocore', 'boto3', 'urllib3']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
    else:
        # Minimal mode: Set up a null handler to suppress all logging
        logging.basicConfig(
            level=logging.CRITICAL,
            handlers=[logging.NullHandler()]
        )
        
        # Suppress all module logs
        for logger_name in ['vtt_summarizer.meeting_processor', 'vtt_summarizer.ai_client', 'vtt_summarizer.meeting_analyzer', 'botocore', 'boto3', 'urllib3']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL)
            logger.addHandler(logging.NullHandler())


def print_header():
    """Print a simple header."""
    print("=" * 60)
    print("🚀 MEETING PROCESSOR")
    print("=" * 60)
    print()


def print_results(results, config, processor=None):
    """Print results in a simple, clean format."""
    print()
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    individual = results.get("individual_results", {})
    global_result = results.get("global_result", {})
    pdf_result = results.get("pdf_result", {})
    
    # Individual summaries
    processed = individual.get('processed', 0)
    skipped = individual.get('skipped', 0)
    errors = individual.get('errors', 0)
    
    print(f"📝 Individual Summaries:")
    print(f"   ✅ Processed: {processed}")
    print(f"   ⏭️  Skipped: {skipped}")
    print(f"   ❌ Errors: {errors}")
    
    # Keyframe statistics
    total_keyframes = 0
    processed_results = [r for r in individual.get('results', []) if r.get('status') == 'success']
    for result in processed_results:
        total_keyframes += result.get('keyframes_extracted', 0)
    
    if total_keyframes > 0:
        print(f"\n🎥 Keyframes:")
        print(f"   🖼️  Total extracted: {total_keyframes}")
        if processed > 0:
            print(f"   📊 Average per summary: {total_keyframes/processed:.1f}")
    
    # Global summary
    print(f"\n🌍 Global Summary:")
    if global_result is None:
        print(f"   ❌ No VTT files found to process")
    elif global_result.get('status') == 'success':
        print(f"   ✅ Generated successfully")
        print(f"   📊 Analyzed {global_result.get('summaries_processed', 0)} summaries")
    elif global_result.get('status') == 'skipped':
        print(f"   ⏭️  Already exists")
    else:
        print(f"   ❌ Error: {global_result.get('error', 'Unknown error')}")
    
    # PDF Report
    print(f"\n📄 PDF Report:")
    if pdf_result.get('status') == 'success':
        print(f"   ✅ PDF generated successfully")
        print(f"   📊 File: {pdf_result.get('pdf_filename', 'Unknown')}")
        if pdf_result.get('consolidated_markdown'):
            markdown_file = Path(pdf_result['consolidated_markdown']).name
            print(f"   📄 Markdown: {markdown_file}")
    elif pdf_result.get('status') == 'markdown_only':
        print(f"   📄 Consolidated markdown created (no PDF converter installed)")
        if pdf_result.get('consolidated_markdown'):
            markdown_file = Path(pdf_result['consolidated_markdown']).name
            print(f"   📄 File: {markdown_file}")
        print(f"   📝 Install pandoc, weasyprint, or wkhtmltopdf for PDF generation")
    elif pdf_result.get('status') == 'disabled':
        print(f"   ⏭️  Disabled in configuration")
    elif pdf_result.get('status') == 'skipped':
        print(f"   ⏭️  Already exists")
    elif pdf_result.get('status') == 'no_summaries':
        print(f"   ⚠️  No summaries available")
    else:
        print(f"   ❌ Failed: {pdf_result.get('error', 'Unknown error')}")
    
    # Model Statistics Summary
    if processor and hasattr(processor, 'performance_tracker'):
        session_stats = processor.performance_tracker.get_session_summary()
        if session_stats['total_calls'] > 0:
            print(f"\n🤖 Model Call Statistics:")
            print(f"   🔢 Total calls: {session_stats['total_calls']} ({session_stats['individual_calls']} individual + {session_stats['analysis_calls']} analysis)")
            print(f"   📊 Total tokens: {session_stats['total_tokens']:,}")
            if session_stats['total_input_tokens'] > 0:
                print(f"   ⬇️  Input tokens: {session_stats['total_input_tokens']:,}")
                print(f"   ⬆️  Output tokens: {session_stats['total_output_tokens']:,}")
            print(f"   ⚡ Average latency: {session_stats['average_latency_ms']:.0f}ms")
            print(f"   🔴 Min/Max latency: {session_stats['min_latency_ms']:.0f}ms / {session_stats['max_latency_ms']:.0f}ms")
    
    # Summary
    print(f"\n📂 Output Location: {results.get('summaries_folder', config.output_folder)}/")
    print(f"⏱️  Total Time: {results.get('total_time', 0)}s")
    
    if results["status"] == "success":
        total_files = processed + skipped
        print(f"\n🎉 Complete! {total_files} individual + 1 global summary ready.")
    else:
        print(f"\n⚠️  Some issues occurred. Check details above.")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Meeting Processor - Process all meeting files and generate summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                 # Process only new files (minimal logging)
  python3 main.py --force         # Force overwrite all existing summaries
  python3 main.py --verbose       # Process with detailed logging
  python3 main.py --no-keyframes  # Skip keyframe extraction
  python3 main.py --max-keyframes 3  # Extract max 3 keyframes per video
        """
    )
    
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Force overwrite existing summary files'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging output'
    )
    
    parser.add_argument(
        '--no-keyframes',
        action='store_true',
        help='Skip keyframe extraction from videos'
    )
    
    parser.add_argument(
        '--max-keyframes',
        type=int,
        default=5,
        help='Maximum number of keyframes to extract per video (default: 5)'
    )
    
    return parser.parse_args()


def main():
    """Main execution function."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging based on verbosity
        setup_logging(verbose=args.verbose)
        
        # Print header
        print_header()
        
        # Load configuration
        print("📋 Loading configuration...")
        config = Config()
        
        # Determine final keyframe settings (CLI overrides config)
        keyframes_enabled = config.keyframes_enabled and not args.no_keyframes
        
        # Use CLI max_keyframes if explicitly provided, otherwise use config
        import sys
        max_keyframes_provided = '--max-keyframes' in sys.argv
        max_keyframes = args.max_keyframes if max_keyframes_provided else config.keyframes_max_frames
        
        # Display basic info
        print(f"📁 Input folder: {config.input_folder}")
        print(f"🤖 Using model: {config.bedrock_model_id}")
        print(f"📂 Output folder: {config.output_folder}")
        if args.force:
            print(f"⚡ Force mode: ON (will overwrite existing files)")
        if args.verbose:
            print(f"🔍 Verbose mode: ON (detailed logging enabled)")
        if config.pdf_enabled:
            print(f"📄 PDF Report: ENABLED")
        else:
            print(f"📄 PDF Report: DISABLED")
        if not keyframes_enabled:
            print(f"🎥 Keyframes: DISABLED")
        else:
            print(f"🎥 Keyframes: ENABLED (max {max_keyframes} per video)")
            if args.verbose:
                print(f"   📊 Min relevance score: {config.keyframes_min_relevance_score}")
                print(f"   🖼️  Image max width: {config.keyframes_image_max_width}px")
        print()
        
        # Initialize and run processor
        print("🚀 Starting meeting processing...")
        
        processor = MeetingProcessor(
            config,
            enable_keyframes=keyframes_enabled,
            max_keyframes=max_keyframes
        )
        results = processor.process_meetings(
            summaries_folder=config.output_folder,
            force_overwrite=args.force
        )
        
        # Print results
        print_results(results, config, processor)
        
        print()
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
