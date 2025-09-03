"""Configuration wrapper to simplify access patterns and reduce duplication."""

from typing import Dict, Any
from .config import Config


class ConfigWrapper:
    """Wrapper around Config to provide commonly used configuration bundles."""
    
    def __init__(self, config: Config):
        self._config = config
    
    @property
    def config(self) -> Config:
        """Access to the underlying config object."""
        return self._config
    
    @property
    def bedrock_settings(self) -> Dict[str, Any]:
        """Get all Bedrock-related settings as a bundle."""
        return {
            'model_id': self._config.bedrock_model_id,
            'max_tokens': self._config.bedrock_max_tokens,
            'temperature': self._config.bedrock_temperature,
            'region': self._config.aws_region
        }
    
    @property
    def summary_settings(self) -> Dict[str, Any]:
        """Get all summary-related settings as a bundle."""
        return {
            'style': self._config.summary_style,
            'include_timestamps': self._config.include_timestamps,
            'include_participants': self._config.include_participants,
            'include_action_items': self._config.include_action_items
        }
    
    @property
    def processing_settings(self) -> Dict[str, Any]:
        """Get all processing-related settings as a bundle."""
        return {
            'input_folder': self._config.input_folder,
            'output_filename': self._config.output_filename
        }
    
    @property
    def logging_settings(self) -> Dict[str, Any]:
        """Get all logging-related settings as a bundle."""
        return {
            'level': self._config.logging_level,
            'format': self._config.logging_format
        }
    
    # Direct access to commonly used individual properties
    @property
    def input_folder(self) -> str:
        return self._config.input_folder
    
    @property
    def model_id(self) -> str:
        return self._config.bedrock_model_id
    
    @property
    def include_timestamps(self) -> bool:
        return self._config.include_timestamps
    
    @property
    def include_participants(self) -> bool:
        return self._config.include_participants
    
    @property
    def include_action_items(self) -> bool:
        return self._config.include_action_items
    
    @property
    def summary_style(self) -> str:
        return self._config.summary_style
