"""AWS Bedrock client for generating summaries using Claude models."""

import json
import boto3
from typing import Dict, Any, Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
import time
import random

from .config import Config
from .utils import setup_module_logger
from .model_statistics import ModelStatisticsTracker, ModelCallStats
from .prompt_engine import PromptEngine


class BedrockClient:
    """Client for interacting with AWS Bedrock models."""
    
    def __init__(self, config: Config, stats_tracker: Optional[ModelStatisticsTracker] = None):
        """
        Initialize Bedrock client.
        
        Args:
            config: Configuration object
            stats_tracker: Optional statistics tracker for monitoring model calls
        """
        self.config = config
        self.logger = setup_module_logger(__name__)
        self.stats_tracker = stats_tracker
        self.prompt_engine = PromptEngine(config)
        
        try:
            self.bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name=self.config.aws_region
            )
            self.logger.info(f"Initialized Bedrock client for region: {self.config.aws_region}")
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
    
    def _is_anthropic_model(self) -> bool:
        """
        Check if the configured model is an Anthropic Claude model.
        
        Returns:
            True if the model is an Anthropic model
        """
        return self.config.bedrock_model_id.startswith('anthropic.')
    
    def _is_openai_model(self) -> bool:
        """
        Check if the configured model is an OpenAI model.
        
        Returns:
            True if the model is an OpenAI model
        """
        return self.config.bedrock_model_id.startswith('openai.')
    
    def generate_summary(self, transcript: str, meeting_context: Optional[str] = None, 
                        stats_context: Optional[str] = None) -> str:
        """
        Generate a summary of the meeting transcript using Claude.
        
        Args:
            transcript: The full transcript text
            meeting_context: Optional context about the meeting (folder name, etc.)
            stats_context: Optional context for statistics tracking
            
        Returns:
            Generated summary text
            
        Raises:
            ValueError: If the request fails or returns invalid response
        """
        prompt = self._build_summary_prompt(transcript, meeting_context)
        
        try:
            response, stats = self._invoke_model_with_stats(prompt, stats_context)
            return response
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")
            raise ValueError(f"Summary generation failed: {str(e)}")
    
    def _build_summary_prompt(self, transcript: str, meeting_context: Optional[str] = None) -> str:
        """
        Build the prompt for Claude to generate a meeting summary using configurable templates.
        
        Args:
            transcript: The meeting transcript
            meeting_context: Optional meeting context
            
        Returns:
            Formatted prompt string
        """
        return self.prompt_engine.build_individual_summary_prompt(transcript, meeting_context)
    
    def _invoke_model_with_stats(self, prompt: str, stats_context: Optional[str] = None) -> Tuple[str, Optional[ModelCallStats]]:
        """
        Invoke the configured model with the given prompt and track statistics.
        
        Args:
            prompt: The prompt to send to the model
            stats_context: Context for statistics tracking
            
        Returns:
            Tuple of (model response text, statistics object)
            
        Raises:
            ClientError: If the API call fails
            ValueError: If the response is invalid
        """
        # Start timing if we have a stats tracker
        start_time = self.stats_tracker.start_call(stats_context) if self.stats_tracker else time.time()
        
        try:
            response_text = self._invoke_model(prompt)
            
            # Record statistics if tracker is available
            stats = None
            if self.stats_tracker and stats_context:
                # Create mock response data for statistics (since we don't have actual usage data from Bedrock)
                response_data = {
                    'content': response_text,
                    'model_id': self.config.bedrock_model_id
                }
                stats = self.stats_tracker.record_call(
                    stats_context, start_time, response_data, 
                    is_global=stats_context == 'global_summary'
                )
            
            return response_text, stats
            
        except Exception as e:
            # Still record failed call statistics if possible
            if self.stats_tracker and stats_context:
                response_data = {
                    'content': '',
                    'model_id': self.config.bedrock_model_id,
                    'error': str(e)
                }
                self.stats_tracker.record_call(
                    stats_context, start_time, response_data,
                    is_global=stats_context == 'global_summary'
                )
            raise
    
    def _invoke_model(self, prompt: str) -> str:
        """
        Invoke the configured model with the given prompt.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            Model's response text
            
        Raises:
            ClientError: If the API call fails
            ValueError: If the response is invalid
        """
        # Determine model type and prepare request body accordingly
        if self._is_anthropic_model():
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.config.bedrock_max_tokens,
                "temperature": self.config.bedrock_temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        elif self._is_openai_model():
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_completion_tokens": self.config.bedrock_max_tokens,
                "temperature": self.config.bedrock_temperature
            }
        else:
            raise ValueError(f"Unsupported model type: {self.config.bedrock_model_id}")
        
        max_retries = 3
        base_delay = 60  # Start with 60 seconds for throttling
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt}/{max_retries}")
                
                self.logger.info(f"Invoking Bedrock model: {self.config.bedrock_model_id}")
                
                response = self.bedrock_runtime.invoke_model(
                    modelId=self.config.bedrock_model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                # If we get here, the request succeeded
                break
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Handle throttling specifically
                if error_code == 'ThrottlingException' and attempt < max_retries:
                    # Exponential backoff with jitter for throttling
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 10)
                    self.logger.warning(f"Throttling detected. Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                    continue
                else:
                    # Re-raise for other errors or max retries exceeded
                    raise
        
        # Parse the response based on model type
        try:
            response_body = json.loads(response['body'].read())
            
            if self._is_anthropic_model():
                # Claude response format
                if 'content' not in response_body or not response_body['content']:
                    raise ValueError("Invalid response from Bedrock: no content")
                
                content = response_body['content']
                if isinstance(content, list) and len(content) > 0:
                    summary_text = content[0].get('text', '')
                else:
                    summary_text = str(content)
                    
            elif self._is_openai_model():
                # OpenAI response format
                if 'choices' not in response_body or not response_body['choices']:
                    raise ValueError("Invalid response from Bedrock: no choices")
                
                choices = response_body['choices']
                if isinstance(choices, list) and len(choices) > 0:
                    choice = choices[0]
                    if 'message' in choice and 'content' in choice['message']:
                        summary_text = choice['message']['content']
                    else:
                        raise ValueError("Invalid OpenAI response format")
                else:
                    raise ValueError("No choices in OpenAI response")
            else:
                raise ValueError(f"Unsupported model type for response parsing: {self.config.bedrock_model_id}")
            
            if not summary_text.strip():
                raise ValueError("Empty response from Bedrock")
            
            self.logger.info("Successfully generated summary")
            return summary_text.strip()
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Bedrock response: {str(e)}")
            raise ValueError(f"Invalid JSON response from Bedrock: {str(e)}")
        except KeyError as e:
            self.logger.error(f"Unexpected response format from Bedrock: {str(e)}")
            raise ValueError(f"Unexpected response format: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to AWS Bedrock.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to invoke with a simple test prompt
            test_prompt = "Please respond with 'Connection successful' to test the API."
            response, _ = self._invoke_model_with_stats(test_prompt)
            
            if "connection successful" in response.lower():
                self.logger.info("Bedrock connection test successful")
                return True
            else:
                self.logger.warning("Bedrock connection test returned unexpected response")
                return False
                
        except Exception as e:
            self.logger.error(f"Bedrock connection test failed: {str(e)}")
            return False
