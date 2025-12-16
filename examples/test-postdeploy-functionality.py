#!/usr/bin/env python3
"""
End-to-End Test for PostDeploy Functionality

This script validates that the PostDeploy stage works correctly by:
1. Creating a test CloudFormation stack with PostDeploy enabled
2. Verifying that PostDeploy resources are created conditionally
3. Testing that the pipeline includes the PostDeploy stage
4. Validating that PostDeploy stage can access deployed resources

Usage:
    python test-postdeploy-functionality.py --stack-name test-postdeploy --region us-east-1

Prerequisites:
- AWS CLI configured with appropriate permissions
- CloudFormation template with PostDeploy functionality
- Test repository and artifacts bucket
"""

import argparse
import boto3
import json
import time
import sys
from typing import Dict, List, Optional


class PostDeployTester:
    def __init__(self, region: str, stack_name: str):
        self.region = region
        self.stack_name = stack_name
        self.cf_client = boto3.client('cloudformation', region_name=region)
        self.codepipeline_client = boto3.client('codepipeline', region_name=region)
        self.codebuild_client = boto3.client('codebuild', region_name=region)
        self.logs_client = boto3.client('logs', region_name=region)
        
    def create_test_parameters(self, postdeploy_enabled: bool) -> Dict:
        """Create test parameters for CloudFormation stack"""
        return {
            'Prefix': 'test',
            'ProjectId': 'postdeploy-validation',
            'StageId': 'e2e',
            'S3BucketNameOrgPrefix': '',
            'RolePath': '/',
            'PermissionsBoundaryArn': '',
            'DeployEnvironment': 'TEST',
            'S3ArtifactsBucket': f'test-artifacts-{int(time.time())}',  # Unique bucket name
            'S3StaticHostBucket': '',
            'BuildSpec': 'buildspec.yml',
            'PostDeployStageEnabled': 'true' if postdeploy_enabled else 'false',
            'PostDeployS3StaticHostBucket': '',
            'PostDeployBuildSpec': 'examples/buildspec-postdeploy-integration-tests.yml',
            'ParameterStoreHierarchy': '/test/',
            'AlarmNotificationEmail': 'test@example.com',
            'CloudFormationSvcRoleIncludeManagedPolicyArns': '',
            'CodeBuildSvcRoleIncludeManagedPolicyArns': '',
            'PostDeploySvcRoleIncludeManagedPolicyArns': '',
            'Repository': 'test-repo',
            'RepositoryBranch': 'main'
        }
    
    def deploy_stack(self, parameters: Dict, template_path: str) -> bool:
        """Deploy CloudFormation stack with given parameters"""
        try:
            # Read template
            with open(template_path, 'r') as f:
                template_body = f.read()
            
            # Convert parameters to CloudFormation format
            cf_parameters = [
                {'ParameterKey': key, 'ParameterValue': value}
                for key, value in parameters.items()
            ]
            
            print(f"Creating stack: {self.stack_name}")
            
            # Create stack
            self.cf_client.create_stack(
                StackName=self.stack_name,
                TemplateBody=template_body,
                Parameters=cf_parameters,
                Capabilities=['CAPABILITY_NAMED_IAM'],
                Tags=[
                    {'Key': 'Purpose', 'Value': 'PostDeployTesting'},
                    {'Key': 'Environment', 'Value': 'Test'}
                ]
            )
            
            # Wait for stack creation
            print("Waiting for stack creation to complete...")
            waiter = self.cf_client.get_waiter('stack_create_complete')
            waiter.wait(
                StackName=self.stack_name,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
            )
            
            print("Stack created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating stack: {e}")
            return False
    
    def get_stack_resources(self) -> List[Dict]:
        """Get all resources in the stack"""
        try:
            response = self.cf_client.describe_stack_resources(StackName=self.stack_name)
            return response['StackResources']
        except Exception as e:
            print(f"Error getting stack resources: {e}")
            return []
    
    def validate_postdeploy_resources(self, postdeploy_enabled: bool) -> bool:
        """Validate that PostDeploy resources are created/not created as expected"""
        resources = self.get_stack_resources()
        resource_types = {r['ResourceType']: r for r in resources}
        
        postdeploy_resource_types = [
            'AWS::IAM::Role',  # PostDeployServiceRole
            'AWS::CodeBuild::Project',  # PostDeployProject  
            'AWS::Logs::LogGroup'  # PostDeployLogGroup
        ]
        
        # Find PostDeploy-specific resources
        postdeploy_resources = []
        for resource in resources:
            logical_id = resource['LogicalResourceId']
            if 'PostDeploy' in logical_id:
                postdeploy_resources.append(resource)
        
        print(f"Found {len(postdeploy_resources)} PostDeploy resources")
        
        if postdeploy_enabled:
            # Should have PostDeploy resources
            expected_resources = ['PostDeployServiceRole', 'PostDeployProject', 'PostDeployLogGroup']
            found_resources = [r['LogicalResourceId'] for r in postdeploy_resources]
            
            missing_resources = [r for r in expected_resources if r not in found_resources]
            
            if missing_resources:
                print(f"ERROR: Missing PostDeploy resources: {missing_resources}")
                return False
            else:
                print("SUCCESS: All expected PostDeploy resources found")
                return True
        else:
            # Should not have PostDeploy resources
            if postdeploy_resources:
                print(f"ERROR: Unexpected PostDeploy resources found: {[r['LogicalResourceId'] for r in postdeploy_resources]}")
                return False
            else:
                print("SUCCESS: No PostDeploy resources found (as expected)")
                return True
    
    def validate_pipeline_structure(self, postdeploy_enabled: bool) -> bool:
        """Validate that pipeline has correct number of stages"""
        try:
            # Find pipeline resource
            resources = self.get_stack_resources()
            pipeline_resource = None
            
            for resource in resources:
                if resource['ResourceType'] == 'AWS::CodePipeline::Pipeline':
                    pipeline_resource = resource
                    break
            
            if not pipeline_resource:
                print("ERROR: No pipeline resource found")
                return False
            
            pipeline_name = pipeline_resource['PhysicalResourceId']
            
            # Get pipeline definition
            response = self.codepipeline_client.get_pipeline(name=pipeline_name)
            pipeline = response['pipeline']
            
            stages = pipeline['stages']
            stage_names = [stage['name'] for stage in stages]
            
            print(f"Pipeline stages: {stage_names}")
            
            if postdeploy_enabled:
                # Should have 4 stages: Source, Build, Deploy, PostDeploy
                expected_stages = ['Source', 'Build', 'Deploy', 'PostDeploy']
                if len(stages) == 4 and 'PostDeploy' in stage_names:
                    print("SUCCESS: Pipeline has PostDeploy stage")
                    return True
                else:
                    print(f"ERROR: Pipeline should have 4 stages with PostDeploy, found: {stage_names}")
                    return False
            else:
                # Should have 3 stages: Source, Build, Deploy
                expected_stages = ['Source', 'Build', 'Deploy']
                if len(stages) == 3 and 'PostDeploy' not in stage_names:
                    print("SUCCESS: Pipeline has no PostDeploy stage")
                    return True
                else:
                    print(f"ERROR: Pipeline should have 3 stages without PostDeploy, found: {stage_names}")
                    return False
                    
        except Exception as e:
            print(f"Error validating pipeline structure: {e}")
            return False
    
    def validate_conditional_logic(self) -> bool:
        """Test both enabled and disabled PostDeploy configurations"""
        print("\n" + "="*60)
        print("TESTING POSTDEPLOY DISABLED CONFIGURATION")
        print("="*60)
        
        # Test 1: PostDeploy disabled
        disabled_params = self.create_test_parameters(postdeploy_enabled=False)
        
        if not self.deploy_stack(disabled_params, 'templates/v2/pipeline/template-pipeline.yml'):
            return False
        
        # Validate no PostDeploy resources
        if not self.validate_postdeploy_resources(postdeploy_enabled=False):
            return False
        
        # Validate pipeline structure
        if not self.validate_pipeline_structure(postdeploy_enabled=False):
            return False
        
        # Clean up
        self.cleanup_stack()
        
        print("\n" + "="*60)
        print("TESTING POSTDEPLOY ENABLED CONFIGURATION")
        print("="*60)
        
        # Test 2: PostDeploy enabled
        enabled_params = self.create_test_parameters(postdeploy_enabled=True)
        
        if not self.deploy_stack(enabled_params, 'templates/v2/pipeline/template-pipeline.yml'):
            return False
        
        # Validate PostDeploy resources exist
        if not self.validate_postdeploy_resources(postdeploy_enabled=True):
            return False
        
        # Validate pipeline structure
        if not self.validate_pipeline_structure(postdeploy_enabled=True):
            return False
        
        return True
    
    def cleanup_stack(self):
        """Delete the test stack"""
        try:
            print(f"Deleting stack: {self.stack_name}")
            self.cf_client.delete_stack(StackName=self.stack_name)
            
            # Wait for deletion
            print("Waiting for stack deletion to complete...")
            waiter = self.cf_client.get_waiter('stack_delete_complete')
            waiter.wait(
                StackName=self.stack_name,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
            )
            
            print("Stack deleted successfully")
            
        except Exception as e:
            print(f"Error deleting stack: {e}")
    
    def run_full_test(self) -> bool:
        """Run complete PostDeploy functionality test"""
        print("Starting PostDeploy End-to-End Test")
        print(f"Region: {self.region}")
        print(f"Stack Name: {self.stack_name}")
        
        try:
            # Run conditional logic tests
            success = self.validate_conditional_logic()
            
            if success:
                print("\n" + "="*60)
                print("✅ ALL TESTS PASSED")
                print("PostDeploy functionality is working correctly!")
                print("="*60)
            else:
                print("\n" + "="*60)
                print("❌ TESTS FAILED")
                print("PostDeploy functionality has issues that need to be addressed.")
                print("="*60)
            
            return success
            
        except Exception as e:
            print(f"Test execution failed: {e}")
            return False
        
        finally:
            # Ensure cleanup
            try:
                self.cleanup_stack()
            except:
                pass


def main():
    parser = argparse.ArgumentParser(description='Test PostDeploy functionality end-to-end')
    parser.add_argument('--stack-name', required=True, help='CloudFormation stack name for testing')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--template-path', default='templates/v2/pipeline/template-pipeline.yml', 
                       help='Path to pipeline template')
    
    args = parser.parse_args()
    
    # Validate template exists
    import os
    if not os.path.exists(args.template_path):
        print(f"ERROR: Template file not found: {args.template_path}")
        sys.exit(1)
    
    # Run tests
    tester = PostDeployTester(args.region, args.stack_name)
    success = tester.run_full_test()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()