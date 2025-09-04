# Naming Improvements Plan

## Current Issues
- Technical jargon in names (e.g., "consolidated", "statistics tracker")
- Overly long class/method names
- Unclear abbreviations (VTT, Bedrock)
- Mixed abstraction levels in naming

## Proposed Changes

### File Renaming
```
OLD NAME                    → NEW NAME                     REASON
consolidated_summarizer.py  → meeting_processor.py         Clearer purpose
bedrock_client.py          → ai_client.py                 Less AWS-specific
global_summarizer.py       → meeting_analyzer.py          More descriptive
model_statistics.py        → performance_tracker.py       Clearer function
keyframe_extractor.py      → video_processor.py          Simpler name
vtt_parser.py              → transcript_parser.py        Less abbreviation
summary_writer.py          → file_writer.py               More generic
pdf_generator.py           → report_generator.py          Broader scope
prompt_engine.py           → template_builder.py         Clearer purpose
```

### Class Renaming
```
OLD NAME                    → NEW NAME                     REASON
ConsolidatedSummarizer     → MeetingProcessor            Main processor role
BedrockClient              → AIClient                    Less vendor-specific
GlobalSummarizer           → MeetingAnalyzer             Analysis focused
ModelStatisticsTracker     → PerformanceTracker         Simpler, clearer
KeyframeExtractor          → VideoProcessor             Broader functionality
VTTParser                  → TranscriptParser           Less abbreviation
SummaryWriter              → FileWriter                 Generic file ops
PDFGenerator               → ReportGenerator            Multi-format support
PromptEngine               → TemplateBuilder            Template focused
```

### Method Renaming Examples
```
OLD NAME                           → NEW NAME                    REASON
_invoke_model_with_stats          → _call_ai_model             Simpler
_generate_consolidated_global     → _create_summary_report     Clearer
_extract_context_window           → _get_surrounding_text      More intuitive
_calculate_relevance_score        → _score_importance          Simpler
summarize_all                     → process_meetings           Clearer action
```

### Variable/Constant Improvements
```
OLD NAME                    → NEW NAME                     REASON
vtt_folders                → meeting_folders              Less technical
keyframes                  → video_screenshots            More descriptive
consolidated_summaries     → meeting_summaries           Clearer
global_result              → analysis_result             More specific
```

## Implementation Strategy

1. **Phase 1**: Rename files and update imports
2. **Phase 2**: Rename classes and update references  
3. **Phase 3**: Rename methods and variables
4. **Phase 4**: Update documentation and configs
5. **Phase 5**: Test everything works correctly

## Benefits
- Easier onboarding for new developers
- Clearer code intentions
- Reduced cognitive load when reading code
- Better alignment with domain language
- More maintainable codebase
