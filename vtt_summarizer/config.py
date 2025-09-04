"""Configuration management for VTT Summarizer."""

import os
import yaml
from typing import Dict, Any, List
from pathlib import Path


class Config:
    """Configuration manager for the VTT Summarizer application."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration YAML file. If None, uses default config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    @property
    def aws_region(self) -> str:
        """Get AWS region."""
        return self._config.get('aws', {}).get('region', 'us-east-1')
    
    @property
    def bedrock_model_id(self) -> str:
        """Get Bedrock model ID."""
        return self._config.get('aws', {}).get('bedrock', {}).get('model_id', 
                                'anthropic.claude-3-5-sonnet-20241022-v2:0')
    
    @property
    def bedrock_max_tokens(self) -> int:
        """Get maximum tokens for Bedrock model."""
        return self._config.get('aws', {}).get('bedrock', {}).get('max_tokens', 4000)
    
    @property
    def bedrock_temperature(self) -> float:
        """Get temperature for Bedrock model."""
        return self._config.get('aws', {}).get('bedrock', {}).get('temperature', 0.1)
    
    @property
    def input_folder(self) -> str:
        """Get input folder path."""
        return self._config.get('processing', {}).get('input_folder', 'walkthroughs')
    
    @property
    def output_folder(self) -> str:
        """Get output folder path."""
        return self._config.get('processing', {}).get('output_folder', 'summaries')
    
    @property
    def individual_summary_filename(self) -> str:
        """Get individual summary filename format."""
        return self._config.get('processing', {}).get('individual_summary_filename', '{folder_name}_summary.md')
    
    @property
    def global_summary_filename(self) -> str:
        """Get global summary filename."""
        return self._config.get('processing', {}).get('global_summary_filename', 'global_summary.md')
    
    @property
    def input_file_patterns(self) -> List[str]:
        """Get input file patterns to search for."""
        return self._config.get('processing', {}).get('input_file_patterns', ['*.vtt'])
    
    @property
    def summary_style(self) -> str:
        """Get summary style."""
        return self._config.get('summary', {}).get('style', 'comprehensive')
    
    @property
    def include_timestamps(self) -> bool:
        """Get whether to include timestamps in summary."""
        return self._config.get('summary', {}).get('include_timestamps', True)
    
    @property
    def include_participants(self) -> bool:
        """Get whether to include participants in summary."""
        return self._config.get('summary', {}).get('include_participants', True)
    
    @property
    def include_action_items(self) -> bool:
        """Get whether to include action items in summary."""
        return self._config.get('summary', {}).get('include_action_items', True)
    
    @property
    def logging_level(self) -> str:
        """Get logging level."""
        return self._config.get('logging', {}).get('level', 'INFO')
    
    @property
    def logging_format(self) -> str:
        """Get logging format."""
        return self._config.get('logging', {}).get('format', 
                               '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Keyframe configuration properties
    @property
    def keyframes_enabled(self) -> bool:
        """Get whether keyframe extraction is enabled."""
        return self._config.get('keyframes', {}).get('enabled', True)
    
    @property
    def keyframes_max_frames(self) -> int:
        """Get maximum number of keyframes to extract per video."""
        return self._config.get('keyframes', {}).get('max_frames', 5)
    
    @property
    def keyframes_min_relevance_score(self) -> float:
        """Get minimum relevance score for keyframe candidates."""
        return self._config.get('keyframes', {}).get('min_relevance_score', 0.3)
    
    @property
    def keyframes_image_max_width(self) -> int:
        """Get maximum width for optimized keyframe images."""
        return self._config.get('keyframes', {}).get('image_max_width', 1200)
    
    @property
    def keyframes_image_quality(self) -> int:
        """Get image quality for keyframe optimization."""
        return self._config.get('keyframes', {}).get('image_quality', 85)
    
    @property
    def keyframes_delays(self) -> Dict[str, float]:
        """Get intelligent delay settings for different content types."""
        default_delays = {
            'screen_sharing': 3.0,
            'screen_sharing_immediate': 0.0,
            'demonstrations': 2.0,
            'technical': 1.0,
            'transitions': 2.0,
            'important': 0.5,
            'questions': 1.0
        }
        return self._config.get('keyframes', {}).get('delays', default_delays)
    
    @property
    def keyframes_caption_context_window(self) -> float:
        """Get seconds of additional transcript context before/after keyframe segment."""
        return self._config.get('keyframes', {}).get('caption_context_window', 5.0)
    
    # PDF configuration properties
    @property
    def pdf_enabled(self) -> bool:
        """Get whether PDF generation is enabled."""
        return self._config.get('pdf', {}).get('enabled', True)
    
    @property
    def pdf_filename(self) -> str:
        """Get PDF filename template."""
        return self._config.get('pdf', {}).get('filename', 'complete_summary_report_{date}.pdf')
    
    @property
    def pdf_title(self) -> str:
        """Get PDF document title."""
        return self._config.get('pdf', {}).get('title', 'Meeting Summary Report')
    
    @property
    def pdf_include_table_of_contents(self) -> bool:
        """Get whether to include table of contents in PDF."""
        return self._config.get('pdf', {}).get('include_table_of_contents', True)
    
    @property
    def pdf_include_keyframes(self) -> bool:
        """Get whether to include keyframes in PDF."""
        return self._config.get('pdf', {}).get('include_keyframes', True)
    
    @property
    def pdf_page_size(self) -> str:
        """Get PDF page size."""
        return self._config.get('pdf', {}).get('page_size', 'A4')
    
    @property
    def pdf_font_size(self) -> int:
        """Get PDF base font size."""
        return self._config.get('pdf', {}).get('font_size', 11)
    
    # Prompt template configuration properties
    @property
    def prompt_individual_summary_instruction(self) -> str:
        """Get individual summary instruction template."""
        default = "Please analyze the following meeting transcript and create a {summary_style} summary."
        return self._config.get('prompts', {}).get('individual_summary', {}).get('instruction', default)
    
    @property
    def prompt_individual_summary_requirements(self) -> Dict[str, str]:
        """Get individual summary requirements templates."""
        defaults = {
            'participants': "- **Participants**: List of people who spoke during the meeting",
            'main_topics': "- **Main Topics**: Key subjects discussed during the meeting",
            'key_points': "- **Key Points**: Important information, decisions, and insights shared",
            'technical_details': "- **Technical Details**: Any technical concepts, architectures, or implementations discussed",
            'action_items': "- **Action Items**: Tasks, next steps, or follow-up items mentioned",
            'decisions': "- **Decisions Made**: Any concrete decisions or conclusions reached",
            'questions_issues': "- **Questions/Issues Raised**: Important questions or problems discussed",
            'timeline': "- **Timeline**: Reference key moments with approximate timestamps when significant topics were discussed"
        }
        return self._config.get('prompts', {}).get('individual_summary', {}).get('requirements', defaults)
    
    @property
    def prompt_individual_summary_format_instructions(self) -> str:
        """Get individual summary format instructions."""
        default = "Please format the summary in clear Markdown with appropriate headers and bullet points.\nFocus on technical accuracy and ensure all important information is captured."
        return self._config.get('prompts', {}).get('individual_summary', {}).get('format_instructions', default)
    
    @property
    def prompt_individual_summary_template(self) -> str:
        """Get individual summary complete template."""
        default = "{instruction}\n\nYour summary should include:\n{requirements}\n\n{format_instructions}\n\n{context_info}**Transcript:**\n{transcript}"
        return self._config.get('prompts', {}).get('individual_summary', {}).get('template', default)
    
    @property
    def prompt_global_summary_instruction(self) -> str:
        """Get global summary instruction."""
        default = "Please analyze the following series of technical walkthrough meetings and create a comprehensive global summary."
        return self._config.get('prompts', {}).get('global_summary', {}).get('instruction', default)
    
    @property
    def prompt_global_summary_required_sections(self) -> List[str]:
        """Get global summary required sections."""
        defaults = [
            "- **Executive Summary**: High-level overview of the entire walkthrough series",
            "- **Meeting Series Overview**: List of all meetings with key details",
            "- **Cross-Meeting Themes**: Common themes and patterns across all sessions",
            "- **Technical Architecture Overview**: Overall technical landscape discussed",
            "- **Key Stakeholders**: People involved across multiple sessions",
            "- **Strategic Initiatives**: Major projects and initiatives identified",
            "- **Technology Stack**: Technologies, platforms, and tools discussed",
            "- **Migration & Transformation**: Any migration or modernization efforts",
            "- **Outstanding Issues**: Common problems and challenges across meetings",
            "- **Action Items Summary**: Consolidated action items and next steps",
            "- **Recommendations**: Strategic recommendations based on all meetings"
        ]
        return self._config.get('prompts', {}).get('global_summary', {}).get('required_sections', defaults)
    
    @property
    def prompt_global_summary_format_instructions(self) -> str:
        """Get global summary format instructions."""
        default = "Format the output in clear Markdown with appropriate headers and bullet points.\nFocus on strategic insights and cross-meeting connections rather than individual meeting details."
        return self._config.get('prompts', {}).get('global_summary', {}).get('format_instructions', default)
    
    @property
    def prompt_global_summary_template(self) -> str:
        """Get global summary complete template."""
        default = "{instruction}\n\nYou should provide:\n{required_sections}\n\n{format_instructions}\n\n**Meeting Series Overview:**\n{meetings_overview}\n\n**Individual Meeting Summaries for Analysis:**\n{combined_summaries}"
        return self._config.get('prompts', {}).get('global_summary', {}).get('template', default)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key (e.g., 'aws.region')."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
