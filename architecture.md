# Meeting Processor - System Architecture

This document provides a comprehensive architectural overview of the Meeting Processor application, which processes meeting recordings and transcript files to generate AI-powered summaries with video screenshot extraction and comprehensive reporting capabilities.

## High-Level Architecture Diagram

```mermaid
graph TB
    %% External Dependencies
    AWS[AWS Bedrock<br/>Claude/OpenAI Models] 
    FILES[Transcript Files<br/>+ Video Files]
    CONFIG[config.yaml<br/>Configuration]
    
    %% Main Entry Point
    MAIN[main.py<br/>CLI Entry Point]
    
    %% Core Orchestration
    PROCESSOR[MeetingProcessor<br/>Main Orchestrator]
    
    %% Processing Components
    TRANSCRIPT_PARSER[TranscriptParser<br/>Content Extraction]
    AI_CLIENT[AIClient<br/>AI Model Interface]
    VIDEO_PROCESSOR[VideoProcessor<br/>Video Processing]
    
    %% Analysis & Generation
    TEMPLATE[TemplateBuilder<br/>Template Management]
    ANALYZER[MeetingAnalyzer<br/>Cross-Meeting Analysis]
    WRITER[FileWriter<br/>File Generation]
    REPORT[ReportGenerator<br/>Report Creation]
    
    %% Supporting Services
    CONFIG_MGR[Config<br/>Settings Manager]
    PERFORMANCE[PerformanceTracker<br/>Performance Monitoring]
    UTILS[Utils<br/>Shared Functions]
    
    %% Outputs
    MD_SUMMARIES[Individual<br/>Meeting Summaries]
    ANALYSIS_MD[Global<br/>Analysis Report]
    SCREENSHOTS[Video<br/>Screenshots]
    FINAL_REPORT[Comprehensive<br/>Final Report]
    
    %% Flow Connections
    MAIN --> CONFIG_MGR
    MAIN --> PROCESSOR
    
    CONFIG --> CONFIG_MGR
    FILES --> TRANSCRIPT_PARSER
    AWS --> AI_CLIENT
    
    PROCESSOR --> TRANSCRIPT_PARSER
    PROCESSOR --> AI_CLIENT
    PROCESSOR --> VIDEO_PROCESSOR
    PROCESSOR --> ANALYZER
    PROCESSOR --> REPORT
    PROCESSOR --> PERFORMANCE
    
    TRANSCRIPT_PARSER --> UTILS
    AI_CLIENT --> TEMPLATE
    AI_CLIENT --> PERFORMANCE
    VIDEO_PROCESSOR --> UTILS
    
    TEMPLATE --> CONFIG_MGR
    ANALYZER --> AI_CLIENT
    ANALYZER --> WRITER
    WRITER --> UTILS
    REPORT --> WRITER
    REPORT --> UTILS
    
    PROCESSOR --> MD_SUMMARIES
    ANALYZER --> ANALYSIS_MD
    VIDEO_PROCESSOR --> SCREENSHOTS
    REPORT --> FINAL_REPORT
    
    %% Styling
    classDef external fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef core fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef processing fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef output fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef support fill:#f5f5f5,stroke:#424242,stroke-width:2px
    
    class AWS,FILES,CONFIG external
    class MAIN,PROCESSOR core
    class TRANSCRIPT_PARSER,AI_CLIENT,VIDEO_PROCESSOR,TEMPLATE,ANALYZER,WRITER,REPORT processing
    class MD_SUMMARIES,ANALYSIS_MD,SCREENSHOTS,FINAL_REPORT output
    class CONFIG_MGR,PERFORMANCE,UTILS support
```

## Detailed Component Architecture

```mermaid
graph TD
    subgraph "Entry Layer"
        MAIN[main.py<br/>• CLI argument parsing<br/>• Logging setup<br/>• Progress reporting<br/>• Error handling]
    end
    
    subgraph "Configuration Layer"
        CONFIG[Config<br/>• YAML configuration<br/>• AWS settings<br/>• Model parameters<br/>• Template definitions<br/>• Processing settings]
    end
    
    subgraph "Core Processing Layer"
        PROCESSOR[MeetingProcessor<br/>• Workflow orchestration<br/>• Individual meeting processing<br/>• Global analysis generation<br/>• Final report creation<br/>• Performance aggregation]
        
        ANALYZER[MeetingAnalyzer<br/>• Cross-meeting analysis<br/>• Strategic insights<br/>• Pattern identification<br/>• Recommendation generation]
    end
    
    subgraph "AI Integration Layer"
        AI_CLIENT[AIClient<br/>• AWS Bedrock interface<br/>• Claude/OpenAI model calls<br/>• Response parsing<br/>• Error handling & retries<br/>• Rate limit management]
        
        TEMPLATE[TemplateBuilder<br/>• Template substitution<br/>• Dynamic prompt building<br/>• Configurable requirements<br/>• Context injection]
        
        PERFORMANCE[PerformanceTracker<br/>• Token usage tracking<br/>• Response time monitoring<br/>• Cost estimation<br/>• Performance analytics]
    end
    
    subgraph "Data Processing Layer"
        TRANSCRIPT_PARSER[TranscriptParser<br/>• Meeting file parsing<br/>• Content extraction<br/>• Metadata extraction<br/>• Speaker identification<br/>• Timeline processing]
        
        VIDEO_PROCESSOR[VideoProcessor<br/>• Video screenshot extraction<br/>• Relevance scoring<br/>• Intelligent timing delays<br/>• Image optimization<br/>• Context window analysis]
        
        WRITER[FileWriter<br/>• Document generation<br/>• Screenshot embedding<br/>• Metadata formatting<br/>• Content structuring]
        
        REPORT[ReportGenerator<br/>• Consolidated documents<br/>• Multi-format conversion<br/>• Table of contents<br/>• Multi-converter support<br/>• Image integration]
    end
    
    subgraph "Utility Layer"
        UTILS[Utils<br/>• File I/O operations<br/>• Time conversions<br/>• Text processing<br/>• Directory management<br/>• Logging setup]
    end
    
    %% Connections
    MAIN --> PROCESSOR
    MAIN --> CONFIG
    
    PROCESSOR --> TRANSCRIPT_PARSER
    PROCESSOR --> AI_CLIENT
    PROCESSOR --> VIDEO_PROCESSOR
    PROCESSOR --> ANALYZER
    PROCESSOR --> REPORT
    PROCESSOR --> PERFORMANCE
    
    ANALYZER --> AI_CLIENT
    ANALYZER --> WRITER
    
    AI_CLIENT --> TEMPLATE
    AI_CLIENT --> PERFORMANCE
    
    TRANSCRIPT_PARSER --> UTILS
    VIDEO_PROCESSOR --> UTILS
    WRITER --> UTILS
    REPORT --> UTILS
    
    TEMPLATE --> CONFIG
    
    %% Styling
    classDef entry fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef config fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef core fill:#fce4ec,stroke:#ad1457,stroke-width:2px
    classDef ai fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    classDef data fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef util fill:#fafafa,stroke:#616161,stroke-width:2px
    
    class MAIN entry
    class CONFIG config
    class PROCESSOR,ANALYZER core
    class AI_CLIENT,TEMPLATE,PERFORMANCE ai
    class TRANSCRIPT_PARSER,VIDEO_PROCESSOR,WRITER,REPORT data
    class UTILS util
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant USER as User
    participant MAIN as main.py
    participant PROC as MeetingProcessor
    participant TRANS as TranscriptParser
    participant VIDEO as VideoProcessor
    participant AI as AIClient
    participant ANALYZER as MeetingAnalyzer
    participant REPORT as ReportGenerator
    participant AWS as AWS Bedrock
    
    USER->>MAIN: Run command with args
    MAIN->>PROC: Initialize with config
    
    loop For each meeting folder
        PROC->>TRANS: Parse transcript file
        TRANS-->>PROC: Content + metadata
        
        opt If video processing enabled
            PROC->>VIDEO: Extract screenshots
            VIDEO-->>PROC: Screenshot images + metadata
        end
        
        PROC->>AI: Create individual summary
        AI->>AWS: API call with content
        AWS-->>AI: AI-generated summary
        AI-->>PROC: Formatted summary
        
        PROC->>PROC: Save individual summary
    end
    
    PROC->>ANALYZER: Create global analysis
    ANALYZER->>AI: Consolidate all summaries
    AI->>AWS: API call with all summaries
    AWS-->>AI: Global analysis
    AI-->>ANALYZER: Analysis content
    ANALYZER-->>PROC: Global analysis file
    
    PROC->>REPORT: Generate final report
    REPORT->>REPORT: Create consolidated document
    REPORT->>REPORT: Convert to multiple formats
    REPORT-->>PROC: Final comprehensive report
    
    PROC-->>MAIN: Complete results
    MAIN-->>USER: Status and summary
```

## File Structure and Responsibilities

```mermaid
graph LR
    subgraph "Project Root"
        MAIN_PY[main.py<br/>Entry point]
        CONFIG_YAML[config.yaml<br/>Configuration]
        REQ[requirements.txt<br/>Dependencies]
        TESTS[tests/<br/>Test suite]
    end
    
    subgraph "vtt_summarizer Package"
        INIT[__init__.py]
        
        subgraph "Core Modules"
            PROCESSOR_PY[meeting_processor.py<br/>Main orchestrator]
            CONFIG_PY[config.py<br/>Configuration manager]
            UTILS_PY[utils.py<br/>Shared utilities]
        end
        
        subgraph "AI Integration"
            AI_PY[ai_client.py<br/>AI interface]
            TEMPLATE_PY[template_builder.py<br/>Template engine]
            PERFORMANCE_PY[performance_tracker.py<br/>Performance tracking]
        end
        
        subgraph "Data Processing"
            TRANSCRIPT_PY[transcript_parser.py<br/>Content parsing]
            VIDEO_PY[video_processor.py<br/>Video processing]
            WRITER_PY[file_writer.py<br/>File output]
            REPORT_PY[report_generator.py<br/>Report creation]
        end
        
        subgraph "Analysis"
            ANALYZER_PY[meeting_analyzer.py<br/>Cross-meeting analysis]
        end
    end
    
    subgraph "Input/Output"
        INPUTS[inputs/<br/>Transcript + Video files]
        OUTPUTS[outputs/<br/>Generated summaries<br/>Video screenshots<br/>Comprehensive reports]
    end
    
    MAIN_PY --> PROCESSOR_PY
    CONFIG_YAML --> CONFIG_PY
    INPUTS --> TRANSCRIPT_PY
    PROCESSOR_PY --> OUTPUTS
    
    %% Styling
    classDef root fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px
    classDef core fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef ai fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef data fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef analysis fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef io fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class MAIN_PY,CONFIG_YAML,REQ,TESTS root
    class PROCESSOR_PY,CONFIG_PY,UTILS_PY core
    class AI_PY,TEMPLATE_PY,PERFORMANCE_PY ai
    class TRANSCRIPT_PY,VIDEO_PY,WRITER_PY,REPORT_PY data
    class ANALYZER_PY analysis
    class INPUTS,OUTPUTS io
```

## Technology Stack

- **Language**: Python 3.8+
- **AI Models**: AWS Bedrock (Claude, OpenAI GPT models)
- **Video Processing**: OpenCV, PIL (Pillow)
- **Document Processing**: WebVTT-py, PyYAML
- **Report Generation**: Pandoc, WeasyPrint, or wkhtmltopdf
- **Configuration**: YAML-based configuration system
- **Dependencies Management**: pip with requirements.txt

## Key Design Patterns

1. **Orchestrator Pattern**: `MeetingProcessor` coordinates all processing steps
2. **Strategy Pattern**: Multiple report converters with fallback options
3. **Template Pattern**: Configurable prompt templates for different AI models
4. **Observer Pattern**: Performance tracking across all model calls
5. **Factory Pattern**: Dynamic model client creation based on configuration
6. **Chain of Responsibility**: Error handling with retries and fallbacks

## Naming Improvements Applied

### Key Changes Made:
- **ConsolidatedSummarizer** → **MeetingProcessor** (clearer main responsibility)
- **BedrockClient** → **AIClient** (less vendor-specific)
- **GlobalSummarizer** → **MeetingAnalyzer** (better describes cross-meeting analysis)
- **ModelStatisticsTracker** → **PerformanceTracker** (simpler, broader scope)
- **KeyframeExtractor** → **VideoProcessor** (broader video processing capabilities)
- **VTTParser** → **TranscriptParser** (less abbreviation-dependent)
- **SummaryWriter** → **FileWriter** (generic file operations)
- **PDFGenerator** → **ReportGenerator** (multi-format support)
- **PromptEngine** → **TemplateBuilder** (clearer template focus)

### Method Naming Improvements:
- **summarize_all()** → **process_meetings()** (clearer action)
- **_invoke_model_with_stats()** → **_call_ai_model()** (simpler)
- **generate_summary()** → **create_summary()** (more direct)
- **extract_keyframes()** → **extract_keyframes()** (kept, but context improved)

### Variable Naming Improvements:
- **vtt_folders** → **meeting_folders** (domain language)
- **keyframes** → **video_screenshots** (more descriptive)
- **global_summary** → **global_analysis** (better describes cross-meeting insights)
- **stats_tracker** → **performance_tracker** (clearer purpose)

## Benefits of New Naming Scheme

1. **Improved Readability**: Code intentions are clearer
2. **Domain Alignment**: Better matches business language
3. **Reduced Cognitive Load**: Less technical jargon
4. **Easier Onboarding**: New developers can understand purpose faster
5. **Better Maintainability**: Changes are easier to locate and understand
6. **Future-Proof**: Names accommodate potential feature expansions
