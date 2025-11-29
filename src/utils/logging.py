"""
Logging Utilities

Provides standardized logging setup for all agents.
"""

import logging
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with standardized configuration.

    Args:
        name: Logger name (typically agent name)
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger("MyAgent")
        >>> logger.info("Agent initialized")
    """
    logger = logging.getLogger(name)

    # Only add handler if it doesn't already have one
    if not logger.handlers:
        handler = logging.StreamHandler()

        # Use custom format or default
        if format_string is None:
            format_string = f'%(asctime)s - {name} - %(levelname)s - %(message)s'

        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger
