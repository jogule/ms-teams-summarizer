"""PDF generation module for creating comprehensive meeting summary reports."""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, 
        Table, TableStyle, Image, KeepTogether
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .config import Config
from .utils import (
    safe_read_file, 
    setup_module_logger,
    get_iso_timestamp,
    ProcessingTimer
)


class PDFGenerator:
    """Generates comprehensive PDF reports from meeting summaries."""
    
    def __init__(self, config: Config):
        """
        Initialize the PDF Generator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = setup_module_logger(__name__)
        
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required for PDF generation. "
                "Install with: pip install reportlab"
            )
        
        self.logger.info("PDF Generator initialized")
    
    def generate_comprehensive_pdf(
        self, 
        summaries_path: Path, 
        global_summary_path: Path,
        individual_summaries: List[Dict],
        force_overwrite: bool = False
    ) -> Dict[str, any]:
        """
        Generate comprehensive PDF report with global and individual summaries.
        
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
        
        # Format PDF filename
        pdf_filename = self._format_filename(self.config.pdf_filename)
        pdf_path = summaries_path / pdf_filename
        
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
            self.logger.info(f"Generating comprehensive PDF report: {pdf_filename}")
            
            with ProcessingTimer("PDF generation") as timer:
                # Sort individual summaries chronologically
                sorted_summaries = self._sort_summaries_chronologically(individual_summaries)
                
                # Create PDF document
                self._create_pdf_document(
                    pdf_path, 
                    global_summary_path,
                    sorted_summaries,
                    summaries_path
                )
            
            self.logger.info(f"PDF generation completed in {timer.duration_rounded}s")
            
            return {
                "status": "success",
                "pdf_path": str(pdf_path),
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
    
    def _create_pdf_document(
        self, 
        pdf_path: Path, 
        global_summary_path: Path,
        sorted_summaries: List[Dict],
        summaries_path: Path
    ) -> None:
        """Create the actual PDF document."""
        # Determine page size
        page_size = A4 if self.config.pdf_page_size.upper() == 'A4' else letter
        
        # Create document
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        styles = self._get_styles()
        
        # Title page
        story.extend(self._create_title_page(styles, sorted_summaries))
        story.append(PageBreak())
        
        # Table of contents (if enabled)
        if self.config.pdf_include_table_of_contents:
            story.extend(self._create_table_of_contents(styles, sorted_summaries))
            story.append(PageBreak())
        
        # Global summary
        story.extend(self._add_global_summary(styles, global_summary_path))
        story.append(PageBreak())
        
        # Individual summaries
        for i, summary in enumerate(sorted_summaries):
            story.extend(self._add_individual_summary(
                styles, summary, summaries_path, i + 1
            ))
            if i < len(sorted_summaries) - 1:  # Don't add page break after last summary
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
    
    def _get_styles(self) -> Dict:
        """Get PDF styles."""
        styles = getSampleStyleSheet()
        font_size = self.config.pdf_font_size
        
        custom_styles = {
            'Title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=font_size + 8,
                spaceAfter=30,
                alignment=TA_CENTER
            ),
            'Heading1': ParagraphStyle(
                'CustomHeading1',
                parent=styles['Heading1'],
                fontSize=font_size + 4,
                spaceAfter=12,
                spaceBefore=12,
                textColor=colors.darkblue
            ),
            'Heading2': ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=font_size + 2,
                spaceAfter=8,
                spaceBefore=10,
                textColor=colors.darkgreen
            ),
            'Normal': ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=font_size,
                spaceAfter=6,
                alignment=TA_JUSTIFY
            ),
            'TOC': ParagraphStyle(
                'TOC',
                parent=styles['Normal'],
                fontSize=font_size,
                leftIndent=20,
                spaceAfter=4
            )
        }
        
        return custom_styles
    
    def _create_title_page(self, styles: Dict, summaries: List[Dict]) -> List:
        """Create title page content."""
        content = []
        
        # Main title
        content.append(Paragraph(self.config.pdf_title, styles['Title']))
        content.append(Spacer(1, 0.5*inch))
        
        # Summary statistics
        stats_data = [
            ['Report Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['Total Meetings:', str(len(summaries))],
            ['Date Range:', self._get_date_range(summaries)],
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 3*inch])
        stats_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), self.config.pdf_font_size),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(stats_table)
        content.append(Spacer(1, 1*inch))
        
        # Meeting topics overview
        content.append(Paragraph("Meeting Topics Covered", styles['Heading2']))
        for summary in summaries:
            topic = summary.get('meeting_topic', summary.get('folder_name', 'Unknown'))
            date = summary.get('meeting_date', 'Date unknown')
            content.append(Paragraph(f"• {topic} ({date})", styles['Normal']))
        
        return content
    
    def _create_table_of_contents(self, styles: Dict, summaries: List[Dict]) -> List:
        """Create table of contents."""
        content = []
        
        content.append(Paragraph("Table of Contents", styles['Heading1']))
        content.append(Spacer(1, 0.3*inch))
        
        # Global summary
        content.append(Paragraph("1. Global Summary", styles['TOC']))
        
        # Individual summaries
        for i, summary in enumerate(summaries, 2):
            topic = summary.get('meeting_topic', summary.get('folder_name', 'Unknown'))
            content.append(Paragraph(f"{i}. {topic}", styles['TOC']))
        
        return content
    
    def _add_global_summary(self, styles: Dict, global_summary_path: Path) -> List:
        """Add global summary section."""
        content = []
        
        content.append(Paragraph("Global Summary", styles['Heading1']))
        
        if global_summary_path.exists():
            global_content = safe_read_file(global_summary_path)
            content.extend(self._convert_markdown_to_pdf_content(global_content, styles))
        else:
            content.append(Paragraph("Global summary not available.", styles['Normal']))
        
        return content
    
    def _add_individual_summary(
        self, 
        styles: Dict, 
        summary: Dict, 
        summaries_path: Path,
        chapter_num: int
    ) -> List:
        """Add individual summary section."""
        content = []
        
        # Chapter heading
        topic = summary.get('meeting_topic', summary.get('folder_name', 'Unknown'))
        content.append(Paragraph(f"Chapter {chapter_num}: {topic}", styles['Heading1']))
        
        # Meeting metadata
        metadata_data = []
        if summary.get('meeting_date'):
            metadata_data.append(['Date:', summary['meeting_date']])
        if summary.get('duration'):
            metadata_data.append(['Duration:', summary['duration']])
        if summary.get('participants'):
            participants = ', '.join(summary['participants'][:5])  # Limit to first 5
            if len(summary['participants']) > 5:
                participants += f" and {len(summary['participants']) - 5} others"
            metadata_data.append(['Participants:', participants])
        
        if metadata_data:
            metadata_table = Table(metadata_data, colWidths=[1*inch, 4*inch])
            metadata_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), self.config.pdf_font_size - 1),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            content.append(metadata_table)
            content.append(Spacer(1, 0.2*inch))
        
        # Summary content
        summary_path = Path(summary['summary_path'])
        if summary_path.exists():
            summary_content = safe_read_file(summary_path)
            content.extend(self._convert_markdown_to_pdf_content(summary_content, styles))
            
            # Add keyframes if enabled and available
            if self.config.pdf_include_keyframes:
                keyframe_content = self._add_keyframes_to_pdf(summary_content, summaries_path, styles)
                content.extend(keyframe_content)
        else:
            content.append(Paragraph("Summary content not available.", styles['Normal']))
        
        return content
    
    def _convert_markdown_to_pdf_content(self, markdown_text: str, styles: Dict) -> List:
        """Convert markdown text to PDF content elements."""
        content = []
        lines = markdown_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                content.append(Spacer(1, 6))
                continue
            
            # Headers
            if line.startswith('# '):
                content.append(Paragraph(line[2:], styles['Heading1']))
            elif line.startswith('## '):
                content.append(Paragraph(line[3:], styles['Heading2']))
            elif line.startswith('### '):
                content.append(Paragraph(f"<b>{line[4:]}</b>", styles['Normal']))
            # Bold text
            elif line.startswith('**') and line.endswith('**'):
                content.append(Paragraph(f"<b>{line[2:-2]}</b>", styles['Normal']))
            # List items
            elif line.startswith('- ') or line.startswith('* '):
                content.append(Paragraph(f"• {line[2:]}", styles['Normal']))
            # Regular paragraphs
            elif not line.startswith('!') and not line.startswith('['):  # Skip image refs and links
                # Clean up markdown formatting
                clean_line = self._clean_markdown_formatting(line)
                content.append(Paragraph(clean_line, styles['Normal']))
        
        return content
    
    def _clean_markdown_formatting(self, text: str) -> str:
        """Clean markdown formatting for PDF."""
        # Convert **bold** to <b>bold</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Convert *italic* to <i>italic</i>
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        # Remove markdown links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        return text
    
    def _add_keyframes_to_pdf(self, summary_content: str, summaries_path: Path, styles: Dict) -> List:
        """Add keyframes to PDF if they exist."""
        content = []
        
        # Look for image references in the summary
        image_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', summary_content)
        
        if image_refs:
            content.append(Paragraph("Meeting Screenshots", styles['Heading2']))
            
            for alt_text, image_path in image_refs:
                # Convert relative path to absolute
                if not image_path.startswith('/'):
                    full_image_path = summaries_path / image_path
                else:
                    full_image_path = Path(image_path)
                
                if full_image_path.exists():
                    try:
                        # Add image with caption
                        img = Image(str(full_image_path), width=4*inch, height=3*inch)
                        content.append(img)
                        content.append(Paragraph(f"<i>{alt_text}</i>", styles['Normal']))
                        content.append(Spacer(1, 0.1*inch))
                    except Exception as e:
                        self.logger.warning(f"Could not add image {full_image_path}: {e}")
                        content.append(Paragraph(f"[Image: {alt_text}]", styles['Normal']))
        
        return content
    
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
