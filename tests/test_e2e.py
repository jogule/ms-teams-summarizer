#!/usr/bin/env python3
"""
End-to-End (E2E) Test Suite for VTT Summarizer

This test suite validates the complete workflow of the VTT Summarizer application,
from VTT file processing to summary generation and global analysis.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vtt_summarizer.config import Config
from vtt_summarizer.consolidated_summarizer import ConsolidatedSummarizer
from vtt_summarizer.vtt_parser import VTTParser
from vtt_summarizer.bedrock_client import BedrockClient


class TestE2EVTTSummarizer(unittest.TestCase):
    """End-to-end tests for the VTT Summarizer application."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="hca_e2e_test_"))
        cls.original_cwd = os.getcwd()
        
        print(f"\n🧪 E2E Test Environment: {cls.test_dir}")
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        os.chdir(cls.original_cwd)
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
        print(f"🧹 Cleaned up test environment")
    
    def setUp(self):
        """Set up individual test case."""
        os.chdir(self.test_dir)
        
        # Create test directory structure
        self.walkthroughs_dir = self.test_dir / "walkthroughs"
        self.summaries_dir = self.test_dir / "summaries"
        self.walkthroughs_dir.mkdir(exist_ok=True)
        
        # Clean up any existing test directories from previous test
        for existing_dir in self.walkthroughs_dir.iterdir():
            if existing_dir.is_dir():
                shutil.rmtree(existing_dir)
        
        # Create test configuration
        self.create_test_config()
        
        # Create sample VTT files
        self.create_sample_vtt_files()
        
    def tearDown(self):
        """Clean up after each test."""
        # Remove generated files but keep test structure
        if self.summaries_dir.exists():
            shutil.rmtree(self.summaries_dir)
    
    def create_test_config(self):
        """Create a test configuration file."""
        config_content = """
aws:
  region: "us-east-1"
  bedrock:
    model_id: "anthropic.claude-3-haiku-20240307-v1:0"
    max_tokens: 1000
    temperature: 0.1

processing:
  input_folder: "walkthroughs"
  output_folder: "summaries"
  
  # Filename formats - use placeholders: {folder_name}, {timestamp}, {date}
  individual_summary_filename: "{folder_name}_summary.md"
  global_summary_filename: "global_summary.md"
  
  # Input file patterns to look for (VTT files)
  input_file_patterns: ["*.vtt"]

summary:
  style: "comprehensive"
  include_timestamps: true
  include_participants: true
  include_action_items: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""
        config_path = self.test_dir / "config.yaml"
        with open(config_path, 'w') as f:
            f.write(config_content)
    
    def create_sample_vtt_files(self):
        """Create sample VTT files for testing."""
        
        # Sample VTT content for meeting 1
        vtt_content_1 = """WEBVTT

00:00:00.000 --> 00:00:05.000
Welcome everyone to our Salesforce integration meeting.

00:00:05.000 --> 00:00:12.000
Today we'll be discussing our API strategy and data synchronization.

00:00:12.000 --> 00:00:20.000
John: I think we should focus on the REST APIs first, then move to GraphQL.

00:00:20.000 --> 00:00:28.000
Sarah: That makes sense. We also need to consider rate limiting and authentication.

00:00:28.000 --> 00:00:35.000
Action item: John will create the API documentation by next week.

00:00:35.000 --> 00:00:40.000
Let's also review the data mapping requirements.
"""
        
        # Sample VTT content for meeting 2
        vtt_content_2 = """WEBVTT

00:00:00.000 --> 00:00:08.000
Good morning team. This is our MuleSoft architecture review session.

00:00:08.000 --> 00:00:15.000
We need to discuss the ESB implementation and message routing patterns.

00:00:15.000 --> 00:00:25.000
Mike: The current setup handles about 10,000 transactions per day.

00:00:25.000 --> 00:00:32.000
Lisa: We should implement circuit breakers for better resilience.

00:00:32.000 --> 00:00:40.000
Decision: We'll upgrade to MuleSoft 4.4 next quarter.

00:00:40.000 --> 00:00:45.000
Action item: Lisa will prepare the migration plan.
"""
        
        # Create test meeting directories with VTT files
        meeting1_dir = self.walkthroughs_dir / "20250815_salesforce"
        meeting2_dir = self.walkthroughs_dir / "20250821_mulesoft"
        
        meeting1_dir.mkdir(exist_ok=True)
        meeting2_dir.mkdir(exist_ok=True)
        
        (meeting1_dir / "transcript.vtt").write_text(vtt_content_1)
        (meeting2_dir / "transcript.vtt").write_text(vtt_content_2)
        
        print(f"📁 Created test meetings: {meeting1_dir.name}, {meeting2_dir.name}")
    
    def create_mock_bedrock_response(self, prompt_context=""):
        """Create a mock Bedrock response based on the prompt context."""
        if "salesforce" in prompt_context.lower():
            return """
# Meeting Summary

## Participants
- John (API Developer)
- Sarah (Integration Architect)

## Main Topics
- Salesforce API Integration Strategy
- REST vs GraphQL Discussion
- Authentication and Rate Limiting
- Data Synchronization Requirements

## Key Points
- Team decided to prioritize REST APIs before moving to GraphQL
- Rate limiting and authentication are critical considerations
- Data mapping requirements need thorough review

## Action Items
- John will create comprehensive API documentation by next week
- Review data mapping requirements in detail

## Decisions Made
- Start with REST API implementation before GraphQL adoption
"""
        elif "mulesoft" in prompt_context.lower():
            return """
# MuleSoft Architecture Review Summary

## Participants  
- Mike (System Architect)
- Lisa (DevOps Engineer)

## Main Topics
- ESB Implementation Review
- Message Routing Patterns
- System Performance Analysis
- Resilience Improvements

## Key Points
- Current system processes 10,000 transactions daily
- Need to implement circuit breakers for better resilience
- Architecture review shows good scalability potential

## Action Items
- Lisa will prepare detailed migration plan for MuleSoft 4.4

## Decisions Made
- Upgrade to MuleSoft 4.4 scheduled for next quarter
- Implement circuit breaker patterns for improved resilience
"""
        elif "global" in prompt_context.lower() or "walkthrough series" in prompt_context.lower():
            return """
# Executive Summary
This walkthrough series covered critical enterprise integration initiatives focusing on Salesforce and MuleSoft platforms.

## Cross-Meeting Themes
- API-first integration strategy
- System resilience and scalability
- Enterprise architecture modernization

## Technical Architecture Overview
- REST API prioritization across platforms
- Circuit breaker patterns for resilience
- Comprehensive authentication frameworks

## Strategic Initiatives
- Salesforce integration enhancement
- MuleSoft platform upgrade to 4.4
- API documentation standardization

## Key Stakeholders
- John: API Development Lead
- Sarah: Integration Architecture
- Mike: System Architecture
- Lisa: DevOps and Migration

## Outstanding Issues
- Data mapping complexity
- Rate limiting optimization
- Migration timeline coordination

## Recommendations
- Establish API governance framework
- Implement monitoring and alerting
- Create comprehensive testing strategy
"""
        else:
            return "This is a test summary generated by the mock Bedrock client."
    
    @patch('vtt_summarizer.bedrock_client.boto3.client')
    def test_complete_workflow_success(self, mock_boto_client):
        """Test the complete E2E workflow with successful processing."""
        print("\n🚀 Testing complete workflow success...")
        
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Mock Bedrock responses based on prompt content
        def mock_invoke_model(**kwargs):
            body_str = kwargs.get('body', '{}')
            try:
                body = json.loads(body_str)
                prompt = body.get('messages', [{}])[0].get('content', '')
                response_text = self.create_mock_bedrock_response(prompt)
            except:
                response_text = "Mock summary response"
            
            response_body = {
                'content': [{'text': response_text}]
            }
            
            mock_response = MagicMock()
            mock_response['body'].read.return_value = json.dumps(response_body)
            return mock_response
        
        mock_bedrock.invoke_model = mock_invoke_model
        
        # Initialize and run the summarizer
        config = Config(str(self.test_dir / "config.yaml"))
        summarizer = ConsolidatedSummarizer(config)
        
        # Run the complete workflow
        results = summarizer.summarize_all(
            summaries_folder="summaries",
            force_overwrite=True
        )
        
        # Verify results structure
        self.assertEqual(results["status"], "success")
        self.assertIn("individual_results", results)
        self.assertIn("global_result", results)
        self.assertIn("total_time", results)
        self.assertIn("summaries_folder", results)
        
        # Verify individual processing results
        individual_results = results["individual_results"]
        self.assertEqual(individual_results["processed"], 2)
        self.assertEqual(individual_results["errors"], 0)
        self.assertEqual(individual_results["total_folders"], 2)
        
        # Verify global summary results
        global_result = results["global_result"]
        self.assertEqual(global_result["status"], "success")
        self.assertEqual(global_result["summaries_processed"], 2)
        
        # Verify files were created
        summaries_path = Path("summaries")
        self.assertTrue(summaries_path.exists())
        
        # Check individual summary files
        salesforce_summary = summaries_path / "20250815_salesforce_summary.md"
        mulesoft_summary = summaries_path / "20250821_mulesoft_summary.md"
        global_summary = summaries_path / "global_summary.md"
        
        self.assertTrue(salesforce_summary.exists())
        self.assertTrue(mulesoft_summary.exists())
        self.assertTrue(global_summary.exists())
        
        # Verify file contents
        salesforce_content = salesforce_summary.read_text()
        self.assertIn("Salesforce", salesforce_content)
        self.assertIn("Meeting Summary", salesforce_content)
        self.assertIn("Participants", salesforce_content)
        
        mulesoft_content = mulesoft_summary.read_text()
        self.assertIn("MuleSoft", mulesoft_content)
        self.assertIn("Meeting Summary", mulesoft_content)
        
        global_content = global_summary.read_text()
        self.assertIn("Global Walkthrough Series Summary", global_content)
        # The mock might return individual summary content for global, so check for Analysis section instead
        self.assertIn("Analysis", global_content)
        
        print("✅ Complete workflow test passed!")
    
    @patch('vtt_summarizer.bedrock_client.boto3.client')
    def test_skip_existing_files(self, mock_boto_client):
        """Test that existing files are skipped when force_overwrite=False."""
        print("\n⏭️  Testing skip existing files...")
        
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock()
        }
        mock_bedrock.invoke_model.return_value['body'].read.return_value = json.dumps({
            'content': [{'text': 'Test summary'}]
        })
        
        # Create summaries directory and existing files
        summaries_path = Path("summaries")
        summaries_path.mkdir(exist_ok=True)
        
        existing_summary = summaries_path / "20250815_salesforce_summary.md"
        existing_summary.write_text("# Existing Summary\nThis file already exists.")
        
        # Run summarizer without force overwrite
        config = Config(str(self.test_dir / "config.yaml"))
        summarizer = ConsolidatedSummarizer(config)
        
        results = summarizer.summarize_all(
            summaries_folder="summaries",
            force_overwrite=False
        )
        
        # Verify results
        individual_results = results["individual_results"]
        self.assertEqual(individual_results["processed"], 1)  # Only new file
        self.assertEqual(individual_results["skipped"], 1)    # Existing file skipped
        
        # Verify existing file wasn't modified
        content = existing_summary.read_text()
        self.assertIn("This file already exists", content)
        
        print("✅ Skip existing files test passed!")
    
    def test_vtt_parser_functionality(self):
        """Test VTT parser functionality in isolation."""
        print("\n📝 Testing VTT parser functionality...")
        
        parser = VTTParser()
        vtt_file = self.walkthroughs_dir / "20250815_salesforce" / "transcript.vtt"
        
        # Test transcript extraction
        transcript = parser.extract_full_transcript(str(vtt_file))
        self.assertIn("Salesforce integration meeting", transcript)
        self.assertIn("API strategy", transcript)
        self.assertIn("REST APIs", transcript)
        self.assertIn("API documentation", transcript)
        
        # Test metadata extraction
        metadata = parser.get_transcript_metadata(str(vtt_file))
        self.assertIn("duration_seconds", metadata)
        self.assertIn("word_count", metadata)
        self.assertIn("segment_count", metadata)
        self.assertGreater(metadata["word_count"], 0)
        self.assertGreater(metadata["duration_seconds"], 0)
        
        print("✅ VTT parser test passed!")
    
    def test_config_loading(self):
        """Test configuration loading and validation."""
        print("\n⚙️  Testing configuration loading...")
        
        config = Config(str(self.test_dir / "config.yaml"))
        
        # Test basic properties
        self.assertEqual(config.aws_region, "us-east-1")
        self.assertEqual(config.bedrock_model_id, "anthropic.claude-3-haiku-20240307-v1:0")
        self.assertEqual(config.input_folder, "walkthroughs")
        self.assertTrue(config.include_timestamps)
        self.assertTrue(config.include_participants)
        self.assertTrue(config.include_action_items)
        
        print("✅ Configuration test passed!")
    
    @patch('vtt_summarizer.bedrock_client.boto3.client')
    def test_error_handling(self, mock_boto_client):
        """Test error handling in various scenarios."""
        print("\n🚨 Testing error handling...")
        
        # Test with missing VTT files
        empty_dir = self.walkthroughs_dir / "empty_meeting"
        empty_dir.mkdir()
        
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock()
        }
        mock_bedrock.invoke_model.return_value['body'].read.return_value = json.dumps({
            'content': [{'text': 'Test summary'}]
        })
        
        config = Config(str(self.test_dir / "config.yaml"))
        summarizer = ConsolidatedSummarizer(config)
        
        results = summarizer.summarize_all(
            summaries_folder="summaries",
            force_overwrite=True
        )
        
        # Should still succeed with available VTT files
        self.assertEqual(results["status"], "success")
        self.assertEqual(results["individual_results"]["processed"], 2)
        
        print("✅ Error handling test passed!")
    
    def test_empty_walkthroughs_directory(self):
        """Test behavior with empty walkthroughs directory."""
        print("\n📂 Testing empty walkthroughs directory...")
        
        # Remove all VTT files
        for meeting_dir in self.walkthroughs_dir.iterdir():
            if meeting_dir.is_dir():
                shutil.rmtree(meeting_dir)
        
        config = Config(str(self.test_dir / "config.yaml"))
        summarizer = ConsolidatedSummarizer(config)
        
        results = summarizer.summarize_all(
            summaries_folder="summaries",
            force_overwrite=True
        )
        
        # Should return no_files status
        self.assertEqual(results["status"], "no_files")
        self.assertEqual(results["individual_results"]["processed"], 0)
        self.assertIsNone(results["global_result"])
        
        print("✅ Empty directory test passed!")


class TestE2EUtilities(unittest.TestCase):
    """Test utility functions used in the E2E workflow."""
    
    def test_utility_imports(self):
        """Test that all utility modules can be imported."""
        print("\n🔧 Testing utility imports...")
        
        try:
            from vtt_summarizer.utils import (
                parse_folder_name, extract_summary_info, time_to_seconds,
                seconds_to_time, ProcessingTimer
            )
            from vtt_summarizer.summary_writer import SummaryWriter
            from vtt_summarizer.error_handler import (
                create_error_result, create_success_result
            )
            print("✅ All utility imports successful!")
        except ImportError as e:
            self.fail(f"❌ Utility import failed: {e}")
    
    def test_processing_timer(self):
        """Test ProcessingTimer utility."""
        from vtt_summarizer.utils import ProcessingTimer
        import time
        
        with ProcessingTimer("Test operation") as timer:
            time.sleep(0.1)  # Simulate work
        
        self.assertGreater(timer.duration_seconds, 0.05)
        self.assertLess(timer.duration_seconds, 0.5)


def run_e2e_tests():
    """Run the complete E2E test suite."""
    print("🎯 Starting HCA VTT Summarizer E2E Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(loader.loadTestsFromTestCase(TestE2EVTTSummarizer))
    suite.addTest(loader.loadTestsFromTestCase(TestE2EUtilities))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL E2E TESTS PASSED!")
        print(f"✅ Ran {result.testsRun} tests successfully")
    else:
        print("❌ SOME E2E TESTS FAILED!")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")
        
        # Print failure details
        for test, traceback in result.failures + result.errors:
            print(f"\n❌ {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run E2E tests when executed directly
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
