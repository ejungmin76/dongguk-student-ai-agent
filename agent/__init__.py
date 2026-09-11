"""Google ADK orchestration package.

This package coordinates plans and responses. It must not access Django models
or repositories directly.
"""

from .agent import root_agent

__all__ = ["root_agent"]
