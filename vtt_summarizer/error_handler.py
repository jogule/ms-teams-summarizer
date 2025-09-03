"""Standardized error handling utilities."""

import logging
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager

from .utils import get_iso_timestamp


class VTTSummarizerError(Exception):
    """Base exception for VTT Summarizer errors."""
    pass


class ConfigurationError(VTTSummarizerError):
    """Configuration-related errors."""
    pass


class ProcessingError(VTTSummarizerError):
    """Processing-related errors."""
    pass


class FileError(VTTSummarizerError):
    """File operation errors."""
    pass


class BedrockError(VTTSummarizerError):
    """AWS Bedrock API errors."""
    pass


def create_error_result(status: str, error: str, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized error result dictionary.
    
    Args:
        status: Error status
        error: Error message
        **kwargs: Additional fields
        
    Returns:
        Error result dictionary
    """
    result = {
        "status": status,
        "error": str(error),
        "timestamp": get_iso_timestamp()
    }
    result.update(kwargs)
    return result


def create_success_result(status: str = "success", **kwargs) -> Dict[str, Any]:
    """
    Create a standardized success result dictionary.
    
    Args:
        status: Success status
        **kwargs: Additional fields
        
    Returns:
        Success result dictionary
    """
    result = {
        "status": status,
        "timestamp": get_iso_timestamp()
    }
    result.update(kwargs)
    return result


@contextmanager
def handle_processing_errors(logger: logging.Logger, operation: str, 
                           context: Optional[Dict[str, Any]] = None):
    """
    Context manager for standardized error handling.
    
    Args:
        logger: Logger instance
        operation: Description of the operation
        context: Additional context for error reporting
        
    Yields:
        None
        
    Raises:
        ProcessingError: On any error during processing
    """
    try:
        logger.info(f"Starting {operation}")
        yield
        logger.info(f"Completed {operation}")
    except FileNotFoundError as e:
        logger.error(f"File not found during {operation}: {str(e)}")
        raise FileError(f"Required file not found: {str(e)}")
    except PermissionError as e:
        logger.error(f"Permission denied during {operation}: {str(e)}")
        raise FileError(f"Permission denied: {str(e)}")
    except Exception as e:
        context_str = f" (Context: {context})" if context else ""
        logger.error(f"Error during {operation}: {str(e)}{context_str}")
        raise ProcessingError(f"Failed to {operation}: {str(e)}")


def safe_execute(func: Callable, logger: logging.Logger, 
                operation: str, *args, **kwargs) -> Dict[str, Any]:
    """
    Safely execute a function with standardized error handling.
    
    Args:
        func: Function to execute
        logger: Logger instance
        operation: Operation description
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Result dictionary with success or error status
    """
    try:
        with handle_processing_errors(logger, operation):
            result = func(*args, **kwargs)
            return create_success_result(**result) if isinstance(result, dict) else create_success_result(result=result)
    except VTTSummarizerError as e:
        return create_error_result("error", str(e))
    except Exception as e:
        logger.error(f"Unexpected error in {operation}: {str(e)}")
        return create_error_result("error", f"Unexpected error: {str(e)}")


def log_and_reraise(logger: logging.Logger, error: Exception, context: str) -> None:
    """
    Log an error and re-raise it as a ProcessingError.
    
    Args:
        logger: Logger instance
        error: Original exception
        context: Context description
        
    Raises:
        ProcessingError: Always raises this with the original error message
    """
    logger.error(f"Error in {context}: {str(error)}")
    raise ProcessingError(f"Failed in {context}: {str(error)}")
