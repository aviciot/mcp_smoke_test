"""
Example Tool - Echo with Error Handling
========================================
Demonstrates proper tool implementation with error handling pattern
"""

import logging
from mcp_app import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def echo(message: str, repeat: int = 1) -> str:
    """
    Echo a message back, optionally repeating it
    
    This demonstrates the proper error handling pattern for MCP tools:
    - Validate inputs
    - Handle exceptions gracefully
    - Return user-friendly error messages
    - Log errors for debugging
    
    Args:
        message: The message to echo
        repeat: Number of times to repeat (default: 1, max: 10)
    
    Returns:
        str: The echoed message or error message
    """
    try:
        # Validate inputs
        if not message:
            return "Error: message cannot be empty"
        
        if not isinstance(repeat, int):
            return f"Error: repeat must be an integer, got {type(repeat).__name__}"
        
        if repeat < 1:
            return "Error: repeat must be at least 1"
        
        if repeat > 10:
            return "Error: repeat cannot exceed 10 (got {repeat})"
        
        # Build response
        result = "\n".join([message] * repeat)
        
        # Return string directly - FastMCP handles the response format
        return result
        
    except Exception as e:
        # Log the full exception for debugging
        logger.exception(f"Unexpected error in echo tool: {e}")
        
        # Return user-friendly error message (don't expose stack traces)
        return f"Error: An unexpected error occurred. Please contact support."

