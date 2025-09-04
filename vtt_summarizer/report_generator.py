"""Report generation module for creating comprehensive meeting reports in multiple formats."""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Check for markdown to PDF converters
MARKDOWN_TO_PDF_AVAILABLE = False
CONVERTER_COMMAND = None

# Try different markdown to PDF converters in order of preference
CONVERTERS = [
    ('pandoc', ['pandoc', '--version']),
    ('weasyprint', ['weasyprint', '--version']),
    ('wkhtmltopdf', ['wkhtmltopdf', '--version'])
]

for converter, test_cmd in CONVERTERS:
    try:
        subprocess.run(test_cmd, capture_output=True, check=True)
        CONVERTER_COMMAND = converter
        MARKDOWN_TO_PDF_AVAILABLE = True
        break
    except (subprocess.CalledProcessError, FileNotFoundError):
        continue

from .config import Config
from .utils import (
    safe_read_file, 
    safe_write_file,
    setup_module_logger,
    get_iso_timestamp,
    ProcessingTimer
)


class ReportGenerator:
    """Generates comprehensive reports in multiple formats from meeting summaries."""
    
    def __init__(self, config: Config):
        """
        Initialize the Report Generator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = setup_module_logger(__name__)
        
        if not MARKDOWN_TO_PDF_AVAILABLE:
            self.logger.warning(
                f"No markdown to PDF converter found. Install one of: {[c[0] for c in CONVERTERS]}. "
                "PDF generation will create consolidated markdown only."
            )
        else:
            self.logger.info(f"Report Generator initialized using {CONVERTER_COMMAND}")
    
    def generate_comprehensive_pdf(
        self, 
        summaries_path: Path, 
        global_summary_path: Path,
        individual_summaries: List[Dict],
        force_overwrite: bool = False
    ) -> Dict[str, any]:
        """
        Generate comprehensive PDF report via consolidated markdown approach.
        
        Args:
            summaries_path: Path to summaries directory
            global_summary_path: Path to global summary file
            individual_summaries: List of individual summary metadata
            force_overwrite: Whether to overwrite existing PDF
            
        Returns:
            Dictionary with generation results
        """
        if not self.config.pdf_enabled:
            return {
                "status": "disabled",
                "message": "PDF generation is disabled in configuration"
            }
        
        # Format filenames
        pdf_filename = self._format_filename(self.config.pdf_filename)
        pdf_path = summaries_path / pdf_filename
        markdown_filename = pdf_filename.replace('.pdf', '_consolidated.md')
        markdown_path = summaries_path / markdown_filename
        
        # Check if PDF already exists
        if pdf_path.exists() and not force_overwrite:
            self.logger.info("PDF report already exists, skipping")
            return {
                "status": "skipped",
                "message": "PDF report already exists",
                "pdf_path": str(pdf_path),
                "timestamp": get_iso_timestamp()
            }
        
        try:
            self.logger.info(f"Generating consolidated markdown and PDF report: {pdf_filename}")
            
            with ProcessingTimer("PDF generation") as timer:
                # Sort individual summaries chronologically
                sorted_summaries = self._sort_summaries_chronologically(individual_summaries)
                
                # Step 1: Create consolidated markdown file
                self.logger.info("Creating consolidated markdown file...")
                self._create_consolidated_markdown(
                    markdown_path,
                    global_summary_path,
                    sorted_summaries,
                    summaries_path
                )
                
                # Step 2: Convert markdown to PDF
                if MARKDOWN_TO_PDF_AVAILABLE:
                    self.logger.info(f"Converting markdown to PDF using {CONVERTER_COMMAND}...")
                    success = self._convert_markdown_to_pdf(markdown_path, pdf_path)
                    if not success:
                        return {
                            "status": "error",
                            "error": "Markdown to PDF conversion failed",
                            "consolidated_markdown": str(markdown_path),
                            "timestamp": get_iso_timestamp()
                        }
                else:
                    self.logger.info("No PDF converter available, created consolidated markdown only")
                    return {
                        "status": "markdown_only",
                        "message": "Created consolidated markdown file (no PDF converter available)",
                        "consolidated_markdown": str(markdown_path),
                        "summaries_included": len(sorted_summaries),
                        "generation_time": timer.duration_rounded,
                        "timestamp": get_iso_timestamp()
                    }
            
            self.logger.info(f"PDF generation completed in {timer.duration_rounded}s")
            
            return {
                "status": "success",
                "pdf_path": str(pdf_path),
                "consolidated_markdown": str(markdown_path),
                "pdf_filename": pdf_filename,
                "generation_time": timer.duration_rounded,
                "summaries_included": len(sorted_summaries),
                "timestamp": get_iso_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating PDF report: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": get_iso_timestamp()
            }
    
    def _format_filename(self, template: str) -> str:
        """Format PDF filename template with variables."""
        format_vars = {
            'timestamp': get_iso_timestamp().replace(':', '-').replace('T', '_'),
            'date': datetime.now().strftime('%Y-%m-%d'),
        }
        return template.format(**format_vars)
    
    def _sort_summaries_chronologically(self, summaries: List[Dict]) -> List[Dict]:
        """Sort summaries by date, with fallback to folder name."""
        def sort_key(summary):
            # Try to use meeting_date first
            if summary.get('meeting_date'):
                return summary['meeting_date']
            # Fall back to folder name which often contains dates
            return summary.get('folder_name', 'z')
        
        return sorted(summaries, key=sort_key)
    
    def _create_consolidated_markdown(
        self,
        markdown_path: Path,
        global_summary_path: Path,
        sorted_summaries: List[Dict],
        summaries_path: Path
    ) -> None:
        """
        Create a consolidated markdown file with all summaries.
        
        Args:
            markdown_path: Path where to save consolidated markdown
            global_summary_path: Path to global summary file
            sorted_summaries: List of individual summaries sorted chronologically
            summaries_path: Path to summaries directory
        """
        content_parts = []
        
        # Document title and metadata
        content_parts.append(f"# {self.config.pdf_title}")
        content_parts.append("")
        content_parts.append(f"**Report Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        content_parts.append(f"**Total Meetings:** {len(sorted_summaries)}")
        content_parts.append(f"**Date Range:** {self._get_date_range(sorted_summaries)}")
        content_parts.append("")
        
        # Table of contents
        if self.config.pdf_include_table_of_contents:
            content_parts.append("## Table of Contents")
            content_parts.append("")
            global_summary_slug = self._generate_markdown_slug("Global Summary")
            content_parts.append(f"1. [Global Summary](#{global_summary_slug})")
            for i, summary in enumerate(sorted_summaries, 1):
                topic = self._extract_meeting_topic(summary)
                # Generate slug that matches the actual chapter heading "Chapter X: Topic"
                chapter_title = f"Chapter {i}: {topic}"
                safe_slug = self._generate_markdown_slug(chapter_title)
                # Use i+1 for TOC numbering since Global Summary takes position 1
                content_parts.append(f"{i+1}. [{topic}](#{safe_slug})")
            content_parts.append("")
            content_parts.append("---")
            content_parts.append("")
        
        # Global summary section
        content_parts.append("# Global Summary")
        content_parts.append("")
        
        if global_summary_path.exists():
            global_content = safe_read_file(global_summary_path)
            # Remove the title from global content as we have our own
            cleaned_global = self._clean_summary_content(global_content, remove_title=True)
            content_parts.append(cleaned_global)
        else:
            content_parts.append("Global summary not available.")
        
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        
        # Individual summary sections
        for i, summary in enumerate(sorted_summaries, 1):
            topic = self._extract_meeting_topic(summary)
            content_parts.append(f"# Chapter {i}: {topic}")
            content_parts.append("")
            
            # Add meeting metadata
            if summary.get('meeting_date'):
                content_parts.append(f"**Date:** {summary['meeting_date']}")
            if summary.get('duration'):
                content_parts.append(f"**Duration:** {summary['duration']}")
            if summary.get('participants'):
                participants = ', '.join(summary['participants'][:5])
                if len(summary['participants']) > 5:
                    participants += f" and {len(summary['participants']) - 5} others"
                content_parts.append(f"**Participants:** {participants}")
            
            if any([summary.get('meeting_date'), summary.get('duration'), summary.get('participants')]):
                content_parts.append("")
            
            # Add summary content
            summary_path = Path(summary['summary_path'])
            if summary_path.exists():
                summary_content = safe_read_file(summary_path)
                cleaned_content = self._clean_summary_content(summary_content)
                content_parts.append(cleaned_content)
            else:
                content_parts.append("Summary content not available.")
            
            content_parts.append("")
            if i < len(sorted_summaries):  # Don't add separator after last chapter
                content_parts.append("---")
                content_parts.append("")
        
        # Write consolidated markdown
        consolidated_content = "\n".join(content_parts)
        safe_write_file(markdown_path, consolidated_content)
        
        self.logger.info(f"Created consolidated markdown file: {markdown_path}")
    
    def _convert_markdown_to_pdf(self, markdown_path: Path, pdf_path: Path) -> bool:
        """
        Convert markdown file to PDF using available converter.
        
        Args:
            markdown_path: Path to source markdown file
            pdf_path: Path where to save PDF
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            if CONVERTER_COMMAND == 'pandoc':
                # Pandoc with good PDF options
                # Use relative paths since we're running from the markdown directory
                markdown_filename = markdown_path.name
                pdf_filename = pdf_path.name
                cmd = [
                    'pandoc',
                    '--from=markdown',
                    markdown_filename,
                    '-o', pdf_filename,
                    '--pdf-engine=xelatex',
                    '--variable', 'geometry:margin=1in',
                    '--variable', 'fontsize=11pt',
                    '--variable', 'documentclass=article',
                    '--variable', 'linestretch=1.2',
                ]
                
                # Add TOC if enabled
                if self.config.pdf_include_table_of_contents:
                    cmd.append('--table-of-contents')
                
                cmd.extend(['--highlight-style=tango'])
                
            elif CONVERTER_COMMAND == 'weasyprint':
                # WeasyPrint
                cmd = ['weasyprint', str(markdown_path), str(pdf_path)]
                
            elif CONVERTER_COMMAND == 'wkhtmltopdf':
                # wkhtmltopdf
                cmd = [
                    'wkhtmltopdf',
                    '--page-size', 'A4',
                    '--margin-top', '1in',
                    '--margin-bottom', '1in',
                    '--margin-left', '1in',
                    '--margin-right', '1in',
                    str(markdown_path),
                    str(pdf_path)
                ]
            else:
                self.logger.error(f"Unknown converter: {CONVERTER_COMMAND}")
                return False
            
            self.logger.info(f"Running command: {' '.join(cmd)}")
            # Run pandoc from the directory containing the markdown file so relative image paths work
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=markdown_path.parent)
            
            if pdf_path.exists():
                self.logger.info(f"Successfully converted markdown to PDF: {pdf_path}")
                return True
            else:
                self.logger.error("PDF conversion completed but file not found")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"PDF conversion failed: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error during PDF conversion: {str(e)}")
            return False
    
    def _clean_summary_content(self, content: str, remove_title: bool = False) -> str:
        """
        Clean summary content for consolidation.
        
        Args:
            content: Original summary content
            remove_title: Whether to remove the title line
            
        Returns:
            Cleaned content
        """
        lines = content.split('\n')
        cleaned_lines = []
        
        skip_until_summary = remove_title
        
        for i, line in enumerate(lines):
            # Skip title and meeting info if requested
            if skip_until_summary:
                if line.strip().startswith('## Summary') or line.strip().startswith('## Analysis'):
                    skip_until_summary = False
                    cleaned_lines.append(line)
                elif line.strip() and not line.startswith('#') and not line.startswith('**') and not line.startswith('-'):
                    # Found content, include it
                    skip_until_summary = False
                    cleaned_lines.append(line)
                continue
            
            # Skip metadata lines at the start
            if (line.startswith('**Date Generated**') or
                line.startswith('**Duration**') or
                line.startswith('**Transcript Words**') or
                line.startswith('**Source File**') or
                line.startswith('## Meeting Information')):
                continue
            
            # Fix image paths - convert relative paths to absolute paths
            if line.strip().startswith('![') and '](images/' in line:
                # Replace images/ with ./images/ to make it relative to the markdown file location
                line = line.replace('](images/', '](./images/')
            
            cleaned_lines.append(line)
            
            # Add blank line after bold headers if the next line is a bullet point
            # This ensures proper markdown list formatting for pandoc
            if (line.strip().startswith('**') and line.strip().endswith(':**') and 
                i + 1 < len(lines) and lines[i + 1].strip().startswith('-')):
                cleaned_lines.append('')  # Add blank line
        
        return '\n'.join(cleaned_lines).strip()
    
    def _get_date_range(self, summaries: List[Dict]) -> str:
        """Get date range string for summaries."""
        dates = [s.get('meeting_date') for s in summaries if s.get('meeting_date')]
        
        if not dates:
            return "Date range unknown"
        
        dates.sort()
        if len(dates) == 1:
            return dates[0]
        else:
            return f"{dates[0]} to {dates[-1]}"
    
    def _extract_meeting_topic(self, summary: Dict) -> str:
        """Extract meeting topic from summary data with fallbacks."""
        # Try different sources for meeting topic
        
        # 1. Direct meeting_topic field
        if summary.get('meeting_topic') and summary['meeting_topic'] != 'Unknown':
            return summary['meeting_topic']
        
        # 2. Parse folder name for meaningful content
        folder_name = summary.get('folder_name', '')
        if folder_name and folder_name != 'Unknown':
            # Clean up folder name - remove dates and make readable
            topic = self._clean_folder_name_for_topic(folder_name)
            if topic != 'Unknown':
                return topic
        
        # 3. Try to extract from summary file content
        summary_path = summary.get('summary_path')
        if summary_path:
            try:
                content = safe_read_file(Path(summary_path))
                topic = self._extract_topic_from_content(content)
                if topic:
                    return topic
            except:
                pass
        
        # 4. Fallback to folder name or default
        return folder_name if folder_name else 'Meeting Session'
    
    def _clean_folder_name_for_topic(self, folder_name: str) -> str:
        """Clean folder name to extract meaningful topic."""
        # Remove common date patterns
        import re
        
        # Remove date patterns like 20250815, 2025-08-15, etc.
        cleaned = re.sub(r'\d{8}', '', folder_name)  # 20250815
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}', '', cleaned)  # 2025-08-15
        cleaned = re.sub(r'\d{2}-\d{2}-\d{4}', '', cleaned)  # 15-08-2025
        cleaned = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '', cleaned)  # 8/15/2025
        
        # Remove leading/trailing separators
        cleaned = re.sub(r'^[-_\s]+', '', cleaned)
        cleaned = re.sub(r'[-_\s]+$', '', cleaned)
        
        # Replace underscores and multiple spaces with single spaces
        cleaned = re.sub(r'[-_]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Capitalize words
        cleaned = cleaned.strip().title()
        
        return cleaned if cleaned and len(cleaned) > 2 else 'Meeting Session'
    
    def _extract_topic_from_content(self, content: str) -> str:
        """Extract topic from summary content."""
        lines = content.split('\n')
        
        # Look for title line (first non-metadata line that looks like a title)
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if (line and 
                not line.startswith('#') and 
                not line.startswith('**') and 
                not line.startswith('-') and 
                not line.startswith('*This summary') and
                len(line) > 10 and 
                len(line) < 100 and
                not ':' in line[-20:]):  # Avoid lines ending with colons (likely metadata)
                # Clean the line
                topic = re.sub(r'[*_`]', '', line)  # Remove markdown
                topic = topic.replace(' - Meeting Summary', '')
                topic = topic.replace(' Meeting Summary', '')
                topic = topic.replace('Meeting Summary', '')
                topic = topic.strip()
                if len(topic) > 5:
                    return topic
        
        return None
    
    def _generate_markdown_slug(self, text: str) -> str:
        """
        Generate markdown-compatible slug from text that matches how 
        markdown processors create anchor IDs from headings.
        
        Args:
            text: The heading text to convert to a slug
            
        Returns:
            URL-safe slug string
        """
        import re
        
        # Convert to lowercase
        slug = text.lower()
        
        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug)
        
        # Remove or replace special characters (keep alphanumeric and hyphens)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        return slug
