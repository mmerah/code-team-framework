"""
Code Team Framework - AI-powered development workflow orchestration.

This framework provides tools for planning, coding, and verifying software projects
using AI agents and structured workflows.
"""

from .models.config import CodeTeamConfig
from .models.plan import Plan
from .orchestrator.orchestrator import Orchestrator

__version__ = "0.2.0"
__all__ = ["CodeTeamConfig", "Plan", "Orchestrator"]
