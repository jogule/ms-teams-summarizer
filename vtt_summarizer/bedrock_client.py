"""AWS Bedrock client for generating summaries using Claude models."""

import json
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError
import logging
import time
import random

from .config import Config


class BedrockClient:
    """Client for interacting with AWS Bedrock models."""
    
    def __init__(self, config: Config):
        """
        Initialize Bedrock client.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
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
    
    def generate_summary(self, transcript: str, meeting_context: Optional[str] = None) -> str:
        """
        Generate a summary of the meeting transcript using Claude.
        
        Args:
            transcript: The full transcript text
            meeting_context: Optional context about the meeting (folder name, etc.)
            
        Returns:
            Generated summary text
            
        Raises:
            ValueError: If the request fails or returns invalid response
        """
        prompt = self._build_summary_prompt(transcript, meeting_context)
        
        try:
            response = self._invoke_claude(prompt)
            return response
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")
            raise ValueError(f"Summary generation failed: {str(e)}")
    
    def _build_summary_prompt(self, transcript: str, meeting_context: Optional[str] = None) -> str:
        """
        Build the prompt for Claude to generate a meeting summary.
        
        Args:
            transcript: The meeting transcript
            meeting_context: Optional meeting context
            
        Returns:
            Formatted prompt string
        """
        context_info = f"Meeting Context: {meeting_context}\\n\\n" if meeting_context else ""
        
        # Create a comprehensive prompt based on configuration
        prompt_parts = [
            f"Please analyze the following meeting transcript and create a {self.config.summary_style} summary.",
            "",
            "Your summary should include:"
        ]
        
        # Add requirements based on configuration
        requirements = []
        if self.config.include_participants:
            requirements.append("- **Participants**: List of people who spoke during the meeting")
        
        requirements.extend([
            "- **Main Topics**: Key subjects discussed during the meeting",
            "- **Key Points**: Important information, decisions, and insights shared",
            "- **Technical Details**: Any technical concepts, architectures, or implementations discussed"
        ])
        
        if self.config.include_action_items:
            requirements.append("- **Action Items**: Tasks, next steps, or follow-up items mentioned")
        
        requirements.extend([
            "- **Decisions Made**: Any concrete decisions or conclusions reached",
            "- **Questions/Issues Raised**: Important questions or problems discussed"
        ])
        
        if self.config.include_timestamps:
            requirements.append("- **Timeline**: Reference key moments with approximate timestamps when significant topics were discussed")
        
        prompt_parts.extend(requirements)
        prompt_parts.extend([
            "",
            "Please format the summary in clear Markdown with appropriate headers and bullet points.",
            "Focus on technical accuracy and ensure all important information is captured.",
            "",
            f"{context_info}**Transcript:**",
            transcript
        ])
        
        return "\\n".join(prompt_parts)
    
    def _invoke_claude(self, prompt: str) -> str:
        """
        Invoke Claude model with the given prompt.
        
        Args:
            prompt: The prompt to send to Claude
            
        Returns:
            Claude's response text
            
        Raises:
            ClientError: If the API call fails
            ValueError: If the response is invalid
        """
        # Prepare the request body for Claude
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
        
        # Parse the response
        try:
            response_body = json.loads(response['body'].read())
            
            if 'content' not in response_body or not response_body['content']:
                raise ValueError("Invalid response from Bedrock: no content")
            
            # Extract the text from Claude's response
            content = response_body['content']
            if isinstance(content, list) and len(content) > 0:
                summary_text = content[0].get('text', '')
            else:
                summary_text = str(content)
            
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
            response = self._invoke_claude(test_prompt)
            
            if "connection successful" in response.lower():
                self.logger.info("Bedrock connection test successful")
                return True
            else:
                self.logger.warning("Bedrock connection test returned unexpected response")
                return False
                
        except Exception as e:
            self.logger.error(f"Bedrock connection test failed: {str(e)}")
            return False
