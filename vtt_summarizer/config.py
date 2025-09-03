"""Configuration management for VTT Summarizer."""

import os
import yaml
from typing import Dict, Any
from pathlib import Path


class Config:
    """Configuration manager for the VTT Summarizer application."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration YAML file. If None, uses default config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    @property
    def aws_region(self) -> str:
        """Get AWS region."""
        return self._config.get('aws', {}).get('region', 'us-east-1')
    
    @property
    def bedrock_model_id(self) -> str:
        """Get Bedrock model ID."""
        return self._config.get('aws', {}).get('bedrock', {}).get('model_id', 
                                'anthropic.claude-3-5-sonnet-20241022-v2:0')
    
    @property
    def bedrock_max_tokens(self) -> int:
        """Get maximum tokens for Bedrock model."""
        return self._config.get('aws', {}).get('bedrock', {}).get('max_tokens', 4000)
    
    @property
    def bedrock_temperature(self) -> float:
        """Get temperature for Bedrock model."""
        return self._config.get('aws', {}).get('bedrock', {}).get('temperature', 0.1)
    
    @property
    def input_folder(self) -> str:
        """Get input folder path."""
        return self._config.get('processing', {}).get('input_folder', 'walkthroughs')
    
    @property
    def output_filename(self) -> str:
        """Get output filename."""
        return self._config.get('processing', {}).get('output_filename', 'summary.md')
    
    @property
    def summary_style(self) -> str:
        """Get summary style."""
        return self._config.get('summary', {}).get('style', 'comprehensive')
    
    @property
    def include_timestamps(self) -> bool:
        """Get whether to include timestamps in summary."""
        return self._config.get('summary', {}).get('include_timestamps', True)
    
    @property
    def include_participants(self) -> bool:
        """Get whether to include participants in summary."""
        return self._config.get('summary', {}).get('include_participants', True)
    
    @property
    def include_action_items(self) -> bool:
        """Get whether to include action items in summary."""
        return self._config.get('summary', {}).get('include_action_items', True)
    
    @property
    def logging_level(self) -> str:
        """Get logging level."""
        return self._config.get('logging', {}).get('level', 'INFO')
    
    @property
    def logging_format(self) -> str:
        """Get logging format."""
        return self._config.get('logging', {}).get('format', 
                               '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key (e.g., 'aws.region')."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
