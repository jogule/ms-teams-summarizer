# VTT Summarizer - System Architecture

This document provides a comprehensive architectural overview of the VTT Summarizer application, which processes meeting recordings (VTT files) and generates AI-powered summaries with keyframe extraction and PDF reporting capabilities.

## High-Level Architecture Diagram

```mermaid
graph TB
    %% External Dependencies
    AWS[AWS Bedrock<br/>Claude/OpenAI Models] 
    VTT[VTT Files<br/>+ Video Files]
    CONFIG[config.yaml<br/>Configuration]
    
    %% Main Entry Point
    MAIN[main.py<br/>CLI Entry Point]
    
    %% Core Orchestration
    CONSOLIDATED[ConsolidatedSummarizer<br/>Main Orchestrator]
    
    %% Processing Components
    VTT_PARSER[VTTParser<br/>Transcript Extraction]
    BEDROCK[BedrockClient<br/>AI Model Interface]
    KEYFRAME[KeyframeExtractor<br/>Video Processing]
    
    %% Analysis & Generation
    PROMPT[PromptEngine<br/>Template Management]
    GLOBAL[GlobalSummarizer<br/>Cross-Meeting Analysis]
    WRITER[SummaryWriter<br/>Markdown Generation]
    PDF[PDFGenerator<br/>Report Creation]
    
    %% Supporting Services
    CONFIG_MGR[Config<br/>Settings Manager]
    STATS[ModelStatisticsTracker<br/>Performance Monitoring]
    UTILS[Utils<br/>Shared Functions]
    
    %% Outputs
    MD_SUMMARIES[Individual<br/>Markdown Summaries]
    GLOBAL_MD[Global<br/>Summary Report]
    KEYFRAME_IMGS[Keyframe<br/>Images]
    PDF_REPORT[Consolidated<br/>PDF Report]
    
    %% Flow Connections
    MAIN --> CONFIG_MGR
    MAIN --> CONSOLIDATED
    
    CONFIG --> CONFIG_MGR
    VTT --> VTT_PARSER
    AWS --> BEDROCK
    
    CONSOLIDATED --> VTT_PARSER
    CONSOLIDATED --> BEDROCK
    CONSOLIDATED --> KEYFRAME
    CONSOLIDATED --> GLOBAL
    CONSOLIDATED --> PDF
    CONSOLIDATED --> STATS
    
    VTT_PARSER --> UTILS
    BEDROCK --> PROMPT
    BEDROCK --> STATS
    KEYFRAME --> UTILS
    
    PROMPT --> CONFIG_MGR
    GLOBAL --> BEDROCK
    GLOBAL --> WRITER
    WRITER --> UTILS
    PDF --> WRITER
    PDF --> UTILS
    
    CONSOLIDATED --> MD_SUMMARIES
    GLOBAL --> GLOBAL_MD
    KEYFRAME --> KEYFRAME_IMGS
    PDF --> PDF_REPORT
    
    %% Styling
    classDef external fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef core fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef processing fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef output fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef support fill:#f5f5f5,stroke:#424242,stroke-width:2px
    
    class AWS,VTT,CONFIG external
    class MAIN,CONSOLIDATED core
    class VTT_PARSER,BEDROCK,KEYFRAME,PROMPT,GLOBAL,WRITER,PDF processing
    class MD_SUMMARIES,GLOBAL_MD,KEYFRAME_IMGS,PDF_REPORT output
    class CONFIG_MGR,STATS,UTILS support
```

## Detailed Component Architecture

```mermaid
graph TD
    subgraph "Entry Layer"
        MAIN[main.py<br/>• CLI argument parsing<br/>• Logging setup<br/>• Progress reporting<br/>• Error handling]
    end
    
    subgraph "Configuration Layer"
        CONFIG[Config<br/>• YAML configuration<br/>• AWS settings<br/>• Model parameters<br/>• Prompt templates<br/>• PDF/Keyframe settings]
    end
    
    subgraph "Core Processing Layer"
        CONSOLIDATED[ConsolidatedSummarizer<br/>• Workflow orchestration<br/>• Individual VTT processing<br/>• Global summary generation<br/>• PDF report creation<br/>• Statistics aggregation]
        
        GLOBAL[GlobalSummarizer<br/>• Cross-meeting analysis<br/>• Strategic insights<br/>• Pattern identification<br/>• Recommendation generation]
    end
    
    subgraph "AI Integration Layer"
        BEDROCK[BedrockClient<br/>• AWS Bedrock interface<br/>• Claude/OpenAI model calls<br/>• Response parsing<br/>• Error handling & retries<br/>• Rate limit management]
        
        PROMPT[PromptEngine<br/>• Template substitution<br/>• Dynamic prompt building<br/>• Configurable requirements<br/>• Context injection]
        
        STATS[ModelStatisticsTracker<br/>• Token usage tracking<br/>• Latency monitoring<br/>• Cost estimation<br/>• Performance analytics]
    end
    
    subgraph "Data Processing Layer"
        VTT_PARSER[VTTParser<br/>• WebVTT file parsing<br/>• Transcript extraction<br/>• Metadata extraction<br/>• Speaker identification<br/>• Timeline processing]
        
        KEYFRAME[KeyframeExtractor<br/>• Video frame extraction<br/>• Relevance scoring<br/>• Intelligent timing delays<br/>• Image optimization<br/>• Context window analysis]
        
        WRITER[SummaryWriter<br/>• Markdown generation<br/>• Keyframe embedding<br/>• Metadata formatting<br/>• Content structuring]
        
        PDF[PDFGenerator<br/>• Consolidated markdown<br/>• PDF conversion<br/>• Table of contents<br/>• Multi-converter support<br/>• Image integration]
    end
    
    subgraph "Utility Layer"
        UTILS[Utils<br/>• File I/O operations<br/>• Time conversions<br/>• Text processing<br/>• Directory management<br/>• Logging setup]
    end
    
    %% Connections
    MAIN --> CONSOLIDATED
    MAIN --> CONFIG
    
    CONSOLIDATED --> VTT_PARSER
    CONSOLIDATED --> BEDROCK
    CONSOLIDATED --> KEYFRAME
    CONSOLIDATED --> GLOBAL
    CONSOLIDATED --> PDF
    CONSOLIDATED --> STATS
    
    GLOBAL --> BEDROCK
    GLOBAL --> WRITER
    
    BEDROCK --> PROMPT
    BEDROCK --> STATS
    
    VTT_PARSER --> UTILS
    KEYFRAME --> UTILS
    WRITER --> UTILS
    PDF --> UTILS
    
    PROMPT --> CONFIG
    
    %% Styling
    classDef entry fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef config fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef core fill:#fce4ec,stroke:#ad1457,stroke-width:2px
    classDef ai fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    classDef data fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef util fill:#fafafa,stroke:#616161,stroke-width:2px
    
    class MAIN entry
    class CONFIG config
    class CONSOLIDATED,GLOBAL core
    class BEDROCK,PROMPT,STATS ai
    class VTT_PARSER,KEYFRAME,WRITER,PDF data
    class UTILS util
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant USER as User
    participant MAIN as main.py
    participant CONS as ConsolidatedSummarizer
    participant VTT as VTTParser
    participant KEY as KeyframeExtractor
    participant BED as BedrockClient
    participant GLOB as GlobalSummarizer
    participant PDF as PDFGenerator
    participant AWS as AWS Bedrock
    
    USER->>MAIN: Run command with args
    MAIN->>CONS: Initialize with config
    
    loop For each VTT folder
        CONS->>VTT: Parse VTT file
        VTT-->>CONS: Transcript + metadata
        
        opt If keyframes enabled
            CONS->>KEY: Extract keyframes
            KEY-->>CONS: Keyframe images + metadata
        end
        
        CONS->>BED: Generate individual summary
        BED->>AWS: API call with transcript
        AWS-->>BED: AI-generated summary
        BED-->>CONS: Formatted summary
        
        CONS->>CONS: Save individual summary
    end
    
    CONS->>GLOB: Generate global summary
    GLOB->>BED: Consolidate all summaries
    BED->>AWS: API call with all summaries
    AWS-->>BED: Global analysis
    BED-->>GLOB: Global summary
    GLOB-->>CONS: Global summary file
    
    CONS->>PDF: Generate PDF report
    PDF->>PDF: Create consolidated markdown
    PDF->>PDF: Convert to PDF
    PDF-->>CONS: PDF report
    
    CONS-->>MAIN: Complete results
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
            CONSOLIDATED_PY[consolidated_summarizer.py<br/>Main orchestrator]
            CONFIG_PY[config.py<br/>Configuration manager]
            UTILS_PY[utils.py<br/>Shared utilities]
        end
        
        subgraph "AI Integration"
            BEDROCK_PY[bedrock_client.py<br/>AWS interface]
            PROMPT_PY[prompt_engine.py<br/>Template engine]
            STATS_PY[model_statistics.py<br/>Tracking]
        end
        
        subgraph "Data Processing"
            VTT_PY[vtt_parser.py<br/>Transcript parsing]
            KEYFRAME_PY[keyframe_extractor.py<br/>Video processing]
            WRITER_PY[summary_writer.py<br/>File output]
            PDF_PY[pdf_generator.py<br/>PDF creation]
        end
        
        subgraph "Analysis"
            GLOBAL_PY[global_summarizer.py<br/>Cross-meeting analysis]
        end
    end
    
    subgraph "Input/Output"
        INPUTS[inputs/<br/>VTT + Video files]
        OUTPUTS[outputs/<br/>Generated summaries<br/>Keyframe images<br/>PDF reports]
    end
    
    MAIN_PY --> CONSOLIDATED_PY
    CONFIG_YAML --> CONFIG_PY
    INPUTS --> VTT_PY
    CONSOLIDATED_PY --> OUTPUTS
    
    %% Styling
    classDef root fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px
    classDef core fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef ai fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef data fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef analysis fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef io fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class MAIN_PY,CONFIG_YAML,REQ,TESTS root
    class CONSOLIDATED_PY,CONFIG_PY,UTILS_PY core
    class BEDROCK_PY,PROMPT_PY,STATS_PY ai
    class VTT_PY,KEYFRAME_PY,WRITER_PY,PDF_PY data
    class GLOBAL_PY analysis
    class INPUTS,OUTPUTS io
```

## Technology Stack

- **Language**: Python 3.8+
- **AI Models**: AWS Bedrock (Claude, OpenAI GPT models)
- **Video Processing**: OpenCV, PIL (Pillow)
- **Document Processing**: WebVTT-py, PyYAML
- **PDF Generation**: Pandoc, WeasyPrint, or wkhtmltopdf
- **Configuration**: YAML-based configuration system
- **Dependencies Management**: pip with requirements.txt

## Key Design Patterns

1. **Orchestrator Pattern**: `ConsolidatedSummarizer` coordinates all processing steps
2. **Strategy Pattern**: Multiple PDF converters with fallback options
3. **Template Pattern**: Configurable prompt templates for different AI models
4. **Observer Pattern**: Statistics tracking across all model calls
5. **Factory Pattern**: Dynamic model client creation based on configuration
6. **Chain of Responsibility**: Error handling with retries and fallbacks

## Scalability Considerations

- Configurable processing limits and timeouts
- Intelligent rate limiting for API calls
- Modular architecture allows easy component replacement
- Statistics tracking for performance monitoring
- Extensive error handling and recovery mechanisms
