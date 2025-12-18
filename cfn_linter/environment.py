"""
Environment Detection and Configuration for CFN Template Linter.
Handles detection of local vs build contexts and ensures consistent validation logic.
"""

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
import logging


class ExecutionContext(Enum):
    """Enumeration of execution contexts."""
    LOCAL = "local"
    BUILD_PIPELINE = "build_pipeline"
    PYTEST = "pytest"
    UNKNOWN = "unknown"


@dataclass
class EnvironmentConfig:
    """Configuration for the current execution environment."""
    context: ExecutionContext
    project_root: Path
    venv_path: Path
    is_ci: bool
    python_executable: str
    environment_variables: Dict[str, str]
    validation_config: Dict[str, Any]


class EnvironmentDetector:
    """Detects and configures the execution environment."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the environment detector.
        
        Args:
            project_root: Path to project root. If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()
        self.logger = logging.getLogger(__name__)
    
    def detect_execution_context(self) -> ExecutionContext:
        """Detect the current execution context.
        
        Returns:
            ExecutionContext enum value indicating the detected context.
        """
        # Check for pytest execution
        if self._is_pytest_context():
            return ExecutionContext.PYTEST
        
        # Check for build pipeline context
        if self._is_build_pipeline_context():
            return ExecutionContext.BUILD_PIPELINE
        
        # Check for local development context
        if self._is_local_context():
            return ExecutionContext.LOCAL
        
        return ExecutionContext.UNKNOWN
    
    def _is_pytest_context(self) -> bool:
        """Check if running in pytest context."""
        # Check if pytest is in the call stack
        import inspect
        
        for frame_info in inspect.stack():
            if 'pytest' in frame_info.filename.lower():
                return True
        
        # Check for pytest environment variables
        pytest_vars = ['PYTEST_CURRENT_TEST', '_PYTEST_RAISE', 'PYTEST_VERSION']
        for var in pytest_vars:
            if var in os.environ:
                return True
        
        # Check if pytest module is imported
        if 'pytest' in sys.modules:
            return True
        
        return False
    
    def _is_build_pipeline_context(self) -> bool:
        """Check if running in build pipeline context."""
        # Common CI/CD environment variables
        ci_indicators = [
            'CI',                    # Generic CI indicator
            'CONTINUOUS_INTEGRATION', # Generic CI indicator
            'BUILD_ID',              # Generic build ID
            'BUILD_NUMBER',          # Generic build number
            'CODEBUILD_BUILD_ID',    # AWS CodeBuild
            'CODEBUILD_BUILD_ARN',   # AWS CodeBuild
            'JENKINS_URL',           # Jenkins
            'GITHUB_ACTIONS',        # GitHub Actions
            'GITLAB_CI',             # GitLab CI
            'TRAVIS',                # Travis CI
            'CIRCLECI',              # CircleCI
            'BUILDKITE',             # Buildkite
            'TEAMCITY_VERSION',      # TeamCity
        ]
        
        for indicator in ci_indicators:
            if indicator in os.environ:
                return True
        
        # Check for buildspec execution (AWS CodeBuild specific)
        if os.environ.get('CODEBUILD_SRC_DIR'):
            return True
        
        # Check if running from a build script
        script_name = os.path.basename(sys.argv[0]) if sys.argv else ''
        build_script_indicators = [
            'cfn_lint_runner.py',  # Still check basename since it's in scripts/
            'build.py',
            'pipeline.py'
        ]
        
        if script_name in build_script_indicators:
            return True
        
        return False
    
    def _is_local_context(self) -> bool:
        """Check if running in local development context."""
        # If not CI and not pytest, assume local
        return not self._is_build_pipeline_context() and not self._is_pytest_context()
    
    def is_ci_environment(self) -> bool:
        """Check if running in any CI/CD environment."""
        return self._is_build_pipeline_context()
    
    def get_environment_config(self) -> EnvironmentConfig:
        """Get complete environment configuration.
        
        Returns:
            EnvironmentConfig with all detected settings.
        """
        context = self.detect_execution_context()
        is_ci = self.is_ci_environment()
        
        # Determine virtual environment path
        venv_path = self.project_root / ".venv"
        
        # Get Python executable
        python_executable = sys.executable
        
        # Collect relevant environment variables
        env_vars = {}
        relevant_vars = [
            'PATH', 'PYTHONPATH', 'VIRTUAL_ENV',
            'CI', 'BUILD_ID', 'CODEBUILD_BUILD_ID',
            'PYTEST_CURRENT_TEST'
        ]
        
        for var in relevant_vars:
            if var in os.environ:
                env_vars[var] = os.environ[var]
        
        # Create validation configuration based on context
        validation_config = self._get_validation_config(context, is_ci)
        
        return EnvironmentConfig(
            context=context,
            project_root=self.project_root,
            venv_path=venv_path,
            is_ci=is_ci,
            python_executable=python_executable,
            environment_variables=env_vars,
            validation_config=validation_config
        )
    
    def _get_validation_config(self, context: ExecutionContext, is_ci: bool) -> Dict[str, Any]:
        """Get validation configuration based on execution context.
        
        Args:
            context: Detected execution context
            is_ci: Whether running in CI environment
            
        Returns:
            Dictionary with validation configuration settings.
        """
        config = {
            'timeout_seconds': 60,
            'fail_on_warnings': False,
            'verbose_output': False,
            'use_venv': True,
            'parallel_execution': False
        }
        
        # Adjust configuration based on context
        if context == ExecutionContext.BUILD_PIPELINE:
            config.update({
                'timeout_seconds': 120,  # Longer timeout for build environments
                'fail_on_warnings': False,  # Don't fail on warnings by default
                'verbose_output': True,  # More verbose in build logs
                'parallel_execution': False  # Keep sequential for build stability
            })
        elif context == ExecutionContext.PYTEST:
            config.update({
                'timeout_seconds': 30,  # Shorter timeout for tests
                'fail_on_warnings': False,
                'verbose_output': False,  # Less verbose in test output
                'parallel_execution': False
            })
        elif context == ExecutionContext.LOCAL:
            config.update({
                'timeout_seconds': 60,
                'fail_on_warnings': False,
                'verbose_output': True,  # Helpful for local development
                'parallel_execution': False
            })
        
        # CI-specific adjustments
        if is_ci:
            config.update({
                'verbose_output': True,  # Always verbose in CI
                'fail_fast': True  # Fail fast in CI to save resources
            })
        
        return config
    
    def verify_environment_consistency(self) -> tuple[bool, list[str]]:
        """Verify that the environment is set up consistently.
        
        Returns:
            Tuple of (is_consistent, list_of_issues)
        """
        issues = []
        
        # Check project root exists
        if not self.project_root.exists():
            issues.append(f"Project root does not exist: {self.project_root}")
        
        # Check virtual environment
        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            issues.append(f"Virtual environment does not exist: {venv_path}")
        else:
            # Check virtual environment structure
            if os.name == 'nt':  # Windows
                python_exe = venv_path / "Scripts" / "python.exe"
            else:  # Unix/Linux/macOS
                python_exe = venv_path / "bin" / "python"
            
            if not python_exe.exists():
                issues.append(f"Python executable not found in virtual environment: {python_exe}")
        
        # Check Python version consistency
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                issues.append("Cannot determine Python version")
        except Exception as e:
            issues.append(f"Error checking Python version: {e}")
        
        # Check for required modules
        required_modules = ['pathlib', 'subprocess', 'json']
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                issues.append(f"Required module not available: {module}")
        
        return len(issues) == 0, issues
    
    def get_environment_summary(self) -> str:
        """Get a human-readable summary of the environment.
        
        Returns:
            Formatted string with environment information.
        """
        config = self.get_environment_config()
        
        lines = []
        lines.append("Environment Configuration Summary")
        lines.append("=" * 40)
        lines.append(f"Execution Context: {config.context.value}")
        lines.append(f"Project Root: {config.project_root}")
        lines.append(f"Virtual Environment: {config.venv_path}")
        lines.append(f"CI Environment: {config.is_ci}")
        lines.append(f"Python Executable: {config.python_executable}")
        
        lines.append("\nValidation Configuration:")
        for key, value in config.validation_config.items():
            lines.append(f"  {key}: {value}")
        
        lines.append("\nEnvironment Variables:")
        for key, value in config.environment_variables.items():
            # Truncate long values
            display_value = value[:50] + "..." if len(value) > 50 else value
            lines.append(f"  {key}: {display_value}")
        
        # Add consistency check
        is_consistent, issues = self.verify_environment_consistency()
        lines.append(f"\nEnvironment Consistency: {'✓ PASS' if is_consistent else '✗ ISSUES'}")
        
        if issues:
            lines.append("Issues found:")
            for issue in issues:
                lines.append(f"  - {issue}")
        
        return "\n".join(lines)


class EnvironmentManager:
    """Manages environment configuration and ensures consistency across contexts."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the environment manager.
        
        Args:
            project_root: Path to project root. If None, uses current working directory.
        """
        self.detector = EnvironmentDetector(project_root)
        self.config = self.detector.get_environment_config()
        self.logger = logging.getLogger(__name__)
    
    def ensure_consistent_environment(self) -> bool:
        """Ensure the environment is set up consistently.
        
        Returns:
            True if environment is consistent, False otherwise.
        """
        is_consistent, issues = self.detector.verify_environment_consistency()
        
        if not is_consistent:
            self.logger.warning("Environment consistency issues detected:")
            for issue in issues:
                self.logger.warning(f"  - {issue}")
        
        return is_consistent
    
    def get_validation_timeout(self) -> int:
        """Get the appropriate validation timeout for the current context.
        
        Returns:
            Timeout in seconds.
        """
        return self.config.validation_config.get('timeout_seconds', 60)
    
    def should_fail_on_warnings(self) -> bool:
        """Check if validation should fail on warnings in the current context.
        
        Returns:
            True if should fail on warnings, False otherwise.
        """
        return self.config.validation_config.get('fail_on_warnings', False)
    
    def should_use_verbose_output(self) -> bool:
        """Check if verbose output should be used in the current context.
        
        Returns:
            True if should use verbose output, False otherwise.
        """
        return self.config.validation_config.get('verbose_output', False)
    
    def get_venv_path(self) -> Path:
        """Get the virtual environment path.
        
        Returns:
            Path to the virtual environment directory.
        """
        return self.config.venv_path
    
    def is_venv_required(self) -> bool:
        """Check if virtual environment usage is required.
        
        Returns:
            True if virtual environment should be used, False otherwise.
        """
        return self.config.validation_config.get('use_venv', True)
    
    def get_execution_context(self) -> ExecutionContext:
        """Get the current execution context.
        
        Returns:
            ExecutionContext enum value.
        """
        return self.config.context
    
    def is_ci_environment(self) -> bool:
        """Check if running in CI environment.
        
        Returns:
            True if running in CI, False otherwise.
        """
        return self.config.is_ci