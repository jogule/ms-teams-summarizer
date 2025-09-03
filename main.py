#!/usr/bin/env python3
"""
VTT Summarizer - Simple Direct Execution

Just run: python3 main.py

No CLI, no options, just processes all VTT files and generates summaries.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from vtt_summarizer.config import Config
from vtt_summarizer.consolidated_summarizer import ConsolidatedSummarizer


def setup_logging(verbose=False):
    """Set up console logging based on verbosity level."""
    if verbose:
        # Verbose mode: Show INFO level logs from our modules
        logging.getLogger().setLevel(logging.INFO)
        
        # Set our modules to INFO level
        for logger_name in ['vtt_summarizer.consolidated_summarizer', 'vtt_summarizer.bedrock_client', 'vtt_summarizer.global_summarizer']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
        
        # Still suppress AWS SDK logs
        for logger_name in ['botocore', 'boto3', 'urllib3']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
    else:
        # Minimal mode: Suppress all logging except critical errors
        logging.getLogger().setLevel(logging.CRITICAL)
        
        # Suppress all module logs
        for logger_name in ['vtt_summarizer.consolidated_summarizer', 'vtt_summarizer.bedrock_client', 'vtt_summarizer.global_summarizer', 'botocore', 'boto3', 'urllib3']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL)


def print_header():
    """Print a simple header."""
    print("=" * 60)
    print("🚀 VTT SUMMARIZER")
    print("=" * 60)
    print()


def print_results(results):
    """Print results in a simple, clean format."""
    print()
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    individual = results.get("individual_results", {})
    global_result = results.get("global_result", {})
    
    # Individual summaries
    processed = individual.get('processed', 0)
    skipped = individual.get('skipped', 0)
    errors = individual.get('errors', 0)
    
    print(f"📝 Individual Summaries:")
    print(f"   ✅ Processed: {processed}")
    print(f"   ⏭️  Skipped: {skipped}")
    print(f"   ❌ Errors: {errors}")
    
    # Global summary
    print(f"\n🌍 Global Summary:")
    if global_result.get('status') == 'success':
        print(f"   ✅ Generated successfully")
        print(f"   📊 Analyzed {global_result.get('summaries_processed', 0)} summaries")
    elif global_result.get('status') == 'skipped':
        print(f"   ⏭️  Already exists")
    else:
        print(f"   ❌ Failed: {global_result.get('error', 'Unknown error')}")
    
    # Summary
    print(f"\n📂 Output Location: {results.get('summaries_folder', 'summaries')}/")
    print(f"⏱️  Total Time: {results.get('total_time', 0)}s")
    
    if results["status"] == "success":
        total_files = processed + skipped
        print(f"\n🎉 Complete! {total_files} individual + 1 global summary ready.")
    else:
        print(f"\n⚠️  Some issues occurred. Check details above.")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="VTT Summarizer - Process all VTT files and generate summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                 # Process only new files (minimal logging)
  python3 main.py --force         # Force overwrite all existing summaries
  python3 main.py --verbose       # Process with detailed logging
  python3 main.py --force --verbose # Force overwrite with detailed logging
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
        
        # Display basic info
        print(f"📁 Input folder: {config.input_folder}")
        print(f"🤖 Using model: {config.bedrock_model_id}")
        print(f"📂 Output folder: summaries")
        if args.force:
            print(f"⚡ Force mode: ON (will overwrite existing files)")
        if args.verbose:
            print(f"🔍 Verbose mode: ON (detailed logging enabled)")
        print()
        
        # Initialize and run summarizer
        print("🚀 Starting VTT summarization...")
        print("   📄 Processing individual VTT files...")
        
        summarizer = ConsolidatedSummarizer(config)
        results = summarizer.summarize_all(
            summaries_folder="summaries",
            force_overwrite=args.force
        )
        
        print("   🌍 Processing global summary...")
        print("   ✅ All done!")
        
        # Print results
        print_results(results)
        
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
