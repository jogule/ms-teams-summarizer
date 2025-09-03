# MS Teams Summarizer

A Python-based tool that automatically processes Microsoft Teams meeting recordings to generate intelligent summaries with keyframe extraction.

## Overview

This application processes VTT (WebVTT) caption files from Teams meetings and generates comprehensive summaries using AWS Bedrock's Claude AI. It can extract key visual moments from recordings and create both individual meeting summaries and consolidated global summaries.

## Features

### 🎯 Core Functionality
- **VTT Processing**: Parses WebVTT caption files from Teams recordings
- **AI Summarization**: Uses AWS Bedrock Claude models for intelligent content analysis
- **Dual Summary Types**: Generates both individual meeting summaries and global consolidated summaries
- **Keyframe Extraction**: Automatically captures relevant screenshots from meeting recordings

### 🔧 Advanced Capabilities
- **Intelligent Timing**: Smart delays for different content types (screen sharing, demonstrations, Q&A)
- **Content Analysis**: Identifies participants, action items, and key discussion points
- **Batch Processing**: Processes multiple meetings in a single run
- **Flexible Configuration**: YAML-based configuration with CLI overrides
- **Force/Resume**: Skip existing summaries or force regeneration

### 📊 Output Features
- **Markdown Summaries**: Clean, readable output format
- **Timestamp Integration**: Preserves timing information from original meetings
- **Participant Tracking**: Identifies and tracks meeting participants
- **Action Items**: Extracts and highlights actionable items
- **Visual Context**: Embeds relevant keyframes in summaries

## Architecture

### Components

```
ms-teams-summarizer/
├── main.py                     # Entry point and CLI interface
├── config.yaml                 # Configuration settings
├── vtt_summarizer/
│   ├── consolidated_summarizer.py  # Main orchestrator
│   ├── vtt_parser.py              # VTT file parsing
│   ├── bedrock_client.py          # AWS Bedrock integration
│   ├── global_summarizer.py       # Multi-meeting analysis
│   ├── keyframe_extractor.py      # Video frame extraction
│   ├── summary_writer.py          # Markdown output generation
│   ├── config.py                  # Configuration management
│   └── utils.py                   # Utility functions
└── tests/                      # Test suite
```

### Data Flow

1. **Input Processing**: Scans for VTT files in configured directories
2. **Content Parsing**: Extracts timestamps, speakers, and dialogue
3. **AI Analysis**: Sends content to Claude for intelligent summarization  
4. **Keyframe Extraction**: Captures relevant visual moments (optional)
5. **Summary Generation**: Creates individual meeting summaries
6. **Global Analysis**: Consolidates multiple meetings into overview summaries
7. **Output**: Saves markdown files with embedded keyframes

### AWS Integration

- **Bedrock**: Claude 3 Haiku/Sonnet models for text analysis
- **Configurable**: Supports different model types and parameters
- **Rate Limiting**: Respects AWS service limits
- **Error Handling**: Robust retry logic for API calls

## Usage

### Quick Start

```bash
# Process all new VTT files
python3 main.py

# Force regenerate all summaries
python3 main.py --force

# Enable detailed logging
python3 main.py --verbose

# Skip keyframe extraction
python3 main.py --no-keyframes

# Limit keyframes per video
python3 main.py --max-keyframes 3
```

### Directory Structure

```
project/
├── walkthroughs/           # Input directory (configurable)
│   ├── meeting-1/
│   │   ├── video.mp4
│   │   └── captions.vtt
│   └── meeting-2/
│       ├── recording.mp4
│       └── transcript.vtt
└── summaries/              # Output directory
    ├── meeting-1_summary.md
    ├── meeting-2_summary.md
    └── global_summary.md
```

## Configuration

The application uses `config.yaml` for settings:

```yaml
aws:
  region: "us-east-1"
  bedrock:
    model_id: "anthropic.claude-3-haiku-20240307-v1:0"
    max_tokens: 4000
    temperature: 0.1

processing:
  input_folder: "walkthroughs"
  output_filename: "summary.md"

summary:
  style: "comprehensive"
  include_timestamps: true
  include_participants: true
  include_action_items: true

keyframes:
  enabled: true
  max_frames: 5
  min_relevance_score: 0.3
  image_max_width: 1200
```

## Installation

### Prerequisites

- Python 3.8+
- AWS account with Bedrock access
- OpenCV for video processing
- Teams meeting recordings with VTT captions

### Setup

```bash
# Clone repository
git clone https://github.com/jogule/ms-teams-summarizer.git
cd ms-teams-summarizer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip3 install -r requirements.txt

# Configure AWS credentials
aws configure

# Update config.yaml with your settings
```

### Dependencies

- `boto3` - AWS SDK for Bedrock integration
- `webvtt-py` - VTT file parsing
- `opencv-python` - Video keyframe extraction  
- `Pillow` - Image processing
- `pyyaml` - Configuration management
- `python-dotenv` - Environment variable support

## Output Examples

### Individual Summary
- Meeting metadata (date, duration, participants)
- Executive summary
- Key discussion points with timestamps
- Action items and decisions
- Embedded keyframe screenshots
- Q&A highlights

### Global Summary  
- Cross-meeting themes and patterns
- Recurring participants and topics
- Progress tracking on action items
- Timeline of decisions across meetings
- Consolidated insights and recommendations

## Security & Privacy

- **Local Processing**: No meeting content sent to third parties except AWS Bedrock
- **Configurable Models**: Choose appropriate Claude model for your security needs
- **No Data Persistence**: Application doesn't store meeting content beyond summaries
- **AWS Security**: Leverages AWS IAM and Bedrock security controls

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Submit a pull request

## License

This project is available under standard open source licensing terms.

---

*Built for efficient meeting analysis and knowledge extraction from Microsoft Teams recordings.*
