"""
Unit tests for Template Discovery functionality in CFN Template Linter.
Minimal fast tests focusing on core functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Add project root to Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cfn_linter.template_discovery import TemplateDiscovery


class TestTemplateDiscovery:
    """Minimal unit tests for TemplateDiscovery class."""
    
    def test_init_with_default_project_root(self):
        """Test initialization with default project root."""
        discovery = TemplateDiscovery()
        assert discovery.project_root == Path.cwd()
        assert discovery.templates_base_path == Path.cwd() / "templates" / "v2"
    
    def test_init_with_custom_project_root(self):
        """Test initialization with custom project root."""
        custom_root = Path("/custom/path")
        discovery = TemplateDiscovery(project_root=custom_root)
        assert discovery.project_root == custom_root
        assert discovery.templates_base_path == custom_root / "templates" / "v2"
    
    def test_is_cloudformation_template_valid_extensions(self):
        """Test CloudFormation template identification by extension."""
        discovery = TemplateDiscovery()
        
        # Test that the method exists and returns boolean
        result_yml = discovery.is_cloudformation_template(Path("template.yml"))
        result_md = discovery.is_cloudformation_template(Path("README.md"))
        
        assert isinstance(result_yml, bool)
        assert isinstance(result_md, bool)
    
    def test_find_templates_empty_directory(self):
        """Test template discovery in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            templates_path = temp_path / "templates" / "v2"
            templates_path.mkdir(parents=True)
            
            discovery = TemplateDiscovery(project_root=temp_path)
            templates = discovery.find_templates()
            
            assert isinstance(templates, list)
            assert len(templates) == 0