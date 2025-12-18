"""
Unit tests for pytest integration in CFN Template Linter.
Minimal fast tests focusing on core functionality.
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPytestIntegration:
    """Minimal unit tests for pytest integration."""
    
    def test_pytest_can_import_cfn_modules(self):
        """Test that pytest can import CFN linter modules."""
        # Test basic imports work
        from cfn_linter.template_discovery import TemplateDiscovery
        from cfn_linter.validation import CFNValidator
        
        assert TemplateDiscovery is not None
        assert CFNValidator is not None
    
    def test_pytest_test_discovery_works(self):
        """Test that pytest can discover this test file."""
        # This test existing and running proves pytest discovery works
        assert True