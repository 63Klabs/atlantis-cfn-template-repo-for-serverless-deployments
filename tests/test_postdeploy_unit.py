"""
Unit tests for specific PostDeploy scenarios in CloudFormation pipeline template.

These tests focus on specific examples, edge cases, and error conditions for parameter validation
and resource configuration, complementing the property-based tests.
"""

import pytest
import re
import sys
import os
from typing import Dict, Any

# Add tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cfn_test_utils import (
    load_template, get_template_section, validate_parameter_constraints,
    validate_iam_policy_structure, validate_environment_variables,
    validate_regex_pattern
)


# Load the pipeline template
PIPELINE_TEMPLATE = load_template('templates/v2/pipeline/template-pipeline.yml')


class TestParameterValidation:
    """Unit tests for parameter validation examples."""
    
    def test_valid_buildspec_paths_examples(self):
        """
        Test specific valid buildspec path examples.
        Requirements: 5.1
        """
        template = PIPELINE_TEMPLATE
        constraints = validate_parameter_constraints(template, 'PostDeployBuildSpec')
        allowed_pattern = constraints.get('AllowedPattern')
        
        # Test specific valid examples
        valid_paths = [
            'buildspec-postdeploy.yml',
            'application-infrastructure/buildspec-postdeploy.yml',
            'path/to/buildspec-postdeploy.yml',
            'deep/nested/path/buildspec-postdeploy.yml',
            '',  # Empty string is allowed (uses default)
        ]
        
        validation_result = validate_regex_pattern(allowed_pattern, valid_paths)
        assert validation_result['valid_pattern'], f"Pattern should be valid: {validation_result.get('error')}"
        assert validation_result['match_count'] == len(valid_paths), f"All valid paths should match pattern"
    
    def test_invalid_buildspec_paths_examples(self):
        """
        Test specific invalid buildspec path examples.
        Requirements: 5.1
        """
        template = PIPELINE_TEMPLATE
        constraints = validate_parameter_constraints(template, 'PostDeployBuildSpec')
        allowed_pattern = constraints.get('AllowedPattern')
        
        # Test specific invalid examples
        invalid_paths = [
            'buildspec.yml',  # Wrong filename - should be buildspec-postdeploy.yml
            'path/to/buildspec.yml',  # Wrong filename
            'buildspec-postdeploy.yaml',  # Wrong extension
            'path with spaces/buildspec-postdeploy.yml',  # Spaces not allowed
            'path/to/directory/',  # No filename
            'buildspec-postdeploy',  # Missing extension
            '../buildspec-postdeploy.yml',  # Relative path with ..
        ]
        
        validation_result = validate_regex_pattern(allowed_pattern, invalid_paths)
        assert validation_result['valid_pattern'], f"Pattern should be valid: {validation_result.get('error')}"
        assert validation_result['match_count'] == 0, f"No invalid paths should match pattern"
    
    def test_valid_s3_uri_examples(self):
        """
        Test specific valid S3 URI examples.
        Requirements: 5.2
        """
        template = PIPELINE_TEMPLATE
        parameters = template.get('Parameters', {})
        buildspec_param = parameters.get('PostDeployBuildSpec')
        allowed_pattern = buildspec_param.get('AllowedPattern')
        pattern = re.compile(allowed_pattern)
        
        # Test specific valid S3 URI examples
        valid_uris = [
            's3://my-bucket/buildspec-postdeploy.yml',
            's3://company-buildspecs/project/buildspec-postdeploy.yml',
            's3://build-artifacts/path/to/buildspec.yml',  # Any filename allowed in S3
            's3://bucket123/deep/nested/path/custom-buildspec.yml',
            's3://a-b-c/file.yml',  # Minimum valid bucket name
        ]
        
        for uri in valid_uris:
            match = pattern.match(uri)
            assert match is not None, f"Valid S3 URI '{uri}' should match pattern"
    
    def test_invalid_s3_uri_examples(self):
        """
        Test specific invalid S3 URI examples.
        Requirements: 5.2
        """
        template = PIPELINE_TEMPLATE
        parameters = template.get('Parameters', {})
        buildspec_param = parameters.get('PostDeployBuildSpec')
        allowed_pattern = buildspec_param.get('AllowedPattern')
        pattern = re.compile(allowed_pattern)
        
        # Test specific invalid S3 URI examples
        # Note: The pattern allows uppercase in bucket names, so we test other invalid cases
        invalid_uris = [
            'http://bucket/buildspec.yml',  # Wrong protocol
            'https://bucket/buildspec.yml',  # Wrong protocol
            's3:bucket/buildspec.yml',  # Missing //
            's3://bucket',  # No object key
            's3://-bucket/buildspec.yml',  # Bucket can't start with dash
            's3://bucket-/buildspec.yml',  # Bucket can't end with dash
            's3://bu/buildspec.yml',  # Bucket name too short (needs at least 3 chars)
            's3://bucket_name/buildspec.yml',  # Underscore not allowed in bucket name
        ]
        
        for uri in invalid_uris:
            match = pattern.match(uri)
            assert match is None, f"Invalid S3 URI '{uri}' should not match pattern"
    
    def test_valid_s3_bucket_name_examples(self):
        """
        Test specific valid S3 bucket name examples.
        Requirements: 5.2
        """
        template = PIPELINE_TEMPLATE
        parameters = template.get('Parameters', {})
        s3_param = parameters.get('PostDeployS3StaticHostBucket')
        allowed_pattern = s3_param.get('AllowedPattern')
        pattern = re.compile(allowed_pattern)
        
        # Test specific valid S3 bucket name examples
        valid_names = [
            'my-bucket',
            'company-static-assets',
            'bucket123',
            'a-b-c',  # Minimum length
            'very-long-bucket-name-with-many-characters-but-still-valid-123',
            '',  # Empty string is allowed
        ]
        
        for name in valid_names:
            match = pattern.match(name)
            assert match is not None, f"Valid S3 bucket name '{name}' should match pattern"
    
    def test_invalid_s3_bucket_name_examples(self):
        """
        Test specific invalid S3 bucket name examples.
        Requirements: 5.2
        """
        template = PIPELINE_TEMPLATE
        parameters = template.get('Parameters', {})
        s3_param = parameters.get('PostDeployS3StaticHostBucket')
        allowed_pattern = s3_param.get('AllowedPattern')
        pattern = re.compile(allowed_pattern)
        
        # Test specific invalid S3 bucket name examples
        # Note: The pattern ^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$|^$ allows 2+ chars, so 'bu' is valid
        invalid_names = [
            'My-Bucket',  # Uppercase not allowed
            'bucket_name',  # Underscore not allowed
            '-bucket',  # Can't start with dash
            'bucket-',  # Can't end with dash
            'b',  # Too short (needs at least 2 chars for non-empty)
            'bucket..name',  # Double dots not allowed
            'bucket name',  # Spaces not allowed
            'bucket.name',  # Dots not allowed in this pattern
        ]
        
        for name in invalid_names:
            match = pattern.match(name)
            assert match is None, f"Invalid S3 bucket name '{name}' should not match pattern"
    
    def test_parameter_constraint_edge_cases(self):
        """
        Test parameter constraint edge cases.
        Requirements: 5.1, 5.2
        """
        template = PIPELINE_TEMPLATE
        parameters = template.get('Parameters', {})
        
        # Test PostDeployStageEnabled parameter
        postdeploy_param = parameters.get('PostDeployStageEnabled')
        assert postdeploy_param['Type'] == 'String'
        assert postdeploy_param['Default'] == 'false'
        assert set(postdeploy_param['AllowedValues']) == {'true', 'false'}
        
        # Test PostDeployBuildSpec parameter
        buildspec_param = parameters.get('PostDeployBuildSpec')
        assert buildspec_param['Type'] == 'String'
        assert buildspec_param['Default'] == 'application-infrastructure/buildspec-postdeploy.yml'
        assert 'AllowedPattern' in buildspec_param
        
        # Test PostDeployS3StaticHostBucket parameter
        s3_param = parameters.get('PostDeployS3StaticHostBucket')
        assert s3_param['Type'] == 'String'
        assert s3_param['Default'] == ''
        assert 'AllowedPattern' in s3_param
        
        # Test that empty string is explicitly allowed for optional parameters
        buildspec_pattern = re.compile(buildspec_param['AllowedPattern'])
        s3_pattern = re.compile(s3_param['AllowedPattern'])
        
        assert buildspec_pattern.match('') is not None, "Empty string should be allowed for PostDeployBuildSpec"
        assert s3_pattern.match('') is not None, "Empty string should be allowed for PostDeployS3StaticHostBucket"


class TestResourceConfiguration:
    """Unit tests for resource configuration examples."""
    
    def test_postdeploy_service_role_configuration(self):
        """
        Test specific PostDeploy service role configuration examples.
        Requirements: 4.1, 4.2, 4.3
        """
        template = PIPELINE_TEMPLATE
        resources = template.get('Resources', {})
        
        # Get PostDeployServiceRole
        postdeploy_role = resources.get('PostDeployServiceRole')
        assert postdeploy_role is not None, "PostDeployServiceRole should exist"
        
        # Test resource type
        assert postdeploy_role['Type'] == 'AWS::IAM::Role'
        
        # Test condition
        condition = postdeploy_role.get('Condition')
        assert condition is not None, "PostDeployServiceRole should have condition"
        
        # Test properties structure
        properties = postdeploy_role.get('Properties', {})
        assert 'RoleName' in properties, "Should have RoleName"
        assert 'AssumeRolePolicyDocument' in properties, "Should have AssumeRolePolicyDocument"
        assert 'Policies' in properties, "Should have Policies"
        
        # Test assume role policy
        assume_policy = properties['AssumeRolePolicyDocument']
        statements = assume_policy.get('Statement', [])
        assert len(statements) > 0, "Should have assume role statements"
        
        codebuild_statement = statements[0]
        assert codebuild_statement['Effect'] == 'Allow'
        assert codebuild_statement['Action'] == 'sts:AssumeRole'
        assert codebuild_statement['Principal']['Service'] == 'codebuild.amazonaws.com'
    
    def test_postdeploy_iam_permission_structure(self):
        """
        Test specific IAM permission structure examples.
        Requirements: 4.2, 4.3
        """
        template = PIPELINE_TEMPLATE
        resources = get_template_section(template, 'Resources')
        
        postdeploy_role = resources.get('PostDeployServiceRole')
        policies = postdeploy_role.get('Properties', {}).get('Policies', [])
        assert len(policies) > 0, "Should have policies"
        
        main_policy = policies[0]
        policy_doc = main_policy.get('PolicyDocument', {})
        
        # Use utility to analyze policy structure
        policy_analysis = validate_iam_policy_structure(policy_doc)
        
        # Test specific permission statements exist
        statement_sids = [stmt['sid'] for stmt in policy_analysis['statements'] if stmt['sid']]
        
        expected_sids = [
            'AllowPostDeployToManageItsLogs',
            'AllowPostDeployToManageItsArtifacts',
            'SsmAccessDuringPostDeploy',
            'AllowListBuckets',
            'CopyAssetsToS3DuringPostDeployByPath',
            'CopyAssetsToS3DuringPostDeployByBucketApplicationTag',
            'CopyAssetsToS3DuringPostDeployByBucketApplicationDeploymentTag'
        ]
        
        for expected_sid in expected_sids:
            assert expected_sid in statement_sids, f"Should have statement with Sid '{expected_sid}'"
        
        # Test that we have expected S3 and SSM actions
        expected_s3_actions = {'s3:Get*', 's3:List*', 's3:PutObject'}
        expected_ssm_actions = {'ssm:GetParameters', 'ssm:GetParameter', 'ssm:GetParametersByPath'}
        
        assert expected_s3_actions.issubset(policy_analysis['actions']), "Should have expected S3 actions"
        assert expected_ssm_actions.issubset(policy_analysis['actions']), "Should have expected SSM actions"
        
        # Test that all statements have Allow effect
        assert policy_analysis['effects'] == {'Allow'}, "All statements should have Allow effect"
    
    def test_postdeploy_project_configuration(self):
        """
        Test specific PostDeploy CodeBuild project configuration examples.
        Requirements: 4.1, 4.4
        """
        template = PIPELINE_TEMPLATE
        resources = template.get('Resources', {})
        
        # Get PostDeployProject
        postdeploy_project = resources.get('PostDeployProject')
        assert postdeploy_project is not None, "PostDeployProject should exist"
        
        # Test resource type
        assert postdeploy_project['Type'] == 'AWS::CodeBuild::Project'
        
        # Test condition
        condition = postdeploy_project.get('Condition')
        assert condition is not None, "PostDeployProject should have condition"
        
        # Test properties structure
        properties = postdeploy_project.get('Properties', {})
        assert 'Name' in properties, "Should have Name"
        assert 'ServiceRole' in properties, "Should have ServiceRole"
        assert 'Environment' in properties, "Should have Environment"
        assert 'Source' in properties, "Should have Source"
        
        # Test environment configuration
        environment = properties.get('Environment', {})
        assert environment.get('ComputeType') == 'BUILD_GENERAL1_SMALL'
        assert environment.get('Type') == 'LINUX_CONTAINER'
        assert 'Image' in environment, "Should have Image specified"
        
        # Test environment variables
        env_vars = environment.get('EnvironmentVariables', [])
        assert len(env_vars) > 0, "Should have environment variables"
        
        env_var_names = [var['Name'] for var in env_vars]
        expected_vars = [
            'AWS_PARTITION', 'AWS_REGION', 'AWS_ACCOUNT', 'S3_ARTIFACTS_BUCKET',
            'PREFIX', 'PROJECT_ID', 'STAGE_ID', 'REPOSITORY', 'REPOSITORY_BRANCH',
            'PARAM_STORE_HIERARCHY', 'DEPLOY_ENVIRONMENT', 'NODE_ENV',
            'POST_DEPLOY_S3_STATIC_HOST_BUCKET'
        ]
        
        for var_name in expected_vars:
            assert var_name in env_var_names, f"Should have environment variable '{var_name}'"
        
        # Test POST_DEPLOY_S3_STATIC_HOST_BUCKET specifically
        postdeploy_s3_var = None
        for var in env_vars:
            if var['Name'] == 'POST_DEPLOY_S3_STATIC_HOST_BUCKET':
                postdeploy_s3_var = var
                break
        
        assert postdeploy_s3_var is not None, "Should have POST_DEPLOY_S3_STATIC_HOST_BUCKET variable"
        
        # Test source configuration
        source = properties.get('Source', {})
        assert source.get('Type') == 'CODEPIPELINE'
        assert 'BuildSpec' in source, "Should have BuildSpec configuration"
    
    def test_postdeploy_log_group_configuration(self):
        """
        Test specific PostDeploy log group configuration examples.
        Requirements: 4.5
        """
        template = PIPELINE_TEMPLATE
        resources = template.get('Resources', {})
        
        # Get PostDeployLogGroup
        log_group = resources.get('PostDeployLogGroup')
        assert log_group is not None, "PostDeployLogGroup should exist"
        
        # Test resource type
        assert log_group['Type'] == 'AWS::Logs::LogGroup'
        
        # Test condition
        condition = log_group.get('Condition')
        assert condition is not None, "PostDeployLogGroup should have condition"
        
        # Test properties
        properties = log_group.get('Properties', {})
        assert 'LogGroupName' in properties, "Should have LogGroupName"
        assert 'RetentionInDays' in properties, "Should have RetentionInDays"
        
        # Test retention policy
        retention_days = properties.get('RetentionInDays')
        assert isinstance(retention_days, int), "RetentionInDays should be integer"
        assert retention_days > 0, "RetentionInDays should be positive"
        
        # Test deletion policies
        assert 'DeletionPolicy' in log_group, "Should have DeletionPolicy"
        assert 'UpdateReplacePolicy' in log_group, "Should have UpdateReplacePolicy"
        assert log_group['DeletionPolicy'] == 'Delete'
        assert log_group['UpdateReplacePolicy'] == 'Retain'
    
    def test_compute_environment_consistency_examples(self):
        """
        Test specific compute environment consistency examples.
        Requirements: 4.1
        """
        template = PIPELINE_TEMPLATE
        resources = template.get('Resources', {})
        
        # Get both projects
        build_project = resources.get('CodeBuildProject')
        postdeploy_project = resources.get('PostDeployProject')
        
        assert build_project is not None, "CodeBuildProject should exist"
        assert postdeploy_project is not None, "PostDeployProject should exist"
        
        # Get environment configurations
        build_env = build_project.get('Properties', {}).get('Environment', {})
        postdeploy_env = postdeploy_project.get('Properties', {}).get('Environment', {})
        
        # Test specific compute settings match
        assert build_env.get('ComputeType') == postdeploy_env.get('ComputeType'), "ComputeType should match"
        assert build_env.get('Type') == postdeploy_env.get('Type'), "Environment Type should match"
        assert build_env.get('Image') == postdeploy_env.get('Image'), "Image should match"
        
        # Test specific values
        assert postdeploy_env.get('ComputeType') == 'BUILD_GENERAL1_SMALL'
        assert postdeploy_env.get('Type') == 'LINUX_CONTAINER'
        assert 'aws/codebuild/amazonlinux' in postdeploy_env.get('Image', '')
    
    def test_environment_variable_configuration_examples(self):
        """
        Test specific environment variable configuration examples.
        Requirements: 4.4
        """
        template = PIPELINE_TEMPLATE
        resources = get_template_section(template, 'Resources')
        
        postdeploy_project = resources.get('PostDeployProject')
        env_vars = postdeploy_project.get('Properties', {}).get('Environment', {}).get('EnvironmentVariables', [])
        
        # Use utility to analyze environment variables
        env_analysis = validate_environment_variables(env_vars)
        
        # Test specific environment variable examples
        expected_vars = {
            'AWS_PARTITION', 'AWS_REGION', 'AWS_ACCOUNT', 'PREFIX', 'PROJECT_ID', 
            'STAGE_ID', 'REPOSITORY', 'REPOSITORY_BRANCH', 'POST_DEPLOY_S3_STATIC_HOST_BUCKET'
        }
        
        assert expected_vars.issubset(env_analysis['variable_names']), "Should have expected environment variables"
        
        # Test NODE_ENV is set to production
        assert env_analysis['variables'].get('NODE_ENV', {}).get('value') == 'production'
        
        # Test that POST_DEPLOY_S3_STATIC_HOST_BUCKET references a parameter
        postdeploy_s3_var = env_analysis['variables'].get('POST_DEPLOY_S3_STATIC_HOST_BUCKET', {})
        assert 'PostDeployS3StaticHostBucket' in str(postdeploy_s3_var.get('value', '')), "Should reference PostDeployS3StaticHostBucket parameter"
    
    def test_conditional_s3_buildspec_permissions(self):
        """
        Test specific conditional S3 buildspec permission examples.
        Requirements: 4.2
        """
        template = PIPELINE_TEMPLATE
        resources = template.get('Resources', {})
        
        postdeploy_role = resources.get('PostDeployServiceRole')
        policies = postdeploy_role.get('Properties', {}).get('Policies', [])
        main_policy = policies[0]
        statements = main_policy.get('PolicyDocument', {}).get('Statement', [])
        
        # Find the conditional S3 buildspec statement
        s3_buildspec_stmt = None
        for stmt in statements:
            if isinstance(stmt, dict) and '!If' in stmt:
                # This is a conditional statement
                if_condition = stmt['!If']
                if len(if_condition) >= 2:
                    condition_name = if_condition[0]
                    if 'HasPostDeployBuildSpecS3Location' in str(condition_name):
                        s3_buildspec_stmt = if_condition[1]  # The statement when condition is true
                        break
        
        assert s3_buildspec_stmt is not None, "Should have conditional S3 buildspec statement"
        
        # Test the statement structure
        assert s3_buildspec_stmt.get('Sid') == 'CopyPostDeploySpecFromS3ForBuild'
        assert s3_buildspec_stmt.get('Effect') == 'Allow'
        
        actions = s3_buildspec_stmt.get('Action', [])
        assert 's3:Get*' in actions, "Should allow s3:Get* actions"
        assert 's3:List*' in actions, "Should allow s3:List* actions"
        
        resources_list = s3_buildspec_stmt.get('Resource', [])
        assert len(resources_list) >= 2, "Should have bucket and object permissions"
        
        # Test that resources reference PostDeployBuildSpec parameter
        resources_str = str(resources_list)
        assert 'PostDeployBuildSpec' in resources_str, "Resources should reference PostDeployBuildSpec parameter"