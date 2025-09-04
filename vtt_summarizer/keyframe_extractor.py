"""Keyframe extraction from video files using VTT transcript timeline."""

import cv2
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import numpy as np

from .utils import time_to_seconds, setup_module_logger
from .vtt_parser import TranscriptSegment


@dataclass
class KeyframeCandidate:
    """Represents a potential keyframe with relevance scoring."""
    timestamp_seconds: float
    timestamp_formatted: str
    relevance_score: float
    context_text: str
    segment_index: int
    delay_seconds: float = 0.0


@dataclass
class ExtractedKeyframe:
    """Represents a successfully extracted keyframe."""
    timestamp_seconds: float
    timestamp_formatted: str
    image_path: str
    context_text: str
    relevance_score: float


class KeyframeExtractor:
    """Extracts relevant keyframes from video files based on VTT transcript analysis."""
    
    def __init__(self, max_frames: int = 5, min_relevance_score: float = 0.3, 
                 custom_delays: Dict[str, float] = None, image_max_width: int = 1200,
                 image_quality: int = 85, caption_context_window: float = 5.0):
        """
        Initialize keyframe extractor.
        
        Args:
            max_frames: Maximum number of keyframes to extract per video
            min_relevance_score: Minimum relevance score to consider a frame
            custom_delays: Optional custom delay overrides for different categories
            image_max_width: Maximum width for optimized images
            image_quality: Quality setting for image optimization
            caption_context_window: Seconds of additional context before/after keyframe segment
        """
        self.max_frames = max_frames
        self.min_relevance_score = min_relevance_score
        self.image_max_width = image_max_width
        self.image_quality = image_quality
        self.caption_context_window = caption_context_window
        self.logger = setup_module_logger(__name__)
        
        # Keywords that indicate potentially relevant moments with intelligent timing delays.
        # 
        # The delay system addresses the common issue where speakers announce actions
        # before they actually occur. For example:
        # - "I will share my screen now" -> Wait 3s for the screen to actually be shared
        # - "Let me show you this demo" -> Wait 2s for the demo to start
        # - "Moving on to the next topic" -> Wait 2s for the transition to complete
        #
        # Each category has optimized delays based on typical meeting behavior patterns.
        self.relevance_keywords = {
            'screen_sharing': {
                'keywords': ['share my screen', 'can you see', 'let me show', 'take a look', 'here you can see', 'on the screen'],
                'delay_seconds': 3.0  # Wait for screen sharing to actually happen
            },
            'screen_sharing_immediate': {
                'keywords': ['sharing my screen', 'screen is shared', 'you should see'],
                'delay_seconds': 0.0  # Already happening
            },
            'demonstrations': {
                'keywords': ['demo', 'example', 'workflow', 'process', 'step by step', 'walk through', 'walkthrough'],
                'delay_seconds': 2.0  # Wait for demo to start
            },
            'technical': {
                'keywords': ['code', 'configuration', 'setup', 'implementation', 'architecture', 'deployment'],
                'delay_seconds': 1.0  # Small delay for context
            },
            'transitions': {
                'keywords': ['next', 'now', 'moving on', 'let\'s go to', 'switch to', 'another thing'],
                'delay_seconds': 2.0  # Wait for transition to complete
            },
            'important': {
                'keywords': ['important', 'key', 'main', 'critical', 'essential', 'note that', 'remember'],
                'delay_seconds': 0.5  # Small delay for emphasis
            },
            'questions': {
                'keywords': ['question', 'ask', 'clarify', 'understand', 'explain'],
                'delay_seconds': 1.0  # Wait for response context
            }
        }
        
        # Apply custom delay overrides if provided
        if custom_delays:
            for category, delay in custom_delays.items():
                if category in self.relevance_keywords:
                    self.relevance_keywords[category]['delay_seconds'] = delay
                    self.logger.info(f"Custom delay for '{category}': {delay}s")
    
    def extract_keyframes(self, video_path: str, transcript_segments: List[TranscriptSegment], 
                         output_dir: str, base_filename: str) -> List[ExtractedKeyframe]:
        """
        Extract keyframes from video based on transcript analysis.
        
        Args:
            video_path: Path to the MP4 video file
            transcript_segments: List of VTT transcript segments
            output_dir: Directory to save extracted images
            base_filename: Base filename for output images (without extension)
            
        Returns:
            List of successfully extracted keyframes
        """
        if not Path(video_path).exists():
            self.logger.warning(f"Video file not found: {video_path}")
            return []
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Analyze transcript for keyframe candidates
        candidates = self._analyze_transcript_for_keyframes(transcript_segments)
        
        if not candidates:
            self.logger.info("No relevant keyframe candidates found in transcript")
            return []
        
        # Select best candidates
        selected_candidates = self._select_best_candidates(candidates)
        
        # Extract frames from video
        extracted_frames = self._extract_frames_from_video(
            video_path, selected_candidates, output_dir, base_filename
        )
        
        self.logger.info(f"Successfully extracted {len(extracted_frames)} keyframes from {Path(video_path).name}")
        return extracted_frames
    
    def _analyze_transcript_for_keyframes(self, segments: List[TranscriptSegment]) -> List[KeyframeCandidate]:
        """
        Analyze transcript segments to identify potential keyframes.
        
        Args:
            segments: List of transcript segments
            
        Returns:
            List of keyframe candidates with relevance scores
        """
        candidates = []
        
        for i, segment in enumerate(segments):
            # Calculate relevance score and delay for this segment
            score, delay = self._calculate_relevance_score_and_delay(segment.text, i, segments)
            
            if score >= self.min_relevance_score:
                # Use the middle of the segment as the base timestamp, then add delay
                start_seconds = time_to_seconds(segment.start_time)
                end_seconds = time_to_seconds(segment.end_time)
                middle_seconds = (start_seconds + end_seconds) / 2
                
                # Add intelligent delay based on content type
                adjusted_timestamp = middle_seconds + delay
                
                # Extract enhanced context text using the context window
                enhanced_context = self._extract_context_window(i, segments)
                
                candidate = KeyframeCandidate(
                    timestamp_seconds=adjusted_timestamp,
                    timestamp_formatted=segment.start_time,
                    relevance_score=score,
                    context_text=enhanced_context,
                    segment_index=i,
                    delay_seconds=delay
                )
                candidates.append(candidate)
        
        # Sort by relevance score (highest first)
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        
        self.logger.info(f"Found {len(candidates)} keyframe candidates with score >= {self.min_relevance_score}")
        return candidates
    
    def _calculate_relevance_score_and_delay(self, text: str, segment_index: int, all_segments: List[TranscriptSegment]) -> Tuple[float, float]:
        """
        Calculate relevance score and intelligent delay for a transcript segment.
        
        Args:
            text: Segment text content
            segment_index: Index of current segment
            all_segments: All transcript segments for context
            
        Returns:
            Tuple of (relevance_score, delay_seconds)
        """
        score = 0.0
        max_delay = 0.0  # Use the highest delay from matched categories
        text_lower = text.lower()
        
        # Check for keyword matches with delay information
        for category, category_info in self.relevance_keywords.items():
            keywords = category_info['keywords']
            delay = category_info['delay_seconds']
            
            for keyword in keywords:
                if keyword in text_lower:
                    # Weight different categories differently
                    if 'screen_sharing' in category:
                        score += 0.4
                    elif category == 'demonstrations':
                        score += 0.3
                    elif category == 'technical':
                        score += 0.2
                    elif category == 'transitions':
                        score += 0.1
                    elif category == 'important':
                        score += 0.15
                    elif category == 'questions':
                        score += 0.1
                    
                    # Track the maximum delay needed
                    max_delay = max(max_delay, delay)
        
        # Bonus for longer segments (more content)
        word_count = len(text.split())
        if word_count > 20:
            score += 0.1
        elif word_count > 50:
            score += 0.2
        
        # Bonus for segments that appear to be section starts
        if segment_index < len(all_segments) - 1:
            # Look for topic transitions
            if any(phrase in text_lower for phrase in ['okay', 'so', 'now', 'next', 'let\'s']):
                score += 0.1
        
        # Cap the score at 1.0
        return min(score, 1.0), max_delay
    
    def _extract_context_window(self, target_segment_index: int, segments: List[TranscriptSegment]) -> str:
        """
        Extract enhanced context text by including segments within the context window.
        
        Args:
            target_segment_index: Index of the target keyframe segment
            segments: All transcript segments
            
        Returns:
            Enhanced context text including surrounding segments within the time window
        """
        if not segments or target_segment_index >= len(segments):
            return ""
            
        target_segment = segments[target_segment_index]
        target_start = time_to_seconds(target_segment.start_time)
        target_end = time_to_seconds(target_segment.end_time)
        
        # Define the context window boundaries
        context_start_time = target_start - self.caption_context_window
        context_end_time = target_end + self.caption_context_window
        
        # Collect segments within the context window
        context_segments = []
        
        for segment in segments:
            segment_start = time_to_seconds(segment.start_time)
            segment_end = time_to_seconds(segment.end_time)
            
            # Include segment if it overlaps with the context window
            if (segment_end >= context_start_time and segment_start <= context_end_time):
                context_segments.append(segment)
        
        # Sort by start time to maintain chronological order
        context_segments.sort(key=lambda s: time_to_seconds(s.start_time))
        
        # Combine the text from all context segments with timestamp and speaker info
        context_text_parts = []
        for segment in context_segments:
            text = segment.text.strip()
            if text:
                # Get timestamp for display
                timestamp = self._format_timestamp_for_display(segment.start_time)
                
                # Get speaker information if available
                speaker = None
                if hasattr(segment, 'original_text') and segment.original_text:
                    speaker = self._extract_speaker_from_text(segment.original_text)
                
                # Format the segment with timestamp and optional speaker
                segment_parts = [f"[{timestamp}]"]
                
                if speaker:
                    segment_parts.append(f"{speaker}:")
                
                # Mark the target segment for clarity
                if segment == target_segment:
                    segment_parts.append(f"**{text}**")
                else:
                    segment_parts.append(text)
                
                context_text_parts.append(" ".join(segment_parts))
        
        return " | ".join(context_text_parts)
    
    def _extract_speaker_from_text(self, text: str) -> Optional[str]:
        """
        Extract speaker name from VTT text if present.
        
        Args:
            text: Original VTT text that may contain speaker information
            
        Returns:
            Speaker name if found, None otherwise
        """
        if not text:
            return None
            
        # Look for speaker patterns at the beginning of text
        # Common patterns: "Speaker: text", "John Smith: text", "Presenter: text"
        speaker_match = re.match(r'^([A-Za-z\s]+):\s*', text.strip())
        if speaker_match:
            return speaker_match.group(1).strip()
        
        return None
    
    def _format_timestamp_for_display(self, timestamp: str) -> str:
        """
        Format timestamp for better readability in context.
        
        Args:
            timestamp: VTT timestamp (e.g., "00:01:23.456")
            
        Returns:
            Formatted timestamp for display (e.g., "1:23")
        """
        try:
            # Parse the timestamp and format it more readably
            parts = timestamp.split(':')
            if len(parts) >= 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(float(parts[2]))
                
                # Format based on duration
                if hours > 0:
                    return f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    return f"{minutes}:{seconds:02d}"
            else:
                return timestamp
        except (ValueError, IndexError):
            return timestamp
    
    def _select_best_candidates(self, candidates: List[KeyframeCandidate]) -> List[KeyframeCandidate]:
        """
        Select the best keyframe candidates, avoiding temporal clustering.
        
        Args:
            candidates: List of all candidates
            
        Returns:
            List of selected candidates
        """
        if len(candidates) <= self.max_frames:
            return candidates
        
        selected = []
        min_interval = 60.0  # Minimum 60 seconds between keyframes
        
        for candidate in candidates:
            # Check if this candidate is too close to already selected ones
            too_close = False
            for selected_candidate in selected:
                if abs(candidate.timestamp_seconds - selected_candidate.timestamp_seconds) < min_interval:
                    too_close = True
                    break
            
            if not too_close:
                selected.append(candidate)
                
                # Stop when we have enough frames
                if len(selected) >= self.max_frames:
                    break
        
        # Sort by timestamp for consistent ordering
        selected.sort(key=lambda x: x.timestamp_seconds)
        
        self.logger.info(f"Selected {len(selected)} keyframes from {len(candidates)} candidates")
        return selected
    
    def _extract_frames_from_video(self, video_path: str, candidates: List[KeyframeCandidate], 
                                  output_dir: str, base_filename: str) -> List[ExtractedKeyframe]:
        """
        Extract actual frames from video file.
        
        Args:
            video_path: Path to video file
            candidates: Selected keyframe candidates
            output_dir: Output directory for images
            base_filename: Base filename for images
            
        Returns:
            List of successfully extracted keyframes
        """
        extracted_frames = []
        
        try:
            # Open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.logger.error(f"Failed to open video file: {video_path}")
                return []
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            
            self.logger.info(f"Video properties: {fps:.2f} FPS, {total_frames} frames, {duration:.2f}s duration")
            
            for i, candidate in enumerate(candidates):
                # Skip if adjusted timestamp is beyond video duration
                if candidate.timestamp_seconds >= duration:
                    self.logger.warning(f"Adjusted timestamp {candidate.timestamp_seconds}s (with {candidate.delay_seconds}s delay) beyond video duration {duration}s")
                    continue
                
                # Calculate frame number
                frame_number = int(candidate.timestamp_seconds * fps)
                
                # Double-check frame number is valid
                if frame_number >= total_frames:
                    self.logger.warning(f"Frame number {frame_number} beyond total frames {total_frames}")
                    continue
                
                # Seek to the frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()
                
                if not ret:
                    self.logger.warning(f"Failed to read frame at {candidate.timestamp_seconds}s")
                    continue
                
                # Generate output filename
                output_filename = f"{base_filename}_{i+1}.png"
                output_path = os.path.join(output_dir, output_filename)
                
                # Save frame as PNG
                success = cv2.imwrite(output_path, frame)
                
                if success:
                    # Optimize image size using PIL
                    self._optimize_image(output_path)
                    
                    extracted_frame = ExtractedKeyframe(
                        timestamp_seconds=candidate.timestamp_seconds,
                        timestamp_formatted=candidate.timestamp_formatted,
                        image_path=output_path,
                        context_text=candidate.context_text,
                        relevance_score=candidate.relevance_score
                    )
                    extracted_frames.append(extracted_frame)
                    
                    if candidate.delay_seconds > 0:
                        self.logger.info(f"Extracted keyframe {i+1}: {candidate.timestamp_formatted} (+{candidate.delay_seconds}s delay) -> {output_filename}")
                    else:
                        self.logger.info(f"Extracted keyframe {i+1}: {candidate.timestamp_formatted} -> {output_filename}")
                else:
                    self.logger.error(f"Failed to save frame to {output_path}")
            
            cap.release()
            
        except Exception as e:
            self.logger.error(f"Error extracting frames from video: {str(e)}")
        
        return extracted_frames
    
    def _optimize_image(self, image_path: str):
        """
        Optimize image size and quality for web display using configured settings.
        
        Args:
            image_path: Path to the image file
        """
        try:
            with Image.open(image_path) as img:
                # Calculate new dimensions while maintaining aspect ratio
                if img.width > self.image_max_width:
                    ratio = self.image_max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((self.image_max_width, new_height), Image.Resampling.LANCZOS)
                
                # Save optimized image (keep as PNG for quality)
                img.save(image_path, 'PNG', optimize=True)
                
        except Exception as e:
            self.logger.warning(f"Failed to optimize image {image_path}: {str(e)}")
    
    def get_video_info(self, video_path: str) -> Optional[Dict[str, any]]:
        """
        Get basic information about a video file.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video information or None if error
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration_seconds': duration,
                'duration_formatted': f"{int(duration//60):02d}:{int(duration%60):02d}"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting video info: {str(e)}")
            return None
