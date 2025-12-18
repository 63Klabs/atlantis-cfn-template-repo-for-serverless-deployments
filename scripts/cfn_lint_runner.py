#!/usr/bin/env python3
"""
CloudFormation Template Linter - Build Pipeline Runner

Standalone script for executing CloudFormation template validation in build pipelines.
Provides command-line interface with appropriate exit codes for CI/CD integration.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cfn_linter.template_discovery import TemplateDiscovery
from cfn_linter.validation import CFNValidator, ValidationSummary
from cfn_linter.environment import EnvironmentManager, ExecutionContext


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='CloudFormation Template Linter for Build Pipelines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 - All templates validated successfully
  1 - Validation failures detected
  2 - No templates found
  3 - Environment setup error
  4 - Execution error
        """
    )
    
    parser.add_argument(
        '--templates-dir',
        type=str,
        default='templates/v2',
        help='Directory containing CloudFormation templates (default: templates/v2)'
    )
    
    parser.add_argument(
        '--project-root',
        type=str,
        default=None,
        help='Project root directory (default: current directory)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress all output except errors'
    )
    
    parser.add_argument(
        '--fail-on-warnings',
        action='store_true',
        help='Treat warnings as failures'
    )
    
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Show only summary, not detailed errors'
    )
    
    return parser.parse_args()


def setup_environment(project_root: Path, verbose: bool = False) -> tuple[bool, Optional[str]]:
    """Set up the validation environment.
    
    Args:
        project_root: Path to project root directory
        verbose: Enable verbose output
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        from cfn_linter.venv_manager import VirtualEnvManager
        
        venv_manager = VirtualEnvManager(project_root)
        
        if verbose:
            print("Setting up virtual environment...")
        
        # Ensure virtual environment exists
        if not venv_manager.ensure_venv_exists():
            return False, "Failed to create or verify virtual environment"
        
        if verbose:
            print("Checking cfn-lint availability...")
        
        # Check if cfn-lint is available
        if not venv_manager.is_cfn_lint_available():
            if verbose:
                print("cfn-lint not found, installing dependencies...")
            
            if not venv_manager.install_dependencies():
                return False, "Failed to install cfn-lint dependencies"
        
        if verbose:
            print("Environment setup complete")
        
        return True, None
        
    except Exception as e:
        return False, f"Environment setup error: {str(e)}"


def discover_templates(project_root: Path, templates_dir: str, verbose: bool = False) -> tuple[list, Optional[str]]:
    """Discover CloudFormation templates.
    
    Args:
        project_root: Path to project root directory
        templates_dir: Relative path to templates directory
        verbose: Enable verbose output
        
    Returns:
        Tuple of (template_paths, error_message)
    """
    try:
        discovery = TemplateDiscovery(project_root=project_root)
        
        # Use custom templates directory if specified
        templates_path = project_root / templates_dir
        
        if verbose:
            print(f"Discovering templates in: {templates_path}")
        
        template_paths = discovery.find_templates(base_path=templates_path)
        
        if verbose:
            print(f"Found {len(template_paths)} template(s)")
        
        return template_paths, None
        
    except Exception as e:
        return [], f"Template discovery error: {str(e)}"


def validate_templates(
    project_root: Path,
    template_paths: list,
    verbose: bool = False,
    fail_on_warnings: bool = False
) -> tuple[ValidationSummary, Optional[str]]:
    """Validate CloudFormation templates.
    
    Args:
        project_root: Path to project root directory
        template_paths: List of template paths to validate
        verbose: Enable verbose output
        fail_on_warnings: Treat warnings as failures
        
    Returns:
        Tuple of (validation_summary, error_message)
    """
    try:
        validator = CFNValidator(project_root=project_root)
        
        if verbose:
            print(f"Validating {len(template_paths)} template(s)...")
        
        summary = validator.validate_all_templates(template_paths)
        
        if verbose:
            print(f"Validation complete in {summary.execution_time:.2f}s")
        
        return summary, None
        
    except Exception as e:
        return None, f"Validation execution error: {str(e)}"


def format_summary_output(summary: ValidationSummary, verbose: bool = False) -> str:
    """Format validation summary for output.
    
    Args:
        summary: Validation summary to format
        verbose: Enable verbose output
        
    Returns:
        Formatted summary string
    """
    lines = []
    
    lines.append("=" * 60)
    lines.append("CloudFormation Template Validation Summary")
    lines.append("=" * 60)
    lines.append(f"Total templates:   {summary.total_templates}")
    lines.append(f"Valid templates:   {summary.valid_templates}")
    lines.append(f"Failed templates:  {summary.failed_templates}")
    lines.append(f"Total errors:      {summary.total_errors}")
    lines.append(f"Total warnings:    {summary.total_warnings}")
    
    if summary.total_templates > 0:
        success_rate = (summary.valid_templates / summary.total_templates) * 100
        lines.append(f"Success rate:      {success_rate:.1f}%")
    
    if verbose:
        lines.append(f"Execution time:    {summary.execution_time:.2f}s")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def format_detailed_output(summary: ValidationSummary, project_root: Path) -> str:
    """Format detailed validation output.
    
    Args:
        summary: Validation summary to format
        project_root: Project root for relative paths
        
    Returns:
        Formatted detailed output string
    """
    lines = []
    
    # Show successful templates
    valid_results = [r for r in summary.results if r.is_valid]
    if valid_results:
        lines.append("\nSuccessfully Validated Templates:")
        lines.append("-" * 40)
        for result in valid_results:
            try:
                relative_path = result.template_path.relative_to(project_root)
            except ValueError:
                relative_path = result.template_path
            
            warning_text = f" ({len(result.warnings)} warnings)" if result.warnings else ""
            lines.append(f"  ✓ {relative_path}{warning_text}")
    
    # Show failed templates with details
    failed_results = [r for r in summary.results if not r.is_valid]
    if failed_results:
        lines.append("\nFailed Templates:")
        lines.append("-" * 40)
        
        for result in failed_results:
            try:
                relative_path = result.template_path.relative_to(project_root)
            except ValueError:
                relative_path = result.template_path
            
            lines.append(f"\n✗ {relative_path}")
            lines.append(f"  Errors: {len(result.errors)}, Warnings: {len(result.warnings)}")
            
            # Show errors
            for error in result.errors:
                location = ""
                if error.line_number:
                    location = f" (line {error.line_number}"
                    if error.column_number:
                        location += f", col {error.column_number}"
                    location += ")"
                
                lines.append(f"    ERROR [{error.rule_id}]: {error.message}{location}")
            
            # Show warnings
            for warning in result.warnings:
                location = ""
                if warning.line_number:
                    location = f" (line {warning.line_number}"
                    if warning.column_number:
                        location += f", col {warning.column_number}"
                    location += ")"
                
                lines.append(f"    WARNING [{warning.rule_id}]: {warning.message}{location}")
    
    return "\n".join(lines)


def main():
    """Main entry point for the build pipeline runner."""
    args = parse_arguments()
    
    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = Path.cwd()
    
    # Validate project root exists
    if not project_root.exists():
        print(f"ERROR: Project root does not exist: {project_root}", file=sys.stderr)
        return 4
    
    # Initialize environment manager for consistent configuration
    env_manager = EnvironmentManager(project_root)
    
    # Verify environment consistency
    if not env_manager.ensure_consistent_environment():
        print("WARNING: Environment consistency issues detected", file=sys.stderr)
        if args.verbose:
            print(env_manager.detector.get_environment_summary())
    
    # Log execution context for debugging
    if args.verbose:
        context = env_manager.get_execution_context()
        print(f"Detected execution context: {context.value}")
        if context == ExecutionContext.BUILD_PIPELINE:
            print("Running in build pipeline mode with extended timeouts")
        elif context == ExecutionContext.LOCAL:
            print("Running in local development mode")
    
    # Step 1: Set up environment
    if not args.quiet:
        if args.verbose:
            print("Step 1: Setting up validation environment...")
    
    success, error = setup_environment(project_root, verbose=args.verbose)
    if not success:
        print(f"ERROR: {error}", file=sys.stderr)
        return 3
    
    # Step 2: Discover templates
    if not args.quiet:
        if args.verbose:
            print("\nStep 2: Discovering CloudFormation templates...")
    
    template_paths, error = discover_templates(
        project_root,
        args.templates_dir,
        verbose=args.verbose
    )
    
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 4
    
    if len(template_paths) == 0:
        if not args.quiet:
            print(f"WARNING: No CloudFormation templates found in {args.templates_dir}")
            print("This may indicate a configuration issue or empty templates directory.")
        return 2
    
    # Step 3: Validate templates
    if not args.quiet:
        if args.verbose:
            print(f"\nStep 3: Validating {len(template_paths)} template(s)...")
    
    summary, error = validate_templates(
        project_root,
        template_paths,
        verbose=args.verbose,
        fail_on_warnings=args.fail_on_warnings
    )
    
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 4
    
    # Step 4: Report results
    if not args.quiet:
        print("\n" + format_summary_output(summary, verbose=args.verbose))
        
        if not args.summary_only:
            print(format_detailed_output(summary, project_root))
    
    # Determine exit code
    if summary.failed_templates > 0:
        if not args.quiet:
            print("\n❌ Validation FAILED", file=sys.stderr)
        return 1
    
    if args.fail_on_warnings and summary.total_warnings > 0:
        if not args.quiet:
            print("\n❌ Validation FAILED (warnings treated as failures)", file=sys.stderr)
        return 1
    
    if not args.quiet:
        print("\n✅ Validation PASSED")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
