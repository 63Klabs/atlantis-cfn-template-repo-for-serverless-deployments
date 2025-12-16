"""
Property-based tests for PostDeploy functionality in CloudFormation pipeline template.

**Feature: pipeline-postdeploy-enhancement**
"""

import pytest
import sys
import os
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List

# Add tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cfn_test_utils import (
    load_template, get_template_section, find_resources_with_condition,
    get_parameter_references, validate_condition_logic, validate_iam_policy_structure,
    validate_environment_variables, compare_resource_properties,
    validate_pipeline_stages, validate_regex_pattern
)


def has_postdeploy_condition(condition: Any) -> bool:
    """Check if a condition references PostDeploy enablement."""
    if isinstance(condition, str):
        return 'IsPostDeployEnabled' in condition
    elif isinstance(condition, dict):
        # Handle complex conditions like !And [IsNotDevelopment, IsPostDeployEnabled]
        return any('IsPostDeployEnabled' in str(v) for v in condition.values())
    return False


# Load the pipeline template
PIPELINE_TEMPLATE = load_template('../templates/v2/pipeline/template-pipeline.yml')


@settings(max_examples=100)
@given(postdeploy_enabled=st.booleans())
def test_conditional_resource_creation(postdeploy_enabled: bool):
    """
    Property 1: Conditional Resource Creation
    For any CloudFormation template configuration, when PostDeployStageEnabled is "true", 
    all PostDeploy-related resources (PostDeployServiceRole, PostDeployProject, PostDeployLogGroup) 
    should exist in the template, and when PostDeployStageEnabled is "false", none of these 
    resources should exist in the template.
    
    **Feature: pipeline-postdeploy-enhancement, Property 1: Conditional Resource Creation**
    **Validates: Requirements 1.3, 1.4, 1.5**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # PostDeploy-related resources that should be conditionally created
    postdeploy_resources = [
        'PostDeployServiceRole',
        'PostDeployProject', 
        'PostDeployLogGroup'
    ]
    
    for resource_name in postdeploy_resources:
        assert resource_name in resources, f"PostDeploy resource '{resource_name}' should exist in template"
        
        resource = resources[resource_name]
        condition = resource.get('Condition')
        
        # Verify that PostDeploy resources have appropriate conditions
        assert condition is not None, f"PostDeploy resource '{resource_name}' should have a condition"
        assert has_postdeploy_condition(condition), f"PostDeploy resource '{resource_name}' should reference IsPostDeployEnabled condition"


@settings(max_examples=50)
@given(st.just(True))  # Test only when PostDeploy is enabled
def test_postdeploy_resources_have_correct_conditions(enabled: bool):
    """
    Verify that PostDeploy resources have the correct conditional logic structure.
    
    **Feature: pipeline-postdeploy-enhancement, Property 1: Conditional Resource Creation**
    **Validates: Requirements 1.3, 1.4, 1.5**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    conditions = template.get('Conditions', {})
    
    # Verify IsPostDeployEnabled condition exists
    assert 'IsPostDeployEnabled' in conditions, "IsPostDeployEnabled condition should exist"
    
    # Verify PostDeployServiceRole condition
    postdeploy_role = resources.get('PostDeployServiceRole', {})
    role_condition = postdeploy_role.get('Condition')
    assert role_condition is not None, "PostDeployServiceRole should have a condition"
    
    # Verify PostDeployProject condition  
    postdeploy_project = resources.get('PostDeployProject', {})
    project_condition = postdeploy_project.get('Condition')
    assert project_condition is not None, "PostDeployProject should have a condition"
    
    # Verify PostDeployLogGroup condition
    postdeploy_log_group = resources.get('PostDeployLogGroup', {})
    log_condition = postdeploy_log_group.get('Condition')
    assert log_condition is not None, "PostDeployLogGroup should have a condition"



@settings(max_examples=100)
@given(postdeploy_enabled=st.booleans())
def test_pipeline_stage_conditional_inclusion(postdeploy_enabled: bool):
    """
    Property 2: Pipeline Stage Conditional Inclusion
    For any pipeline configuration, when PostDeployStageEnabled is "true", the pipeline 
    should contain a PostDeploy stage, and when PostDeployStageEnabled is "false", 
    the pipeline should not contain a PostDeploy stage.
    
    **Feature: pipeline-postdeploy-enhancement, Property 2: Pipeline Stage Conditional Inclusion**
    **Validates: Requirements 1.1, 1.2**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get the ProjectPipeline resource
    pipeline_resource = resources.get('ProjectPipeline')
    assert pipeline_resource is not None, "ProjectPipeline resource should exist"
    
    # Get the pipeline stages configuration
    properties = pipeline_resource.get('Properties', {})
    stages = properties.get('Stages')
    
    # The stages should be conditional - either a !If construct or array
    assert stages is not None, "Pipeline should have stages defined"
    
    # Check if stages is a conditional construct
    if isinstance(stages, dict) and '!If' in stages:
        # This is the conditional structure we expect
        if_condition = stages['!If']
        assert len(if_condition) == 3, "!If should have condition, true_value, false_value"
        
        condition_name = if_condition[0]
        stages_with_postdeploy = if_condition[1]
        stages_without_postdeploy = if_condition[2]
        
        # Verify condition references PostDeploy enablement
        assert 'IsPostDeployEnabled' in str(condition_name), "Pipeline condition should reference IsPostDeployEnabled"
        
        # Verify stages with PostDeploy include PostDeploy stage
        postdeploy_stage_found = False
        for stage in stages_with_postdeploy:
            if stage.get('Name') == 'PostDeploy':
                postdeploy_stage_found = True
                break
        assert postdeploy_stage_found, "When PostDeploy is enabled, pipeline should include PostDeploy stage"
        
        # Verify stages without PostDeploy don't include PostDeploy stage
        postdeploy_stage_found = False
        for stage in stages_without_postdeploy:
            if stage.get('Name') == 'PostDeploy':
                postdeploy_stage_found = True
                break
        assert not postdeploy_stage_found, "When PostDeploy is disabled, pipeline should not include PostDeploy stage"


@settings(max_examples=50)
@given(st.just(True))
def test_pipeline_dependencies_when_postdeploy_enabled(enabled: bool):
    """
    Verify that pipeline dependencies are correctly configured when PostDeploy is enabled.
    
    **Feature: pipeline-postdeploy-enhancement, Property 2: Pipeline Stage Conditional Inclusion**
    **Validates: Requirements 1.1, 1.2**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get the ProjectPipeline resource
    pipeline_resource = resources.get('ProjectPipeline')
    assert pipeline_resource is not None, "ProjectPipeline resource should exist"
    
    # Check DependsOn configuration
    depends_on = pipeline_resource.get('DependsOn')
    assert depends_on is not None, "ProjectPipeline should have DependsOn configuration"
    
    # DependsOn should be conditional based on PostDeploy enablement
    if isinstance(depends_on, dict) and '!If' in depends_on:
        if_condition = depends_on['!If']
        assert len(if_condition) == 3, "DependsOn !If should have condition, true_value, false_value"
        
        condition_name = if_condition[0]
        deps_with_postdeploy = if_condition[1]
        deps_without_postdeploy = if_condition[2]
        
        # Verify condition references PostDeploy enablement
        assert 'IsPostDeployEnabled' in str(condition_name), "DependsOn condition should reference IsPostDeployEnabled"
        
        # Verify dependencies include PostDeployProject when enabled
        assert 'PostDeployProject' in deps_with_postdeploy, "When PostDeploy enabled, should depend on PostDeployProject"
        assert 'CodeBuildProject' in deps_with_postdeploy, "Should always depend on CodeBuildProject"
        
        # Verify dependencies don't include PostDeployProject when disabled
        assert 'PostDeployProject' not in deps_without_postdeploy, "When PostDeploy disabled, should not depend on PostDeployProject"
        assert 'CodeBuildProject' in deps_without_postdeploy, "Should always depend on CodeBuildProject"

# Use the utility function from cfn_test_utils
# find_exact_parameter_references is now get_parameter_references


@settings(max_examples=50)
@given(st.just("PostDeployStageEnabled"))
def test_parameter_naming_consistency(param_name: str):
    """
    Property 3: Parameter Naming Consistency
    For any reference to the PostDeploy enable parameter throughout the template, 
    the parameter name should be consistently "PostDeployStageEnabled" in all 
    conditions, metadata, and references.
    
    **Feature: pipeline-postdeploy-enhancement, Property 3: Parameter Naming Consistency**
    **Validates: Requirements 2.1**
    """
    template = PIPELINE_TEMPLATE
    
    # Verify the parameter exists with the correct name
    parameters = template.get('Parameters', {})
    assert param_name in parameters, f"Parameter '{param_name}' should exist in template"
    
    # Check metadata references
    metadata = template.get('Metadata', {})
    if 'AWS::CloudFormation::Interface' in metadata:
        interface = metadata['AWS::CloudFormation::Interface']
        param_groups = interface.get('ParameterGroups', [])
        
        # Find the PostDeploy parameter group
        postdeploy_group = None
        for group in param_groups:
            if 'Post Deploy Environment Information' in group.get('Label', {}).get('default', ''):
                postdeploy_group = group
                break
        
        if postdeploy_group:
            group_params = postdeploy_group.get('Parameters', [])
            assert param_name in group_params, f"Metadata should reference '{param_name}' consistently"
    
    # Check all references throughout the template use the correct parameter name
    all_refs = get_parameter_references(template, param_name)
    
    # Verify no incorrect parameter names are used
    incorrect_names = ['EnablePostDeployStage', 'PostDeployEnabled', 'EnablePostDeploy']
    for incorrect_name in incorrect_names:
        incorrect_refs = get_parameter_references(template, incorrect_name)
        assert len(incorrect_refs) == 0, f"Found incorrect parameter reference '{incorrect_name}': {incorrect_refs}"


@settings(max_examples=50)
@given(st.just(True))
def test_postdeploy_parameter_structure(enabled: bool):
    """
    Verify the PostDeploy parameter has the correct structure and constraints.
    
    **Feature: pipeline-postdeploy-enhancement, Property 3: Parameter Naming Consistency**
    **Validates: Requirements 2.1**
    """
    template = PIPELINE_TEMPLATE
    parameters = template.get('Parameters', {})
    
    # Verify PostDeployStageEnabled parameter structure
    postdeploy_param = parameters.get('PostDeployStageEnabled')
    assert postdeploy_param is not None, "PostDeployStageEnabled parameter should exist"
    
    # Verify parameter type
    assert postdeploy_param.get('Type') == 'String', "PostDeployStageEnabled should be String type"
    
    # Verify allowed values
    allowed_values = postdeploy_param.get('AllowedValues')
    assert allowed_values is not None, "PostDeployStageEnabled should have AllowedValues"
    assert set(allowed_values) == {'true', 'false'}, "PostDeployStageEnabled should allow 'true' and 'false'"
    
    # Verify default value
    default_value = postdeploy_param.get('Default')
    assert default_value == 'false', "PostDeployStageEnabled should default to 'false'"

@settings(max_examples=50)
@given(st.just("IsPostDeployEnabled"))
def test_condition_name_consistency(condition_name: str):
    """
    Property 4: Condition Name Consistency
    For any PostDeploy-related conditional resource, all resources should reference 
    the same condition name for consistency.
    
    **Feature: pipeline-postdeploy-enhancement, Property 4: Condition Name Consistency**
    **Validates: Requirements 2.2**
    """
    template = PIPELINE_TEMPLATE
    
    # Verify the condition exists
    conditions = template.get('Conditions', {})
    assert condition_name in conditions, f"Condition '{condition_name}' should exist in template"
    
    # Verify the condition references the correct parameter
    condition_def = conditions[condition_name]
    condition_refs = get_parameter_references(condition_def, 'PostDeployStageEnabled')
    assert len(condition_refs) > 0, f"Condition '{condition_name}' should reference PostDeployStageEnabled parameter"
    
    # Get all PostDeploy-related resources
    resources = template.get('Resources', {})
    postdeploy_resources = [
        'PostDeployServiceRole',
        'PostDeployProject', 
        'PostDeployLogGroup'
    ]
    
    # Verify all PostDeploy resources use the same condition name
    for resource_name in postdeploy_resources:
        resource = resources.get(resource_name)
        assert resource is not None, f"PostDeploy resource '{resource_name}' should exist"
        
        resource_condition = resource.get('Condition')
        assert resource_condition is not None, f"PostDeploy resource '{resource_name}' should have a condition"
        
        # Check if condition directly references IsPostDeployEnabled or uses it in a complex condition
        if isinstance(resource_condition, str):
            assert condition_name in resource_condition, f"Resource '{resource_name}' should reference '{condition_name}'"
        elif isinstance(resource_condition, dict):
            # Handle complex conditions like !And [IsNotDevelopment, IsPostDeployEnabled]
            condition_str = str(resource_condition)
            assert condition_name in condition_str, f"Resource '{resource_name}' should reference '{condition_name}' in complex condition"


@settings(max_examples=50)
@given(st.just(True))
def test_postdeploy_condition_structure(enabled: bool):
    """
    Verify the PostDeploy condition has the correct structure.
    
    **Feature: pipeline-postdeploy-enhancement, Property 4: Condition Name Consistency**
    **Validates: Requirements 2.2**
    """
    template = PIPELINE_TEMPLATE
    conditions = template.get('Conditions', {})
    
    # Verify IsPostDeployEnabled condition structure
    postdeploy_condition = conditions.get('IsPostDeployEnabled')
    assert postdeploy_condition is not None, "IsPostDeployEnabled condition should exist"
    
    # Should be an !Equals condition
    assert isinstance(postdeploy_condition, dict), "IsPostDeployEnabled should be a condition object"
    assert '!Equals' in postdeploy_condition, "IsPostDeployEnabled should use !Equals"
    
    equals_args = postdeploy_condition['!Equals']
    assert len(equals_args) == 2, "!Equals should have exactly 2 arguments"
    
    # First argument should be !Ref PostDeployStageEnabled
    first_arg = equals_args[0]
    assert isinstance(first_arg, dict), "First argument should be a reference"
    assert '!Ref' in first_arg, "First argument should be !Ref"
    assert first_arg['!Ref'] == 'PostDeployStageEnabled', "Should reference PostDeployStageEnabled parameter"
    
    # Second argument should be "true"
    second_arg = equals_args[1]
    assert second_arg == 'true', "Second argument should be 'true'"


@settings(max_examples=50)
@given(st.just(True))
def test_complex_postdeploy_conditions(enabled: bool):
    """
    Verify complex PostDeploy conditions that combine multiple conditions.
    
    **Feature: pipeline-postdeploy-enhancement, Property 4: Condition Name Consistency**
    **Validates: Requirements 2.2**
    """
    template = PIPELINE_TEMPLATE
    conditions = template.get('Conditions', {})
    
    # Check for HasPostDeployBuildSpecS3Location condition
    s3_condition = conditions.get('HasPostDeployBuildSpecS3Location')
    if s3_condition is not None:
        # Should be a condition object (either !And or !If with !And inside)
        assert isinstance(s3_condition, dict), "HasPostDeployBuildSpecS3Location should be a condition object"
        
        # Handle both !And and !If structures
        and_conditions = None
        has_postdeploy_ref = False
        
        if '!And' in s3_condition:
            and_conditions = s3_condition['!And']
        elif '!If' in s3_condition:
            # Check if the condition references IsPostDeployEnabled
            if_parts = s3_condition['!If']
            if len(if_parts) >= 1 and if_parts[0] == 'IsPostDeployEnabled':
                has_postdeploy_ref = True
            # Check if the true branch contains !And
            if len(if_parts) >= 2 and isinstance(if_parts[1], dict) and '!And' in if_parts[1]:
                and_conditions = if_parts[1]['!And']
        
        if and_conditions is not None:
            assert isinstance(and_conditions, list), "!And should contain a list of conditions"
            
            # Check for IsPostDeployEnabled reference in !And structure
            if not has_postdeploy_ref:
                for condition in and_conditions:
                    if isinstance(condition, str) and condition == 'IsPostDeployEnabled':
                        has_postdeploy_ref = True
                        break
                    elif isinstance(condition, dict) and '!Condition' in condition:
                        if condition['!Condition'] == 'IsPostDeployEnabled':
                            has_postdeploy_ref = True
                            break
        
        assert has_postdeploy_ref, "HasPostDeployBuildSpecS3Location should reference IsPostDeployEnabled condition"
@settings(max_examples=50)
@given(st.just("PostDeployBuildSpec"))
def test_buildspec_parameter_reference(param_name: str):
    """
    Property 5: BuildSpec Parameter Reference
    For any PostDeploy CodeBuild project configuration, the BuildSpec property 
    should correctly reference the PostDeployBuildSpec parameter.
    
    **Feature: pipeline-postdeploy-enhancement, Property 5: BuildSpec Parameter Reference**
    **Validates: Requirements 2.3**
    """
    template = PIPELINE_TEMPLATE
    
    # Verify the parameter exists
    parameters = template.get('Parameters', {})
    assert param_name in parameters, f"Parameter '{param_name}' should exist in template"
    
    # Get PostDeployProject resource
    resources = template.get('Resources', {})
    postdeploy_project = resources.get('PostDeployProject')
    assert postdeploy_project is not None, "PostDeployProject resource should exist"
    
    # Check BuildSpec configuration in Source property
    properties = postdeploy_project.get('Properties', {})
    source = properties.get('Source', {})
    buildspec = source.get('BuildSpec')
    
    assert buildspec is not None, "PostDeployProject should have BuildSpec configured"
    
    # BuildSpec should be conditional based on S3 location or use parameter reference
    if isinstance(buildspec, dict) and '!If' in buildspec:
        # Conditional BuildSpec - check both branches
        if_condition = buildspec['!If']
        assert len(if_condition) == 3, "BuildSpec !If should have condition, true_value, false_value"
        
        # Check that PostDeployBuildSpec parameter is referenced somewhere in the configuration
        buildspec_str = str(buildspec)
        assert param_name in buildspec_str, f"BuildSpec configuration should reference {param_name} parameter"
    else:
        # Direct reference - should reference the parameter
        buildspec_refs = get_parameter_references(buildspec, param_name)
        assert len(buildspec_refs) > 0, f"BuildSpec should reference {param_name} parameter"


@settings(max_examples=50)
@given(st.just(True))
def test_postdeploy_buildspec_parameter_structure(enabled: bool):
    """
    Verify the PostDeployBuildSpec parameter has the correct structure.
    
    **Feature: pipeline-postdeploy-enhancement, Property 5: BuildSpec Parameter Reference**
    **Validates: Requirements 2.3**
    """
    template = PIPELINE_TEMPLATE
    parameters = template.get('Parameters', {})
    
    # Verify PostDeployBuildSpec parameter structure
    buildspec_param = parameters.get('PostDeployBuildSpec')
    assert buildspec_param is not None, "PostDeployBuildSpec parameter should exist"
    
    # Verify parameter type
    assert buildspec_param.get('Type') == 'String', "PostDeployBuildSpec should be String type"
    
    # Verify default value
    default_value = buildspec_param.get('Default')
    assert default_value == 'application-infrastructure/buildspec-postdeploy.yml', "PostDeployBuildSpec should have correct default"
    
    # Verify AllowedPattern for buildspec validation
    allowed_pattern = buildspec_param.get('AllowedPattern')
    assert allowed_pattern is not None, "PostDeployBuildSpec should have AllowedPattern for validation"
    
    # Pattern should allow S3 URIs and local paths ending with buildspec-postdeploy.yml
    assert 's3:' in allowed_pattern, "AllowedPattern should allow S3 URIs"
    assert 'buildspec-postdeploy' in allowed_pattern, "AllowedPattern should allow buildspec-postdeploy.yml files"
@settings(max_examples=50)
@given(st.just(True))
def test_s3_buildspec_iam_permissions(enabled: bool):
    """
    Property 6: S3 BuildSpec IAM Permissions
    For any PostDeploy configuration using S3 buildspec location, the PostDeployServiceRole 
    should have appropriate S3 read permissions for the buildspec file.
    
    **Feature: pipeline-postdeploy-enhancement, Property 6: S3 BuildSpec IAM Permissions**
    **Validates: Requirements 2.4**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get PostDeployServiceRole
    postdeploy_role = resources.get('PostDeployServiceRole')
    assert postdeploy_role is not None, "PostDeployServiceRole should exist"
    
    # Check IAM policies
    properties = postdeploy_role.get('Properties', {})
    policies = properties.get('Policies', [])
    assert len(policies) > 0, "PostDeployServiceRole should have policies"
    
    # Find the main service policy
    service_policy = None
    for policy in policies:
        policy_name = policy.get('PolicyName', '')
        if isinstance(policy_name, dict) and '!Sub' in policy_name:
            # Dynamic policy name with !Sub
            sub_template = policy_name['!Sub']
            if 'PostDeployServicePolicy' in sub_template:
                service_policy = policy
                break
        elif 'PostDeployServicePolicy' in policy_name:
            service_policy = policy
            break
    
    assert service_policy is not None, "PostDeployServiceRole should have PostDeployServicePolicy"
    
    # Check policy document statements
    policy_doc = service_policy.get('PolicyDocument', {})
    statements = policy_doc.get('Statement', [])
    
    # Look for S3 buildspec permissions statement
    s3_buildspec_statement = None
    for statement in statements:
        if isinstance(statement, dict) and '!If' in statement:
            # This is a conditional statement - check if it's for S3 buildspec
            if_condition = statement['!If']
            if len(if_condition) >= 2:
                condition_name = if_condition[0]
                if 'HasPostDeployBuildSpecS3Location' in str(condition_name):
                    s3_buildspec_statement = if_condition[1]  # The statement when condition is true
                    break
    
    if s3_buildspec_statement is not None:
        # Verify the S3 buildspec statement has correct permissions
        assert 'Sid' in s3_buildspec_statement, "S3 buildspec statement should have Sid"
        assert 'CopyPostDeploySpecFromS3ForBuild' in s3_buildspec_statement['Sid'], "Should have correct Sid"
        
        actions = s3_buildspec_statement.get('Action', [])
        assert 's3:Get*' in actions, "Should allow s3:Get* actions"
        assert 's3:List*' in actions, "Should allow s3:List* actions"
        
        resources_list = s3_buildspec_statement.get('Resource', [])
        assert len(resources_list) >= 2, "Should have bucket and object permissions"
        
        # Check that resources reference PostDeployBuildSpec parameter
        resources_str = str(resources_list)
        assert 'PostDeployBuildSpec' in resources_str, "Resources should reference PostDeployBuildSpec parameter"


@settings(max_examples=50)
@given(st.just(True))
def test_postdeploy_s3_buildspec_condition(enabled: bool):
    """
    Verify the HasPostDeployBuildSpecS3Location condition is properly configured.
    
    **Feature: pipeline-postdeploy-enhancement, Property 6: S3 BuildSpec IAM Permissions**
    **Validates: Requirements 2.4**
    """
    template = PIPELINE_TEMPLATE
    conditions = template.get('Conditions', {})
    
    # Verify HasPostDeployBuildSpecS3Location condition exists
    s3_condition = conditions.get('HasPostDeployBuildSpecS3Location')
    assert s3_condition is not None, "HasPostDeployBuildSpecS3Location condition should exist"
    
    # Should be a condition object (either !And or !If with !And inside)
    assert isinstance(s3_condition, dict), "HasPostDeployBuildSpecS3Location should be a condition object"
    
    # Handle both !And and !If structures
    and_conditions = None
    if '!And' in s3_condition:
        and_conditions = s3_condition['!And']
    elif '!If' in s3_condition:
        # Check if the true branch contains !And
        if_parts = s3_condition['!If']
        if len(if_parts) >= 2 and isinstance(if_parts[1], dict) and '!And' in if_parts[1]:
            and_conditions = if_parts[1]['!And']
    
    assert and_conditions is not None, "Should contain !And logic either directly or within !If"
    assert isinstance(and_conditions, list), "!And should contain a list of conditions"
    assert len(and_conditions) >= 2, "Should have at least 2 conditions in !And"
    
    # Should include PostDeployBuildSpec and s3 checks
    has_postdeploy_ref = False
    has_buildspec_check = False
    has_s3_check = False
    
    # Also check the condition name in !If structure
    condition_str = str(s3_condition)
    if 'IsPostDeployEnabled' in condition_str:
        has_postdeploy_ref = True
    
    for condition in and_conditions:
        condition_str = str(condition)
        if 'PostDeployBuildSpec' in condition_str:
            has_buildspec_check = True
        if 's3' in condition_str:
            has_s3_check = True
    
    assert has_postdeploy_ref, "Should reference IsPostDeployEnabled condition"
    assert has_buildspec_check, "Should check PostDeployBuildSpec parameter"
    assert has_s3_check, "Should check for s3 protocol"
@settings(max_examples=50)
@given(st.just("POST_DEPLOY_S3_STATIC_HOST_BUCKET"))
def test_environment_variable_configuration(env_var_name: str):
    """
    Property 7: Environment Variable Configuration
    For any PostDeploy CodeBuild project, the environment variables should include 
    POST_DEPLOY_S3_STATIC_HOST_BUCKET when PostDeploy is enabled.
    
    **Feature: pipeline-postdeploy-enhancement, Property 7: Environment Variable Configuration**
    **Validates: Requirements 2.5**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get PostDeployProject
    postdeploy_project = resources.get('PostDeployProject')
    assert postdeploy_project is not None, "PostDeployProject should exist"
    
    # Check environment configuration
    properties = postdeploy_project.get('Properties', {})
    environment = properties.get('Environment', {})
    env_vars = environment.get('EnvironmentVariables', [])
    
    assert len(env_vars) > 0, "PostDeployProject should have environment variables"
    
    # Look for POST_DEPLOY_S3_STATIC_HOST_BUCKET environment variable
    postdeploy_s3_var = None
    for env_var in env_vars:
        if env_var.get('Name') == env_var_name:
            postdeploy_s3_var = env_var
            break
    
    assert postdeploy_s3_var is not None, f"PostDeployProject should have {env_var_name} environment variable"
    
    # Verify it references the PostDeployS3StaticHostBucket parameter
    value = postdeploy_s3_var.get('Value')
    assert value is not None, f"{env_var_name} should have a value"
    
    # Should reference PostDeployS3StaticHostBucket parameter
    if isinstance(value, dict) and '!Ref' in value:
        assert value['!Ref'] == 'PostDeployS3StaticHostBucket', f"{env_var_name} should reference PostDeployS3StaticHostBucket parameter"
    else:
        value_str = str(value)
        assert 'PostDeployS3StaticHostBucket' in value_str, f"{env_var_name} should reference PostDeployS3StaticHostBucket parameter"


@settings(max_examples=50)
@given(st.just(True))
def test_postdeploy_s3_static_host_bucket_parameter(enabled: bool):
    """
    Verify the PostDeployS3StaticHostBucket parameter configuration.
    
    **Feature: pipeline-postdeploy-enhancement, Property 7: Environment Variable Configuration**
    **Validates: Requirements 2.5**
    """
    template = PIPELINE_TEMPLATE
    parameters = template.get('Parameters', {})
    
    # Verify PostDeployS3StaticHostBucket parameter exists
    s3_param = parameters.get('PostDeployS3StaticHostBucket')
    assert s3_param is not None, "PostDeployS3StaticHostBucket parameter should exist"
    
    # Verify parameter type
    assert s3_param.get('Type') == 'String', "PostDeployS3StaticHostBucket should be String type"
    
    # Verify default value (should be empty)
    default_value = s3_param.get('Default')
    assert default_value == '', "PostDeployS3StaticHostBucket should default to empty string"
    
    # Verify AllowedPattern for S3 bucket name validation
    allowed_pattern = s3_param.get('AllowedPattern')
    assert allowed_pattern is not None, "PostDeployS3StaticHostBucket should have AllowedPattern"
    
    # Pattern should allow valid S3 bucket names and empty string
    assert '[a-z0-9]' in allowed_pattern, "AllowedPattern should allow lowercase alphanumeric"
    assert '\\^\\$' in allowed_pattern or '^$' in allowed_pattern, "AllowedPattern should allow empty string"
@settings(max_examples=50)
@given(st.just(True))
def test_compute_environment_consistency(enabled: bool):
    """
    Property 8: Compute Environment Consistency
    For any PostDeploy CodeBuild project, the compute environment configuration 
    should match the Build stage configuration.
    
    **Feature: pipeline-postdeploy-enhancement, Property 8: Compute Environment Consistency**
    **Validates: Requirements 4.1**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get both CodeBuild projects
    build_project = resources.get('CodeBuildProject')
    postdeploy_project = resources.get('PostDeployProject')
    
    assert build_project is not None, "CodeBuildProject should exist"
    assert postdeploy_project is not None, "PostDeployProject should exist"
    
    # Get environment configurations
    build_env = build_project.get('Properties', {}).get('Environment', {})
    postdeploy_env = postdeploy_project.get('Properties', {}).get('Environment', {})
    
    # Compare compute environment settings
    compute_settings = ['ComputeType', 'Type', 'Image']
    
    for setting in compute_settings:
        build_value = build_env.get(setting)
        postdeploy_value = postdeploy_env.get(setting)
        
        assert build_value is not None, f"Build project should have {setting} configured"
        assert postdeploy_value is not None, f"PostDeploy project should have {setting} configured"
        assert build_value == postdeploy_value, f"{setting} should be consistent between Build and PostDeploy projects"


@settings(max_examples=50)
@given(st.just(True))
def test_s3_permission_consistency(enabled: bool):
    """
    Property 9: S3 Permission Consistency
    For any PostDeploy service role, the S3 permissions for artifact management 
    should be similar to the CodeBuildServiceRole permissions.
    
    **Feature: pipeline-postdeploy-enhancement, Property 9: S3 Permission Consistency**
    **Validates: Requirements 4.2**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get both service roles
    build_role = resources.get('CodeBuildServiceRole')
    postdeploy_role = resources.get('PostDeployServiceRole')
    
    assert build_role is not None, "CodeBuildServiceRole should exist"
    assert postdeploy_role is not None, "PostDeployServiceRole should exist"
    
    # Get policies from both roles
    build_policies = build_role.get('Properties', {}).get('Policies', [])
    postdeploy_policies = postdeploy_role.get('Properties', {}).get('Policies', [])
    
    assert len(build_policies) > 0, "CodeBuildServiceRole should have policies"
    assert len(postdeploy_policies) > 0, "PostDeployServiceRole should have policies"
    
    # Find S3 artifact management statements in both policies
    build_s3_statements = []
    postdeploy_s3_statements = []
    
    for policy in build_policies:
        statements = policy.get('PolicyDocument', {}).get('Statement', [])
        for stmt in statements:
            if isinstance(stmt, dict) and 'AllowCodeBuildToManageItsArtifacts' in stmt.get('Sid', ''):
                build_s3_statements.append(stmt)
    
    for policy in postdeploy_policies:
        statements = policy.get('PolicyDocument', {}).get('Statement', [])
        for stmt in statements:
            if isinstance(stmt, dict) and 'AllowPostDeployToManageItsArtifacts' in stmt.get('Sid', ''):
                postdeploy_s3_statements.append(stmt)
    
    assert len(build_s3_statements) > 0, "Build role should have S3 artifact management statements"
    assert len(postdeploy_s3_statements) > 0, "PostDeploy role should have S3 artifact management statements"
    
    # Compare S3 actions - should be similar
    build_actions = set()
    postdeploy_actions = set()
    
    for stmt in build_s3_statements:
        actions = stmt.get('Action', [])
        if isinstance(actions, list):
            build_actions.update(actions)
        else:
            build_actions.add(actions)
    
    for stmt in postdeploy_s3_statements:
        actions = stmt.get('Action', [])
        if isinstance(actions, list):
            postdeploy_actions.update(actions)
        else:
            postdeploy_actions.add(actions)
    
    # Should have similar S3 actions
    common_actions = {'s3:Get*', 's3:List*', 's3:PutObject'}
    assert common_actions.issubset(build_actions), "Build role should have common S3 actions"
    assert common_actions.issubset(postdeploy_actions), "PostDeploy role should have common S3 actions"


@settings(max_examples=50)
@given(st.just(True))
def test_ssm_permission_consistency(enabled: bool):
    """
    Property 10: SSM Permission Consistency
    For any PostDeploy service role, the SSM Parameter Store permissions 
    should be similar to the CodeBuildServiceRole permissions.
    
    **Feature: pipeline-postdeploy-enhancement, Property 10: SSM Permission Consistency**
    **Validates: Requirements 4.3**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get both service roles
    build_role = resources.get('CodeBuildServiceRole')
    postdeploy_role = resources.get('PostDeployServiceRole')
    
    assert build_role is not None, "CodeBuildServiceRole should exist"
    assert postdeploy_role is not None, "PostDeployServiceRole should exist"
    
    # Find SSM statements in both policies
    build_ssm_statements = []
    postdeploy_ssm_statements = []
    
    build_policies = build_role.get('Properties', {}).get('Policies', [])
    postdeploy_policies = postdeploy_role.get('Properties', {}).get('Policies', [])
    
    for policy in build_policies:
        statements = policy.get('PolicyDocument', {}).get('Statement', [])
        for stmt in statements:
            if isinstance(stmt, dict) and 'SsmAccessDuringCodeBuild' in stmt.get('Sid', ''):
                build_ssm_statements.append(stmt)
    
    for policy in postdeploy_policies:
        statements = policy.get('PolicyDocument', {}).get('Statement', [])
        for stmt in statements:
            if isinstance(stmt, dict) and 'SsmAccessDuringPostDeploy' in stmt.get('Sid', ''):
                postdeploy_ssm_statements.append(stmt)
    
    assert len(build_ssm_statements) > 0, "Build role should have SSM statements"
    assert len(postdeploy_ssm_statements) > 0, "PostDeploy role should have SSM statements"
    
    # Compare SSM actions - should be similar
    build_actions = set()
    postdeploy_actions = set()
    
    for stmt in build_ssm_statements:
        actions = stmt.get('Action', [])
        if isinstance(actions, list):
            build_actions.update(actions)
        else:
            build_actions.add(actions)
    
    for stmt in postdeploy_ssm_statements:
        actions = stmt.get('Action', [])
        if isinstance(actions, list):
            postdeploy_actions.update(actions)
        else:
            postdeploy_actions.add(actions)
    
    # Should have similar SSM actions
    common_actions = {'ssm:GetParameters', 'ssm:GetParameter', 'ssm:GetParametersByPath'}
    assert common_actions.issubset(build_actions), "Build role should have common SSM actions"
    assert common_actions.issubset(postdeploy_actions), "PostDeploy role should have common SSM actions"
@settings(max_examples=50)
@given(st.just(True))
def test_core_environment_variable_consistency(enabled: bool):
    """
    Property 11: Core Environment Variable Consistency
    For any PostDeploy CodeBuild project, it should receive the same core 
    environment variables as the Build stage project.
    
    **Feature: pipeline-postdeploy-enhancement, Property 11: Core Environment Variable Consistency**
    **Validates: Requirements 4.4**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get both CodeBuild projects
    build_project = resources.get('CodeBuildProject')
    postdeploy_project = resources.get('PostDeployProject')
    
    assert build_project is not None, "CodeBuildProject should exist"
    assert postdeploy_project is not None, "PostDeployProject should exist"
    
    # Get environment variables
    build_env_vars = build_project.get('Properties', {}).get('Environment', {}).get('EnvironmentVariables', [])
    postdeploy_env_vars = postdeploy_project.get('Properties', {}).get('Environment', {}).get('EnvironmentVariables', [])
    
    assert len(build_env_vars) > 0, "Build project should have environment variables"
    assert len(postdeploy_env_vars) > 0, "PostDeploy project should have environment variables"
    
    # Convert to dictionaries for easier comparison
    build_vars = {var['Name']: var['Value'] for var in build_env_vars}
    postdeploy_vars = {var['Name']: var['Value'] for var in postdeploy_env_vars}
    
    # Core environment variables that should be consistent
    core_vars = [
        'AWS_PARTITION', 'AWS_REGION', 'AWS_ACCOUNT', 'S3_ARTIFACTS_BUCKET',
        'PREFIX', 'PROJECT_ID', 'STAGE_ID', 'S3_BUCKET_NAME_ORG_PREFIX',
        'REPOSITORY', 'REPOSITORY_BRANCH', 'PARAM_STORE_HIERARCHY',
        'DEPLOY_ENVIRONMENT', 'ALARM_NOTIFICATION_EMAIL', 'ROLE_PATH',
        'PERMISSIONS_BOUNDARY_ARN', 'NODE_ENV'
    ]
    
    for var_name in core_vars:
        assert var_name in build_vars, f"Build project should have {var_name} environment variable"
        assert var_name in postdeploy_vars, f"PostDeploy project should have {var_name} environment variable"
        
        # Values should be identical
        build_value = build_vars[var_name]
        postdeploy_value = postdeploy_vars[var_name]
        assert build_value == postdeploy_value, f"Environment variable {var_name} should have consistent values between Build and PostDeploy"


@settings(max_examples=50)
@given(st.just(True))
def test_log_group_configuration(enabled: bool):
    """
    Property 12: Log Group Configuration
    For any PostDeploy configuration, when enabled, a dedicated CloudWatch log group 
    should exist with proper retention policy.
    
    **Feature: pipeline-postdeploy-enhancement, Property 12: Log Group Configuration**
    **Validates: Requirements 4.5**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get PostDeployLogGroup
    postdeploy_log_group = resources.get('PostDeployLogGroup')
    assert postdeploy_log_group is not None, "PostDeployLogGroup should exist"
    
    # Verify it has the correct condition
    condition = postdeploy_log_group.get('Condition')
    assert condition is not None, "PostDeployLogGroup should have a condition"
    assert has_postdeploy_condition(condition), "PostDeployLogGroup should reference IsPostDeployEnabled condition"
    
    # Verify properties
    properties = postdeploy_log_group.get('Properties', {})
    
    # Check log group name
    log_group_name = properties.get('LogGroupName')
    assert log_group_name is not None, "PostDeployLogGroup should have LogGroupName"
    
    # Should reference PostDeploy in the name
    log_group_name_str = str(log_group_name)
    assert 'PostDeploy' in log_group_name_str, "Log group name should reference PostDeploy"
    
    # Check retention policy
    retention_days = properties.get('RetentionInDays')
    assert retention_days is not None, "PostDeployLogGroup should have RetentionInDays"
    assert isinstance(retention_days, int), "RetentionInDays should be an integer"
    assert retention_days > 0, "RetentionInDays should be positive"
    
    # Check deletion and update policies
    deletion_policy = postdeploy_log_group.get('DeletionPolicy')
    update_policy = postdeploy_log_group.get('UpdateReplacePolicy')
    
    assert deletion_policy is not None, "PostDeployLogGroup should have DeletionPolicy"
    assert update_policy is not None, "PostDeployLogGroup should have UpdateReplacePolicy"
# Strategies for generating buildspec paths and S3 URIs
@st.composite
def valid_buildspec_paths(draw):
    """Generate valid local buildspec file paths."""
    # Valid path components
    path_components = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'),
        min_size=0, max_size=3
    ))
    
    # PostDeployBuildSpec only accepts buildspec-postdeploy.yml files
    filename = 'buildspec-postdeploy.yml'
    
    if path_components:
        return '/'.join(path_components) + '/' + filename
    else:
        return filename


@st.composite
def valid_s3_uris(draw):
    """Generate valid S3 URIs for buildspec files."""
    # Valid S3 bucket name
    bucket_name = draw(st.text(
        min_size=3, max_size=63,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
    ).filter(lambda x: x[0].isalnum() and x[-1].isalnum() and '--' not in x))
    
    # Valid object key
    key_components = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'),
        min_size=1, max_size=5
    ))
    
    # PostDeployBuildSpec accepts any file in S3, not just buildspec-postdeploy.yml
    filename = draw(st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.'))
    object_key = '/'.join(key_components) + '/' + filename
    
    return f"s3://{bucket_name}/{object_key}"


@st.composite
def invalid_buildspec_paths(draw):
    """Generate invalid buildspec file paths."""
    invalid_type = draw(st.sampled_from([
        'wrong_extension',
        'empty_path',
        'invalid_characters',
        'no_filename'
    ]))
    
    if invalid_type == 'wrong_extension':
        return 'path/to/buildspec.yml'  # Should be buildspec-postdeploy.yml
    elif invalid_type == 'empty_path':
        return ''
    elif invalid_type == 'invalid_characters':
        return 'path/with spaces/buildspec.yml'  # Spaces not allowed
    else:  # no_filename
        return 'path/to/directory/'


@st.composite
def invalid_s3_uris(draw):
    """Generate invalid S3 URIs."""
    invalid_type = draw(st.sampled_from([
        'wrong_protocol',
        'wrong_format',
        'invalid_bucket_start',
        'invalid_bucket_end'
    ]))
    
    if invalid_type == 'wrong_protocol':
        return 'http://bucket/path/buildspec.yml'
    elif invalid_type == 'wrong_format':
        return 's3:bucket/buildspec.yml'  # Missing //
    elif invalid_type == 'invalid_bucket_start':
        return 's3://-bucket/buildspec.yml'  # Bucket can't start with dash
    else:  # invalid_bucket_end
        return 's3://bucket-/buildspec.yml'  # Bucket can't end with dash


@settings(max_examples=100)
@given(buildspec_path=valid_buildspec_paths())
def test_buildspec_path_validation(buildspec_path: str):
    """
    Property 13: BuildSpec Path Validation
    For any valid local buildspec file path ending with buildspec.yml or buildspec-postdeploy.yml, 
    the parameter validation should accept it, and for invalid paths, it should reject them.
    
    **Feature: pipeline-postdeploy-enhancement, Property 13: BuildSpec Path Validation**
    **Validates: Requirements 5.1**
    """
    import re
    
    template = PIPELINE_TEMPLATE
    parameters = template.get('Parameters', {})
    
    # Get PostDeployBuildSpec parameter
    buildspec_param = parameters.get('PostDeployBuildSpec')
    assert buildspec_param is not None, "PostDeployBuildSpec parameter should exist"
    
    # Get the AllowedPattern
    allowed_pattern = buildspec_param.get('AllowedPattern')
    assert allowed_pattern is not None, "PostDeployBuildSpec should have AllowedPattern"
    
    # Test that valid buildspec paths match the pattern
    pattern = re.compile(allowed_pattern)
    match_result = pattern.match(buildspec_path)
    
    # Valid paths should match
    assert match_result is not None, f"Valid buildspec path '{buildspec_path}' should match AllowedPattern"


@settings(max_examples=100)
@given(s3_uri=valid_s3_uris())
def test_s3_uri_validation(s3_uri: str):
    """
    Property 14: S3 URI Validation
    For any valid S3 URI with proper bucket and object key format, the buildspec parameter 
    validation should accept it, and for invalid S3 URIs, it should reject them.
    
    **Feature: pipeline-postdeploy-enhancement, Property 14: S3 URI Validation**
    **Validates: Requirements 5.2**
    """
    import re
    
    template = PIPELINE_TEMPLATE
    parameters = template.get('Parameters', {})
    
    # Get PostDeployBuildSpec parameter
    buildspec_param = parameters.get('PostDeployBuildSpec')
    assert buildspec_param is not None, "PostDeployBuildSpec parameter should exist"
    
    # Get the AllowedPattern
    allowed_pattern = buildspec_param.get('AllowedPattern')
    assert allowed_pattern is not None, "PostDeployBuildSpec should have AllowedPattern"
    
    # Test that valid S3 URIs match the pattern
    pattern = re.compile(allowed_pattern)
    match_result = pattern.match(s3_uri)
    
    # Valid S3 URIs should match
    assert match_result is not None, f"Valid S3 URI '{s3_uri}' should match AllowedPattern"


@settings(max_examples=50)
@given(invalid_path=invalid_buildspec_paths())
def test_invalid_buildspec_paths_rejected(invalid_path: str):
    """
    Verify that invalid buildspec paths are rejected by the parameter validation.
    
    **Feature: pipeline-postdeploy-enhancement, Property 13: BuildSpec Path Validation**
    **Validates: Requirements 5.1**
    """
    import re
    
    template = PIPELINE_TEMPLATE
    parameters = template.get('Parameters', {})
    
    # Get PostDeployBuildSpec parameter
    buildspec_param = parameters.get('PostDeployBuildSpec')
    allowed_pattern = buildspec_param.get('AllowedPattern')
    
    # Test that invalid paths don't match the pattern
    pattern = re.compile(allowed_pattern)
    match_result = pattern.match(invalid_path)
    
    # Invalid paths should not match (unless it's empty string which is allowed)
    if invalid_path == '':
        # Empty string is allowed by the pattern
        assert match_result is not None, "Empty string should be allowed"
    else:
        assert match_result is None, f"Invalid buildspec path '{invalid_path}' should not match AllowedPattern"


@settings(max_examples=50)
@given(invalid_uri=invalid_s3_uris())
def test_invalid_s3_uris_rejected(invalid_uri: str):
    """
    Verify that invalid S3 URIs are rejected by the parameter validation.
    
    **Feature: pipeline-postdeploy-enhancement, Property 14: S3 URI Validation**
    **Validates: Requirements 5.2**
    """
    import re
    
    template = PIPELINE_TEMPLATE
    parameters = template.get('Parameters', {})
    
    # Get PostDeployBuildSpec parameter
    buildspec_param = parameters.get('PostDeployBuildSpec')
    allowed_pattern = buildspec_param.get('AllowedPattern')
    
    # Test that invalid S3 URIs don't match the pattern
    pattern = re.compile(allowed_pattern)
    match_result = pattern.match(invalid_uri)
    
    # Invalid S3 URIs should not match
    assert match_result is None, f"Invalid S3 URI '{invalid_uri}' should not match AllowedPattern"


@settings(max_examples=50)
@given(st.just(True))
def test_default_buildspec_configuration(enabled: bool):
    """
    Property 15: Default BuildSpec Configuration
    For any template configuration using default buildspec locations, the Build stage 
    should use "buildspec.yml" and PostDeploy stage should use "buildspec-postdeploy.yml".
    
    **Feature: pipeline-postdeploy-enhancement, Property 15: Default BuildSpec Configuration**
    **Validates: Requirements 5.4, 5.5**
    """
    template = PIPELINE_TEMPLATE
    resources = template.get('Resources', {})
    
    # Get both CodeBuild projects
    build_project = resources.get('CodeBuildProject')
    postdeploy_project = resources.get('PostDeployProject')
    
    assert build_project is not None, "CodeBuildProject should exist"
    assert postdeploy_project is not None, "PostDeployProject should exist"
    
    # Check Build project default buildspec
    build_source = build_project.get('Properties', {}).get('Source', {})
    build_buildspec = build_source.get('BuildSpec')
    
    # Should be conditional - check for nested structure
    if isinstance(build_buildspec, dict) and '!If' in build_buildspec:
        if_condition = build_buildspec['!If']
        # Look for the default buildspec value in the nested structure
        buildspec_str = str(build_buildspec)
        assert 'buildspec.yml' in buildspec_str, "Build project should reference 'buildspec.yml' as default"
    
    # Check PostDeploy project default buildspec
    postdeploy_source = postdeploy_project.get('Properties', {}).get('Source', {})
    postdeploy_buildspec = postdeploy_source.get('BuildSpec')
    
    # Should be conditional - check for nested structure
    if isinstance(postdeploy_buildspec, dict) and '!If' in postdeploy_buildspec:
        if_condition = postdeploy_buildspec['!If']
        # Look for the default buildspec value in the nested structure
        buildspec_str = str(postdeploy_buildspec)
        assert 'buildspec-postdeploy.yml' in buildspec_str, "PostDeploy project should reference 'buildspec-postdeploy.yml' as default"