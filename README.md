# VTT Summarizer

An AI-powered Python application that automatically generates comprehensive meeting summaries from VTT (WebVTT) transcript files using AWS Bedrock and Claude models.

## 🚀 Features

- **Automated VTT Processing**: Parses WebVTT files and extracts clean transcript text
- **AI-Powered Summaries**: Uses AWS Bedrock Claude models to generate comprehensive meeting summaries
- **Batch Processing**: Process all VTT files in a directory with a single command
- **Intelligent Rate Limiting**: Handles AWS API throttling with exponential backoff retry logic
- **Flexible Configuration**: YAML-based configuration for easy customization
- **Professional CLI**: Command-line interface with multiple processing options
- **Comprehensive Logging**: Detailed progress tracking and error reporting
- **Markdown Output**: Generates well-structured markdown summaries with metadata
- **Global Summary Generation**: Creates master summaries aggregating all individual meeting summaries

## 📋 Generated Summary Content

Each summary includes:
- **Participants**: List of meeting attendees
- **Main Topics**: Key subjects discussed
- **Key Points**: Important information and insights
- **Technical Details**: Technical concepts and implementations discussed
- **Action Items**: Tasks and next steps identified
- **Decisions Made**: Concrete decisions and conclusions
- **Questions/Issues**: Important questions or problems raised
- **Timeline**: Key moments with timestamps (optional)

### Global Summary Content

The global summary aggregates all individual summaries and provides:
- **Executive Summary**: High-level overview of the entire series
- **Cross-Meeting Themes**: Common patterns and themes across all sessions
- **Technical Architecture Overview**: Overall technical landscape
- **Key Stakeholders**: People involved across multiple meetings
- **Strategic Initiatives**: Major projects and transformation efforts
- **Technology Stack**: Comprehensive list of technologies discussed
- **Consolidated Action Items**: All action items from all meetings
- **Strategic Recommendations**: High-level recommendations based on all meetings

## 🛠 Installation

### Prerequisites

- Python 3.9 or higher
- AWS CLI configured with valid credentials
- Access to AWS Bedrock with Claude models enabled

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/hca
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv vtt_env
   source vtt_env/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Configure AWS credentials** (if not already done):
   ```bash
   aws configure
   ```

5. **Test the setup:**
   ```bash
   python3 run_summarizer.py test
   ```

## 🏗 Project Structure

```
hca/
├── vtt_summarizer/           # Main package
│   ├── __init__.py
│   ├── main.py              # CLI application
│   ├── config.py            # Configuration management
│   ├── vtt_parser.py        # VTT file parsing
│   ├── bedrock_client.py    # AWS Bedrock integration
│   └── summarizer.py        # Main processing logic
├── walkthroughs/            # Input directory with VTT files
│   ├── 20250815_salesforce/
│   ├── 20250821_mulesoft/
│   └── ...
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── run_summarizer.py        # Entry point script
└── README.md               # This file
```

## 📖 Usage

### Super Simple - Just Run It!

```bash
source vtt_env/bin/activate
python3 main.py
```

That's it! The app will:
1. ✅ Find all VTT files in your `walkthroughs/` directory
2. ✅ Generate individual summaries for each meeting
3. ✅ Create a global summary analyzing all meetings
4. ✅ Save everything in clean `summaries/` folder
5. ✅ Skip files that already have summaries (unless you delete them)

### What You Get

**Clean Output Structure:**
```
summaries/
├── 20250815_salesforce_summary.md
├── 20250821_mulesoft_summary.md  
├── 20250822_mainframe_summary.md
├── 20250826_cloud_summary.md
├── 20250827_databases_summary.md
├── 20250829_networking_summary.md
└── global_summary.md
```

**Simple Progress Display:**
```
🚀 VTT SUMMARIZER
📋 Loading configuration...
📁 Input folder: walkthroughs
🤖 Using model: anthropic.claude-3-haiku-20240307-v1:0
🚀 Starting VTT summarization...
   📄 Processing individual VTT files...
   🌍 Processing global summary...
   ✅ All done!
```

### Configuration Options

Edit `config.yaml` to customize:

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
  style: "comprehensive"  # Options: brief, comprehensive, detailed
  include_timestamps: true
  include_participants: true
  include_action_items: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 🔧 AWS Bedrock Models

The application supports various Claude models:

- **Claude 3 Haiku** (Recommended): Fast, cost-effective, 20 req/min rate limit
- **Claude 3.5 Sonnet**: Higher quality, 1 req/min rate limit
- **Claude 3 Opus**: Highest quality, lower rate limits

Current configuration uses **Claude 3 Haiku** for optimal performance.

## 📊 Performance

Recent processing results (6 files, ~36,000 total words):
- **Total Processing Time**: ~1 minute
- **Average per File**: ~10 seconds
- **Success Rate**: 100% (6/6 files)
- **No Rate Limiting Issues**: With Claude 3 Haiku

## 🚨 Troubleshooting

### Common Issues

1. **Throttling Errors**
   - The application automatically handles rate limiting with exponential backoff
   - Consider switching to Claude 3 Haiku for higher throughput

2. **AWS Credentials Issues**
   ```bash
   aws configure list
   aws sts get-caller-identity
   ```

3. **Model Access Issues**
   - Ensure Claude models are enabled in your AWS Bedrock console
   - Check model availability in your AWS region

4. **VTT File Issues**
   - Ensure VTT files are valid WebVTT format
   - Check file permissions and encoding

### Debug Mode

Run with verbose logging for detailed troubleshooting:
```bash
python3 run_summarizer.py --verbose process-single folder_name
```

## 📁 Input File Structure

Expected directory structure:
```
walkthroughs/
├── 20250815_salesforce/
│   ├── Salesforce Walkthrough.vtt
│   ├── meeting_recording.mp4
│   └── summary.md (generated)
├── 20250821_mulesoft/
│   ├── Mulesoft Walkthrough.vtt
│   └── summary.md (generated)
└── ...
```

- Each subdirectory should contain one VTT file
- Summary files are automatically generated in the same directory
- Other files (like MP4 recordings) are ignored

## 🔄 Backup and Recovery

### Configuration Backup
```bash
cp config.yaml config.yaml.backup
```

### Summary Backup
```bash
tar -czf summaries_backup_$(date +%Y%m%d).tar.gz walkthroughs/*/summary.md
```

### Full Project Backup
```bash
tar -czf vtt_summarizer_backup_$(date +%Y%m%d).tar.gz \
    --exclude=vtt_env \
    --exclude=walkthroughs/*/*.mp4 \
    .
```

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Run `python3 run_summarizer.py test` to verify setup
3. Enable verbose logging for detailed error information
4. Check AWS Bedrock service quotas and model availability

## 📝 Output Examples

Generated summaries include:
- Meeting metadata (duration, participants, word count)
- Structured content with headers and bullet points
- Technical details and action items
- Professional formatting suitable for sharing

Example output location: `walkthroughs/20250821_mulesoft/summary.md`

---

*This application was developed to automatically process meeting transcripts and generate comprehensive summaries using AWS Bedrock and Claude AI models.*
