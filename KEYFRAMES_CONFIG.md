# Keyframe Configuration Guide

This document explains the keyframe extraction configuration options available in `config.yaml`.

## Overview

The keyframe extraction feature automatically captures relevant screenshots from meeting videos based on transcript analysis. All settings are configurable through the `keyframes` section in `config.yaml`.

## Configuration Options

### Basic Settings

```yaml
keyframes:
  enabled: true              # Enable/disable keyframe extraction globally
  max_frames: 5              # Maximum keyframes per video (can be overridden by CLI)
  min_relevance_score: 0.3   # Minimum score threshold for keyframe candidates
  image_max_width: 1200      # Maximum width for optimized keyframe images (px)
  image_quality: 85          # Image quality for optimization (0-100)
```

- **`enabled`**: Master switch for keyframe extraction. Set to `false` to disable globally.
- **`max_frames`**: Default maximum number of keyframes per video. CLI `--max-keyframes` overrides this.
- **`min_relevance_score`**: Threshold for selecting keyframes. Lower = more keyframes, higher = fewer but more relevant.
- **`image_max_width`**: Keyframes are resized to this width while maintaining aspect ratio.
- **`image_quality`**: PNG optimization level (0-100, higher = better quality but larger files).

### Intelligent Delays

```yaml
  delays:
    screen_sharing: 3.0        # "I will share my screen" -> wait for actual sharing
    screen_sharing_immediate: 0.0  # "I'm sharing my screen" -> already happening  
    demonstrations: 2.0        # "Let me show you" -> wait for demo to start
    technical: 1.0            # Technical discussions -> small delay for context
    transitions: 2.0          # "Moving on to" -> wait for transition to complete
    important: 0.5            # Important points -> small delay for emphasis
    questions: 1.0            # Q&A moments -> wait for response context
```

The delay system addresses the common issue where speakers announce actions before they actually occur:

- **`screen_sharing`**: Longer delay for future tense ("I will share") - captures when screen is actually visible
- **`screen_sharing_immediate`**: No delay for present tense ("I'm sharing") - already happening
- **`demonstrations`**: Wait for demos/workflows to actually start
- **`technical`**: Small delay for technical discussions to include context
- **`transitions`**: Wait for topic transitions to complete
- **`important`**: Brief pause for emphasis on important points
- **`questions`**: Include time for questions and initial responses

## CLI Overrides

Command-line options can override configuration defaults:

```bash
# Use config defaults
python3 main.py

# Override max keyframes (but use config delays)
python3 main.py --max-keyframes 3

# Disable keyframes entirely (overrides config enabled: true)
python3 main.py --no-keyframes

# Use config defaults with verbose output
python3 main.py --verbose
```

## Customization Tips

### For Different Meeting Types

**Technical Reviews** (more detailed capture):
```yaml
max_frames: 8
min_relevance_score: 0.2
delays:
  screen_sharing: 4.0      # Allow extra time for complex screens
  technical: 1.5           # More context for technical discussions
```

**Quick Updates** (fewer keyframes):
```yaml
max_frames: 3
min_relevance_score: 0.4
delays:
  screen_sharing: 2.0      # Faster transitions
  demonstrations: 1.0      # Quick demos
```

**Customer Demos** (capture key moments):
```yaml
max_frames: 6
delays:
  screen_sharing: 3.5      # Extra time for screen sharing setup
  demonstrations: 2.5      # Wait for demo preparation
  questions: 2.0           # Include customer questions/reactions
```

### Image Quality vs. File Size

**High Quality** (better images, larger files):
```yaml
image_max_width: 1600
image_quality: 95
```

**Optimized** (smaller files, good quality):
```yaml
image_max_width: 1000
image_quality: 75
```

**Minimal** (smallest files):
```yaml
image_max_width: 800
image_quality: 60
```

## Output

Keyframes are saved in the `summaries/images/` directory with the naming pattern:
- `{meeting_name}_summary_1.png`
- `{meeting_name}_summary_2.png`
- etc.

They are automatically embedded in the markdown summaries in a "Meeting Screenshots" section.

## Troubleshooting

**No keyframes extracted?**
- Lower `min_relevance_score` (try 0.2 or 0.1)
- Increase `max_frames`
- Check that video files exist alongside VTT files

**Too many keyframes?**
- Increase `min_relevance_score` (try 0.4 or 0.5)
- Decrease `max_frames`

**Keyframes at wrong moments?**
- Adjust delay values for your meeting patterns
- Check verbose logs to see which categories are matching

**Large file sizes?**
- Reduce `image_max_width` 
- Lower `image_quality`
- Consider fewer `max_frames`
