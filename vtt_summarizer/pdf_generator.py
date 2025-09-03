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
        """Get PDF styles that match rendered markdown appearance."""
        styles = getSampleStyleSheet()
        font_size = self.config.pdf_font_size
        
        custom_styles = {
            'Title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=font_size + 10,
                spaceAfter=30,
                spaceBefore=20,
                alignment=TA_CENTER,
                textColor=colors.darkblue,
                fontName='Helvetica-Bold'
            ),
            'Heading1': ParagraphStyle(
                'CustomHeading1',
                parent=styles['Heading1'],
                fontSize=font_size + 6,
                spaceAfter=8,
                spaceBefore=16,
                textColor=colors.black,
                fontName='Helvetica-Bold',
                borderWidth=0,
                borderColor=colors.lightgrey,
                borderPadding=2
            ),
            'Heading2': ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=font_size + 4,
                spaceAfter=6,
                spaceBefore=12,
                textColor=colors.black,
                fontName='Helvetica-Bold'
            ),
            'Heading3': ParagraphStyle(
                'CustomHeading3',
                parent=styles['Heading2'],
                fontSize=font_size + 2,
                spaceAfter=4,
                spaceBefore=8,
                textColor=colors.black,
                fontName='Helvetica-Bold'
            ),
            'Normal': ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=font_size,
                spaceAfter=0,
                spaceBefore=0,
                alignment=TA_LEFT,
                fontName='Helvetica',
                leading=font_size + 3  # Line spacing
            ),
            'BulletList': ParagraphStyle(
                'BulletList',
                parent=styles['Normal'],
                fontSize=font_size,
                leftIndent=18,
                bulletIndent=12,
                spaceAfter=2,
                spaceBefore=1,
                alignment=TA_LEFT,
                fontName='Helvetica',
                leading=font_size + 2
            ),
            'NumberedList': ParagraphStyle(
                'NumberedList',
                parent=styles['Normal'],
                fontSize=font_size,
                leftIndent=18,
                spaceAfter=2,
                spaceBefore=1,
                alignment=TA_LEFT,
                fontName='Helvetica',
                leading=font_size + 2
            ),
            'Code': ParagraphStyle(
                'Code',
                parent=styles['Normal'],
                fontSize=font_size - 1,
                fontName='Courier',
                backgroundColor=colors.lightgrey,
                borderWidth=1,
                borderColor=colors.grey,
                borderPadding=6,
                leftIndent=12,
                rightIndent=12,
                spaceAfter=6,
                spaceBefore=6
            ),
            'Quote': ParagraphStyle(
                'Quote',
                parent=styles['Normal'],
                fontSize=font_size,
                fontName='Helvetica-Oblique',
                leftIndent=24,
                rightIndent=12,
                borderColor=colors.lightgrey,
                borderWidth=2,
                borderPadding=8,
                spaceAfter=8,
                spaceBefore=8,
                textColor=colors.darkgrey
            ),
            'TOC': ParagraphStyle(
                'TOC',
                parent=styles['Normal'],
                fontSize=font_size,
                leftIndent=20,
                spaceAfter=4,
                fontName='Helvetica'
            )
        }
        
        return custom_styles
    
    def _create_title_page(self, styles: Dict, summaries: List[Dict]) -> List:
        """Create professional title page content."""
        content = []
        
        # Add some top spacing
        content.append(Spacer(1, 1.5*inch))
        
        # Main title
        content.append(Paragraph(self.config.pdf_title, styles['Title']))
        content.append(Spacer(1, 0.3*inch))
        
        # Subtitle
        subtitle = f"Comprehensive Analysis of {len(summaries)} Meeting Sessions"
        content.append(Paragraph(subtitle, styles['Heading2']))
        content.append(Spacer(1, 0.8*inch))
        
        # Summary statistics in a nice table
        stats_data = [
            ['📅 Report Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['📊 Total Meetings:', str(len(summaries))],
            ['📆 Date Range:', self._get_date_range(summaries)],
            ['📄 Document Pages:', 'Multiple chapters with analysis'],
        ]
        
        stats_table = Table(stats_data, colWidths=[2.2*inch, 3.5*inch])
        stats_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), self.config.pdf_font_size),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        content.append(stats_table)
        content.append(Spacer(1, 0.8*inch))
        
        # Meeting topics overview with better formatting
        content.append(Paragraph("📋 Meeting Sessions Included", styles['Heading2']))
        content.append(Spacer(1, 0.2*inch))
        
        for i, summary in enumerate(summaries, 1):
            # Try multiple ways to get meeting topic
            topic = self._extract_meeting_topic(summary)
            date = summary.get('meeting_date', 'Date unknown')
            duration = summary.get('duration', 'Duration unknown')
            
            meeting_info = f"{i}. <b>{topic}</b>"
            if date != 'Date unknown':
                meeting_info += f" • {date}"
            if duration != 'Duration unknown':
                meeting_info += f" • {duration}"
                
            content.append(Paragraph(meeting_info, styles['BulletList']))
            content.append(Spacer(1, 2))
        
        content.append(Spacer(1, 0.5*inch))
        
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
        topic = self._extract_meeting_topic(summary)
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
            
            # Extract just the summary section (skip the header metadata)
            clean_content = self._extract_summary_section(summary_content)
            content.extend(self._convert_markdown_to_pdf_content(clean_content, styles))
            
            # Add keyframes if enabled and available
            if self.config.pdf_include_keyframes:
                keyframe_content = self._add_keyframes_to_pdf(summary_content, summaries_path, styles)
                content.extend(keyframe_content)
        else:
            content.append(Paragraph("Summary content not available.", styles['Normal']))
        
        return content
    
    def _convert_markdown_to_pdf_content(self, markdown_text: str, styles: Dict) -> List:
        """Convert markdown text to PDF content elements with proper formatting."""
        content = []
        lines = markdown_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Skip empty lines but add spacing
            if not line:
                content.append(Spacer(1, 6))
                i += 1
                continue
            
            # Skip certain metadata lines that are already handled elsewhere
            if (line.startswith('*This summary was generated') or 
                line.startswith('---') or
                line.startswith('**Date Generated**') or
                line.startswith('**Duration**') or
                line.startswith('**Transcript Words**') or
                line.startswith('**Source File**')):
                i += 1
                continue
            
            # Headers with proper spacing
            if line.startswith('# '):
                content.append(Spacer(1, 12))
                content.append(Paragraph(self._clean_markdown_formatting(line[2:]), styles['Heading1']))
                content.append(Spacer(1, 6))
            elif line.startswith('## '):
                content.append(Spacer(1, 10))
                content.append(Paragraph(self._clean_markdown_formatting(line[3:]), styles['Heading2']))
                content.append(Spacer(1, 4))
            elif line.startswith('### '):
                content.append(Spacer(1, 8))
                content.append(Paragraph(f"<b>{self._clean_markdown_formatting(line[4:])}</b>", styles['Heading3']))
                content.append(Spacer(1, 2))
            elif line.startswith('#### '):
                content.append(Spacer(1, 6))
                content.append(Paragraph(f"<b><i>{self._clean_markdown_formatting(line[5:])}</i></b>", styles['Normal']))
                
            # Multi-line lists (collect consecutive list items)
            elif line.startswith('- ') or line.startswith('* ') or line.startswith('+ '):
                list_items = []
                while i < len(lines) and (lines[i].startswith('- ') or lines[i].startswith('* ') or lines[i].startswith('+ ') or lines[i].startswith('  ')):
                    current_line = lines[i].rstrip()
                    if current_line.startswith(('- ', '* ', '+ ')):
                        list_items.append(current_line[2:])
                    elif current_line.startswith('  ') and list_items:  # Continuation of previous item
                        list_items[-1] += ' ' + current_line.strip()
                    i += 1
                
                # Add list items
                for item in list_items:
                    clean_item = self._clean_markdown_formatting(item)
                    content.append(Paragraph(f"• {clean_item}", styles['BulletList']))
                i -= 1  # Adjust because we'll increment at the end of the loop
                
            # Numbered lists
            elif self._is_numbered_list_item(line):
                list_items = []
                while i < len(lines) and (self._is_numbered_list_item(lines[i]) or lines[i].startswith('  ')):
                    current_line = lines[i].rstrip()
                    if self._is_numbered_list_item(current_line):
                        # Extract the number and content
                        parts = current_line.split('.', 1)
                        if len(parts) == 2:
                            list_items.append((parts[0].strip(), parts[1].strip()))
                    elif current_line.startswith('  ') and list_items:  # Continuation
                        list_items[-1] = (list_items[-1][0], list_items[-1][1] + ' ' + current_line.strip())
                    i += 1
                
                # Add numbered list items
                for num, item in list_items:
                    clean_item = self._clean_markdown_formatting(item)
                    content.append(Paragraph(f"{num}. {clean_item}", styles['NumberedList']))
                i -= 1
                
            # Code blocks
            elif line.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if code_lines:
                    code_text = '\n'.join(code_lines)
                    content.append(Paragraph(f"<font name='Courier'>{code_text}</font>", styles['Code']))
                    content.append(Spacer(1, 6))
                    
            # Block quotes
            elif line.startswith('> '):
                quote_lines = []
                while i < len(lines) and lines[i].startswith('> '):
                    quote_lines.append(lines[i][2:])
                    i += 1
                quote_text = ' '.join(quote_lines)
                clean_quote = self._clean_markdown_formatting(quote_text)
                content.append(Paragraph(f"<i>\"{clean_quote}\"</i>", styles['Quote']))
                content.append(Spacer(1, 6))
                i -= 1
                
            # Tables (basic support)
            elif '|' in line and not line.startswith('!'):
                table_lines = []
                while i < len(lines) and '|' in lines[i] and not lines[i].startswith('!'):
                    table_lines.append(lines[i])
                    i += 1
                if len(table_lines) > 1:  # Skip single-line tables
                    table_content = self._create_table_from_markdown(table_lines, styles)
                    if table_content:
                        content.extend(table_content)
                i -= 1
                
            # Regular paragraphs
            elif not line.startswith('!') and not line.startswith('[') and not line.startswith('<'):
                # Collect multi-line paragraphs
                paragraph_lines = [line]
                i += 1
                while (i < len(lines) and 
                       lines[i].strip() and 
                       not lines[i].startswith('#') and 
                       not lines[i].startswith('-') and 
                       not lines[i].startswith('*') and 
                       not lines[i].startswith('+') and 
                       not self._is_numbered_list_item(lines[i]) and
                       not lines[i].startswith('```') and
                       not lines[i].startswith('> ') and
                       '|' not in lines[i]):
                    paragraph_lines.append(lines[i].strip())
                    i += 1
                
                paragraph_text = ' '.join(paragraph_lines)
                clean_paragraph = self._clean_markdown_formatting(paragraph_text)
                if clean_paragraph.strip():  # Only add non-empty paragraphs
                    content.append(Paragraph(clean_paragraph, styles['Normal']))
                    content.append(Spacer(1, 3))
                i -= 1
            
            i += 1
        
        return content
    
    def _clean_markdown_formatting(self, text: str) -> str:
        """Clean markdown formatting for PDF with proper HTML tags."""
        # Convert **bold** to <b>bold</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Convert *italic* to <i>italic</i> (but not if it's already in bold)
        text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
        # Convert `inline code` to <font name='Courier'>code</font>
        text = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', text)
        # Remove markdown links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Convert --- to em dash
        text = text.replace('---', '—')
        # Convert -- to en dash
        text = text.replace('--', '–')
        # Clean up any double spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _is_numbered_list_item(self, line: str) -> bool:
        """Check if line is a numbered list item."""
        return bool(re.match(r'^\d+\.\s+', line.strip()))
    
    def _create_table_from_markdown(self, table_lines: List[str], styles: Dict) -> List:
        """Create a table from markdown table lines."""
        if len(table_lines) < 2:
            return []
        
        # Parse table data
        table_data = []
        for line in table_lines:
            if '|' in line:
                # Split by | and clean up
                cells = [cell.strip() for cell in line.split('|')]
                # Remove empty first/last cells if they exist
                if cells and not cells[0]:
                    cells = cells[1:]
                if cells and not cells[-1]:
                    cells = cells[:-1]
                # Skip separator lines (lines with mostly dashes)
                if not all(cell.replace('-', '').replace(':', '').replace(' ', '') == '' for cell in cells):
                    # Clean markdown formatting in cells
                    clean_cells = [self._clean_markdown_formatting(cell) for cell in cells]
                    table_data.append(clean_cells)
        
        if len(table_data) < 1:
            return []
        
        # Create table
        try:
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header row
                ('FONTSIZE', (0, 0), (-1, -1), self.config.pdf_font_size - 1),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            return [table, Spacer(1, 6)]
        except:
            # If table creation fails, return as regular paragraphs
            content = []
            for row in table_data:
                content.append(Paragraph(' | '.join(row), styles['Normal']))
            return content
    
    def _extract_summary_section(self, markdown_text: str) -> str:
        """Extract just the summary content, skipping metadata headers."""
        lines = markdown_text.split('\n')
        
        # Find where the actual summary starts (after meeting information)
        summary_start = 0
        for i, line in enumerate(lines):
            # Look for ## Summary or similar pattern
            if (line.strip().startswith('## Summary') or 
                line.strip().startswith('# Summary') or
                (i > 10 and line.strip().startswith('##') and 'summary' in line.lower())):
                summary_start = i
                break
            # Alternative: if we find content that looks like summary content
            elif (i > 5 and line.strip() and 
                  not line.startswith('#') and 
                  not line.startswith('**') and 
                  not line.startswith('-') and
                  not line.startswith('*This summary was generated') and
                  len(line.strip()) > 50):
                summary_start = max(0, i - 1)  # Include a bit of context
                break
        
        # If no clear summary section found, return everything after first few metadata lines
        if summary_start == 0:
            for i, line in enumerate(lines):
                if i > 8:  # Skip first several lines which are usually metadata
                    summary_start = i
                    break
        
        return '\n'.join(lines[summary_start:])
    
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
