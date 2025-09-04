# Prompt Template Customization

The VTT Summarizer now supports fully customizable prompt templates through the `config.yaml` file. This allows you to tailor how the AI analyzes and summarizes your meetings without modifying any code.

## Overview

All prompt templates are configured in the `prompts` section of `config.yaml`. The system supports two main types of prompts:

1. **Individual Summary Prompts** - For analyzing single meeting transcripts
2. **Global Summary Prompts** - For analyzing multiple meetings together

## Configuration Structure

```yaml
prompts:
  individual_summary:
    instruction: "Main analysis instruction with {summary_style} placeholder"
    requirements:
      participants: "Template for participants section"
      main_topics: "Template for main topics section"
      # ... other requirement templates
    format_instructions: "Instructions for output formatting"
    template: "Complete prompt template with placeholders"
  
  global_summary:
    instruction: "Global analysis instruction"
    required_sections: ["List", "of", "required", "sections"]
    format_instructions: "Global formatting instructions"
    template: "Global prompt template with placeholders"
```

## Template Placeholders

### Individual Summary Placeholders
- `{summary_style}` - Replaced with the configured summary style (comprehensive, brief, detailed)
- `{requirements}` - Replaced with dynamically built requirements based on config settings
- `{format_instructions}` - Replaced with formatting instructions
- `{context_info}` - Replaced with meeting context (if provided)
- `{transcript}` - Replaced with the actual meeting transcript

### Global Summary Placeholders
- `{instruction}` - Replaced with the main instruction
- `{required_sections}` - Replaced with the list of required sections
- `{format_instructions}` - Replaced with formatting instructions
- `{meetings_overview}` - Replaced with auto-generated meetings overview
- `{combined_summaries}` - Replaced with all individual meeting summaries

## Customization Examples

### 1. Changing Analysis Focus

To focus on technical architecture:
```yaml
prompts:
  individual_summary:
    instruction: "As a senior software architect, analyze this meeting transcript and create a {summary_style} technical architecture summary."
```

### 2. Custom Requirements

To add custom requirement templates:
```yaml
prompts:
  individual_summary:
    requirements:
      participants: "- **Meeting Attendees**: List all participants with their roles and departments"
      technical_details: "- **System Architecture**: Detailed analysis of system designs, APIs, and data flows discussed"
      security_concerns: "- **Security Considerations**: Any security-related discussions or requirements"
```

### 3. Custom Output Format

To change the output structure:
```yaml
prompts:
  individual_summary:
    format_instructions: |
      Format your response as a structured technical report with:
      - Executive summary at the top
      - Technical sections with code examples
      - Risk assessment section
      - Clear action items with owners and deadlines
```

### 4. Role-Based Analysis

For different team perspectives:
```yaml
# For Engineering Teams
prompts:
  individual_summary:
    instruction: "As a lead engineer, analyze this technical meeting and create a {summary_style} engineering-focused summary."

# For Product Teams  
prompts:
  individual_summary:
    instruction: "As a product manager, analyze this meeting transcript and create a {summary_style} product-focused summary with emphasis on user impact and business value."

# For Architecture Teams
prompts:
  individual_summary:
    instruction: "As a solution architect, analyze this design review and create a {summary_style} architecture summary focusing on system design and technical decisions."
```

## Dynamic Requirements

The system automatically includes or excludes requirement sections based on your configuration:

```yaml
summary:
  include_participants: true    # Includes participants requirement
  include_timestamps: true      # Includes timeline requirement
  include_action_items: true    # Includes action items requirement
```

## Global Summary Customization

Customize how multiple meetings are analyzed together:

```yaml
prompts:
  global_summary:
    instruction: "As a technical program manager, analyze this meeting series to identify program-level patterns and strategic technical decisions."
    required_sections:
      - "- **Program Overview**: High-level summary of the technical program"
      - "- **Architecture Evolution**: How designs evolved across meetings"
      - "- **Risk Assessment**: Technical and program risks identified"
      - "- **Resource Planning**: Resource needs and allocation insights"
```

## Best Practices

1. **Keep Placeholders**: Always maintain the required placeholders in your templates
2. **Test Incrementally**: Make small changes and test with sample data
3. **Role Consistency**: Use consistent role/perspective throughout your prompts
4. **Clear Instructions**: Be specific about what you want the AI to focus on
5. **Format Specification**: Clearly specify your desired output format

## Validation

The system includes template validation to ensure all required placeholders are present. If validation fails, you'll see error messages indicating missing placeholders.

## Example Files

- `config.yaml` - Default templates
- `config_custom_prompts_example.yaml` - Example with customized technical analysis focus

## Migration from Hardcoded Prompts

The new template system is backward compatible. If no prompt templates are specified in the config, the system will use the original hardcoded prompts as defaults.

This ensures existing configurations continue to work while providing full customization flexibility for new use cases.
