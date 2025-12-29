"""
AgentCore Memory integration for customer support agent.

This module provides memory hooks and configuration for enabling
persistent customer context across conversations.
"""

from .client import CustomerSupportMemoryHooks, get_memory_config

__all__ = ["CustomerSupportMemoryHooks", "get_memory_config"]
