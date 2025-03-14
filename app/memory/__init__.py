# app/memory/__init__.py
# Make the 'memory' directory a package. This allows for absolute imports.

from .base import BaseMemory, get_memory, SimpleMemory  # Export for easy access
__all__ = ["BaseMemory", "get_memory", "SimpleMemory"]