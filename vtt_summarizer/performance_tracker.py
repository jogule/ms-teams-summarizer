"""Performance tracking for monitoring AI model usage, costs, and response times."""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ModelCallStats:
    """Performance statistics for a single AI model call."""
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    model_id: str = ""
    timestamp: float = field(default_factory=time.time)
    
    @property
    def latency_seconds(self) -> float:
        """Get latency in seconds."""
        return self.latency_ms / 1000.0


class PerformanceTracker:
    """Tracks AI model performance metrics across the entire processing session."""
    
    def __init__(self):
        """Initialize the performance tracker."""
        self.individual_calls: Dict[str, ModelCallStats] = {}
        self.analysis_calls: Dict[str, ModelCallStats] = {}
        self.session_start = time.time()
    
    def start_call(self, context: str) -> float:
        """
        Start timing a model call.
        
        Args:
            context: Context identifier (e.g., folder name or "global_summary")
            
        Returns:
            Start time for measuring latency
        """
        return time.time()
    
    def record_call(self, context: str, start_time: float, response_data: Dict[str, Any], 
                   is_analysis: bool = False) -> ModelCallStats:
        """
        Record a completed AI model call with its performance metrics.
        
        Args:
            context: Context identifier (e.g., folder name or "global_analysis")
            start_time: Start time from start_call()
            response_data: Response data from the model API
            is_analysis: Whether this is a global analysis call
            
        Returns:
            ModelCallStats object with recorded statistics
        """
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Extract token usage from response (if available)
        usage = response_data.get('usage', {})
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        total_tokens = input_tokens + output_tokens
        
        # If no usage data in response, estimate based on content
        if total_tokens == 0:
            total_tokens = self._estimate_tokens(response_data)
        
        stats = ModelCallStats(
            tokens_used=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model_id=response_data.get('model_id', 'unknown'),
            timestamp=end_time
        )
        
        # Store in appropriate collection
        if is_analysis:
            self.analysis_calls[context] = stats
        else:
            self.individual_calls[context] = stats
        
        return stats
    
    def _estimate_tokens(self, response_data: Dict[str, Any]) -> int:
        """
        Estimate token count when not provided by the API.
        Rough approximation: ~4 characters per token for English text.
        
        Args:
            response_data: Response data from the model
            
        Returns:
            Estimated token count
        """
        content = ""
        
        # Try to extract text content from different response formats
        if 'content' in response_data:
            if isinstance(response_data['content'], list):
                content = " ".join([item.get('text', '') for item in response_data['content']])
            else:
                content = str(response_data['content'])
        elif 'choices' in response_data:
            choices = response_data['choices']
            if isinstance(choices, list) and choices:
                choice = choices[0]
                if 'message' in choice and 'content' in choice['message']:
                    content = choice['message']['content']
        
        # Rough token estimation (4 chars ≈ 1 token)
        return max(1, len(content) // 4)
    
    def get_individual_stats(self, folder_name: str) -> Optional[ModelCallStats]:
        """
        Get statistics for an individual file processing.
        
        Args:
            folder_name: Name of the processed folder
            
        Returns:
            ModelCallStats if available, None otherwise
        """
        return self.individual_calls.get(folder_name)
    
    def get_analysis_stats(self) -> Optional[ModelCallStats]:
        """
        Get statistics for global analysis processing.
        
        Returns:
            ModelCallStats if available, None otherwise
        """
        return self.analysis_calls.get('global_analysis')
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the entire session.
        
        Returns:
            Dictionary with session-wide statistics
        """
        all_stats = list(self.individual_calls.values()) + list(self.analysis_calls.values())
        
        if not all_stats:
            return {
                'total_calls': 0,
                'total_tokens': 0,
                'total_latency_ms': 0.0,
                'average_latency_ms': 0.0,
                'session_duration_seconds': time.time() - self.session_start
            }
        
        total_calls = len(all_stats)
        total_tokens = sum(stat.tokens_used for stat in all_stats)
        total_latency_ms = sum(stat.latency_ms for stat in all_stats)
        average_latency_ms = total_latency_ms / total_calls if total_calls > 0 else 0.0
        
        return {
            'total_calls': total_calls,
            'individual_calls': len(self.individual_calls),
            'analysis_calls': len(self.analysis_calls),
            'total_tokens': total_tokens,
            'total_input_tokens': sum(stat.input_tokens for stat in all_stats),
            'total_output_tokens': sum(stat.output_tokens for stat in all_stats),
            'total_latency_ms': total_latency_ms,
            'average_latency_ms': average_latency_ms,
            'min_latency_ms': min(stat.latency_ms for stat in all_stats),
            'max_latency_ms': max(stat.latency_ms for stat in all_stats),
            'session_duration_seconds': time.time() - self.session_start
        }
    
    def format_stats_for_display(self, stats: ModelCallStats) -> str:
        """
        Format model call statistics for display.
        
        Args:
            stats: ModelCallStats to format
            
        Returns:
            Formatted string with statistics
        """
        lines = []
        
        if stats.input_tokens > 0 and stats.output_tokens > 0:
            lines.append(f"   🔢 Tokens: {stats.input_tokens} in + {stats.output_tokens} out = {stats.tokens_used} total")
        else:
            lines.append(f"   🔢 Tokens: ~{stats.tokens_used} (estimated)")
        
        lines.append(f"   ⚡ Latency: {stats.latency_ms:.0f}ms ({stats.latency_seconds:.2f}s)")
        lines.append(f"   🤖 Model: {stats.model_id}")
        
        return "\n".join(lines)
