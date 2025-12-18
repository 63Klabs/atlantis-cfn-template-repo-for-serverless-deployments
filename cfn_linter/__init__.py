"""
CFN Template Linter package.
Provides CloudFormation template validation using cfn-lint with virtual environment isolation.
"""

from .venv_manager import VirtualEnvManager
from .template_discovery import TemplateDiscovery
from .validation import CFNValidator, ValidationResult, ValidationSummary, ValidationError

__version__ = "1.0.0"
__all__ = ["VirtualEnvManager", "TemplateDiscovery", "CFNValidator", "ValidationResult", "ValidationSummary", "ValidationError"]