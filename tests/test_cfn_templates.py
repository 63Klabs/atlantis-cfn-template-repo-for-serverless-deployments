"""
Integration test for CloudFormation template validation.
Minimal fast test focusing on core functionality.
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cfn_linter.template_discovery import TemplateDiscovery
from cfn_linter.validation import CFNValidator


def test_cfn_template_discovery():
    """Test that CloudFormation template discovery works correctly."""
    project_root = Path(__file__).parent.parent
    discovery = TemplateDiscovery(project_root=project_root)
    
    # Test that discovery can be instantiated and run
    templates = discovery.find_templates()
    
    # Should return a list (may be empty if no templates exist)
    assert isinstance(templates, list)
    
    # If templates exist, they should be Path objects
    for template in templates:
        assert isinstance(template, Path)
        assert template.exists()


def test_cfn_validator_initialization():
    """Test that CFN validator can be initialized."""
    project_root = Path(__file__).parent.parent
    validator = CFNValidator(project_root=project_root)
    
    # Should be able to create validator instance
    assert validator is not None
    assert validator.project_root == project_root