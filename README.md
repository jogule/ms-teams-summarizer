# VTT Summarizer 🚀

AI-powered meeting summarizer that processes VTT transcripts and video files to generate comprehensive summaries with keyframe extraction and PDF reports.

## Quick Start

### Prerequisites
- Python 3.8+
- AWS credentials configured
- One of: `pandoc`, `weasyprint`, or `wkhtmltopdf` (for PDF generation)

### Installation

```bash
# Clone and navigate to the project
git clone <repository-url>
cd repo_folder

# Install dependencies
pip3 install -r requirements.txt

# Install PDF converter (choose one)
brew install pandoc basictex      # Recommended
# OR
pip3 install weasyprint
# OR  
brew install wkhtmltopdf
```

### Setup

1. **Configure AWS credentials** (one of):
   ```bash
   aws configure                    # AWS CLI
   # OR export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
   # OR use IAM roles
   ```

2. **Prepare your files**:
   ```bash
   mkdir inputs
   # Place folders with VTT files (and optional MP4 videos) in inputs/
   # Example structure:
   # inputs/
   #   └── 20250815_meeting1/
   #       ├── transcript.vtt
   #       └── recording.mp4 (optional)
   ```

3. **Configure settings** (optional):
   ```bash
   # Edit config.yaml to customize:
   # - AI model (Claude Haiku/Sonnet, GPT)
   # - Summary style and requirements
   # - Keyframe extraction settings
   # - PDF generation options
   ```

### Run

```bash
# Basic usage - process all files with minimal logging
python3 main.py

# Force overwrite existing summaries
python3 main.py --force

# Enable detailed logging
python3 main.py --verbose

# Disable keyframe extraction
python3 main.py --no-keyframes

# Limit keyframes per video
python3 main.py --max-keyframes 3
```

### Output

The tool generates:
- **Individual summaries**: `outputs/[folder]_summary.md`
- **Global summary**: `outputs/global_summary.md` 
- **Keyframe images**: `outputs/images/[folder]_summary_N.png`
- **PDF report**: `outputs/complete_summary_report_YYYY-MM-DD.pdf`

## Configuration

Key settings in `config.yaml`:

```yaml
aws:
  region: "us-west-2"
  bedrock:
    model_id: "anthropic.claude-3-haiku-20240307-v1:0"
    max_tokens: 4000
    temperature: 0.1

processing:
  input_folder: "inputs"
  output_folder: "outputs"

keyframes:
  enabled: true
  max_frames: 5
  min_relevance_score: 0.3

pdf:
  enabled: true
  include_keyframes: true
```

## Features

- ✅ **Multi-model AI support** - Claude, GPT via AWS Bedrock
- ✅ **Smart keyframe extraction** - Intelligent timing with context
- ✅ **Comprehensive summaries** - Participants, topics, action items
- ✅ **Global analysis** - Cross-meeting insights and patterns
- ✅ **PDF reports** - Professional consolidated documents
- ✅ **Performance tracking** - Token usage and latency monitoring
- ✅ **Configurable templates** - Customizable prompts and requirements

## Architecture

```
VTT Files → Parser → AI Analysis → Individual Summaries
    ↓              ↓          ↓            ↓
Video Files → Keyframes → Global Analysis → PDF Report
```

For detailed architecture documentation, see [`architecture.md`](architecture.md).

## Troubleshooting

**AWS Issues**:
```bash
# Test AWS credentials
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-west-2
```

**PDF Generation Issues**:
```bash
# Test PDF converters
pandoc --version
weasyprint --version  
wkhtmltopdf --version

# Install missing converter
brew install pandoc basictex
```

**Python Issues**:
```bash
# Use virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip3 install -r requirements.txt
```

## Examples

**Basic workflow**:
```bash
# 1. Add VTT files to inputs/
mkdir -p inputs/20250815_demo
cp my-meeting.vtt inputs/20250815_demo/

# 2. Run processing
python3 main.py --verbose

# 3. Check results
ls outputs/
open outputs/complete_summary_report_2025-01-04.pdf
```

**Advanced usage**:
```bash
# Custom configuration with high-quality keyframes
python3 main.py --max-keyframes 10 --verbose

# Skip existing files, generate PDF only
python3 main.py --no-keyframes --force
```

## Development

```bash
# Run tests
python3 run_tests.py

# Validate configuration
python3 -c "from vtt_summarizer.config import Config; print('Config OK')"

# Check dependencies
python3 -c "import boto3, cv2, webvtt; print('Dependencies OK')"
```

---

**Need help?** Check the [architecture documentation](architecture.md) or configuration file comments for detailed explanations.
