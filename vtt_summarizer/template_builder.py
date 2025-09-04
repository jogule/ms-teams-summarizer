"""Template builder for creating AI prompts from configurable templates."""

from typing import Dict, List, Any, Optional
from .config import Config


class TemplateBuilder:
    """Handles AI prompt template creation and variable substitution."""
    
    def __init__(self, config: Config):
        """
        Initialize the template builder.
        
        Args:
            config: Configuration object with template definitions
        """
        self.config = config
    
    def build_individual_summary_prompt(self, transcript: str, meeting_context: Optional[str] = None) -> str:
        """
        Build an individual meeting summary prompt using configured templates.
        
        Args:
            transcript: The meeting transcript text
            meeting_context: Optional meeting context
            
        Returns:
            Complete formatted prompt string
        """
        # Get base instruction and substitute summary style
        instruction = self.config.prompt_individual_summary_instruction.format(
            summary_style=self.config.summary_style
        )
        
        # Build requirements list based on config settings
        requirements = self._build_individual_requirements()
        
        # Get format instructions
        format_instructions = self.config.prompt_individual_summary_format_instructions
        
        # Build context info
        context_info = f"Meeting Context: {meeting_context}\\n\\n" if meeting_context else ""
        
        # Use the main template to combine everything
        prompt = self.config.prompt_individual_summary_template.format(
            instruction=instruction,
            requirements=requirements,
            format_instructions=format_instructions,
            context_info=context_info,
            transcript=transcript
        )
        
        return prompt
    
    def build_global_summary_prompt(self, summaries: List[Dict[str, Any]]) -> str:
        """
        Build a global meeting analysis prompt using configured templates.
        
        Args:
            summaries: List of individual summary data
            
        Returns:
            Complete formatted prompt string
        """
        # Get instruction
        instruction = self.config.prompt_global_summary_instruction
        
        # Get required sections and format them
        required_sections = "\\n".join(self.config.prompt_global_summary_required_sections)
        
        # Get format instructions
        format_instructions = self.config.prompt_global_summary_format_instructions
        
        # Build meetings overview
        meetings_overview = self._build_meetings_overview(summaries)
        
        # Build combined summaries
        combined_summaries = self._build_combined_summaries(summaries)
        
        # Use the main template to combine everything
        prompt = self.config.prompt_global_summary_template.format(
            instruction=instruction,
            required_sections=required_sections,
            format_instructions=format_instructions,
            meetings_overview=meetings_overview,
            combined_summaries=combined_summaries
        )
        
        return prompt
    
    def _build_individual_requirements(self) -> str:
        """
        Build the requirements section for individual summaries based on config settings.
        
        Returns:
            Formatted requirements string
        """
        requirements = []
        requirement_templates = self.config.prompt_individual_summary_requirements
        
        # Add participants if enabled
        if self.config.include_participants:
            requirements.append(requirement_templates.get('participants', ''))
        
        # Always include core requirements
        requirements.extend([
            requirement_templates.get('main_topics', ''),
            requirement_templates.get('key_points', ''),
            requirement_templates.get('technical_details', '')
        ])
        
        # Add action items if enabled
        if self.config.include_action_items:
            requirements.append(requirement_templates.get('action_items', ''))
        
        # Add more core requirements
        requirements.extend([
            requirement_templates.get('decisions', ''),
            requirement_templates.get('questions_issues', '')
        ])
        
        # Add timeline if enabled
        if self.config.include_timestamps:
            requirements.append(requirement_templates.get('timeline', ''))
        
        # Filter out any empty requirements
        requirements = [req for req in requirements if req]
        
        return "\\n".join(requirements)
    
    def _build_meetings_overview(self, summaries: List[Dict[str, Any]]) -> str:
        """
        Build the meetings overview section for global summaries.
        
        Args:
            summaries: List of individual summary data
            
        Returns:
            Formatted meetings overview string
        """
        meetings_overview = []
        
        for i, summary in enumerate(summaries, 1):
            overview = f"{i}. **{summary['meeting_topic']}** ({summary.get('meeting_date', 'Date unknown')})"
            overview += f"\\n   - Duration: {summary.get('duration', 'Unknown')}"
            overview += f"\\n   - Participants: {len(summary.get('participants', []))} people"
            overview += f"\\n   - Key Topics: {len(summary.get('main_topics', []))} main areas"
            meetings_overview.append(overview)
        
        return "\\n".join(meetings_overview)
    
    def _build_combined_summaries(self, summaries: List[Dict[str, Any]]) -> str:
        """
        Build the combined summaries section for global summaries.
        
        Args:
            summaries: List of individual summary data
            
        Returns:
            Formatted combined summaries string
        """
        combined_parts = []
        
        for summary in summaries:
            header = f"MEETING: {summary['meeting_topic']} ({summary.get('meeting_date', 'Unknown date')})"
            content = summary['content']
            combined_parts.append(f"{header}\\n{content}")
        
        return "\\n\\n" + ("=" * 80 + "\\n\\n").join(combined_parts)
    
    def validate_templates(self) -> List[str]:
        """
        Validate that all required template placeholders are present and properly formatted.
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        
        # Validate individual summary template
        individual_template = self.config.prompt_individual_summary_template
        required_placeholders = ['instruction', 'requirements', 'format_instructions', 'context_info', 'transcript']
        
        for placeholder in required_placeholders:
            if f'{{{placeholder}}}' not in individual_template:
                errors.append(f"Individual summary template missing placeholder: {{{placeholder}}}")
        
        # Validate global summary template
        global_template = self.config.prompt_global_summary_template
        required_global_placeholders = ['instruction', 'required_sections', 'format_instructions', 
                                       'meetings_overview', 'combined_summaries']
        
        for placeholder in required_global_placeholders:
            if f'{{{placeholder}}}' not in global_template:
                errors.append(f"Global summary template missing placeholder: {{{placeholder}}}")
        
        # Validate instruction template
        instruction = self.config.prompt_individual_summary_instruction
        if '{summary_style}' not in instruction:
            errors.append("Individual summary instruction missing placeholder: {summary_style}")
        
        return errors
