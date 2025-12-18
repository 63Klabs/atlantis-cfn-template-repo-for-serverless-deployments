# PostDeploy Stage Examples

This directory contains example buildspec files and parameter configurations demonstrating different use cases for the PostDeploy stage functionality in the CloudFormation pipeline template.

## Overview

The PostDeploy stage is an optional final stage in the CodePipeline that runs after the main deployment completes. It's designed for tasks that require the application infrastructure to be deployed first, such as:

- Integration tests against deployed endpoints
- Configuration validation and compliance checking
- Exporting configurations (e.g., OpenAPI specs from API Gateway)
- Post-deployment data migration or setup tasks

## Directory Structure

```
examples/
├── README.md                                          # This file
├── buildspec-postdeploy-api-docs.yml                 # API documentation export
├── buildspec-postdeploy-integration-tests.yml        # Integration testing
├── buildspec-postdeploy-config-validation.yml        # Configuration validation
└── parameter-configs/
    ├── postdeploy-api-docs-example.json              # API docs export config
    ├── postdeploy-integration-tests-example.json     # Integration testing config
    ├── postdeploy-config-validation-example.json     # Config validation config
    └── postdeploy-disabled-example.json              # PostDeploy disabled config
```

## Buildspec Examples

### 1. API Documentation Export (`buildspec-postdeploy-api-docs.yml`)

**Purpose**: Automatically export OpenAPI specifications from deployed API Gateway instances and upload them to S3 for documentation generation.

**Key Features**:
- Discovers API Gateway REST APIs tagged with the application identifier
- Exports OpenAPI 3.0 specifications with integrations, authorizers, and documentation
- Validates exported specifications using swagger-parser
- Generates documentation metadata with timestamps and application info
- Uploads to S3 bucket organized by date for version tracking

**Use Cases**:
- Automated API documentation generation
- API specification archival and versioning
- Integration with external documentation systems
- Compliance documentation for API governance

**Environment Variables Used**:
- `S3_STATIC_HOST_BUCKET`: Target bucket for documentation files
- Standard pipeline variables for resource discovery

### 2. Integration Testing (`buildspec-postdeploy-integration-tests.yml`)

**Purpose**: Run comprehensive integration tests against the deployed application to validate functionality and performance.

**Key Features**:
- Discovers deployed CloudFormation stack resources and outputs
- Tests API endpoint accessibility and response codes
- Validates environment-specific configuration
- Performs basic performance testing (response times, success rates)
- Generates HTML and JSON test reports
- Fails build if critical tests fail

**Test Categories**:
- **Stack Validation**: CloudFormation stack health and status
- **Endpoint Testing**: API accessibility and basic functionality
- **Environment Configuration**: Environment-specific settings validation
- **Resource Tagging**: Governance and compliance tag verification
- **Performance Testing**: Basic load and response time validation

**Use Cases**:
- Automated deployment validation
- Continuous integration testing
- Performance regression detection
- Environment-specific behavior validation

### 3. Configuration Validation (`buildspec-postdeploy-config-validation.yml`)

**Purpose**: Validate deployed infrastructure against security, compliance, and operational requirements.

**Key Features**:
- CloudFormation stack configuration validation
- IAM role and permissions boundary checking
- CloudWatch log group retention policy validation
- Security scanning using Checkov
- Environment-specific compliance checks
- Comprehensive compliance reporting

**Validation Categories**:
- **Stack Health**: CloudFormation stack status and configuration
- **Security Compliance**: IAM roles, permissions boundaries, security policies
- **Operational Standards**: Log retention, monitoring resources, tagging
- **Environment-Specific**: Production vs. development requirement differences
- **Compliance Frameworks**: SOX, PCI-DSS, AWS Well-Architected Framework

**Use Cases**:
- Production deployment validation
- Security and compliance auditing
- Operational readiness verification
- Regulatory compliance documentation

## Parameter Configuration Examples

### API Documentation Export Configuration

```json
{
  "PostDeployStageEnabled": "true",
  "PostDeployS3StaticHostBucket": "myorg-docs-api-documentation",
  "PostDeployBuildSpec": "examples/buildspec-postdeploy-api-docs.yml"
}
```

**Prerequisites**:
- S3 bucket for documentation storage must exist
- API Gateway instances should be properly tagged
- PostDeploy service role needs S3 write permissions

### Integration Testing Configuration

```json
{
  "PostDeployStageEnabled": "true",
  "PostDeployS3StaticHostBucket": "acme-test-results-bucket",
  "PostDeployBuildSpec": "examples/buildspec-postdeploy-integration-tests.yml"
}
```

**Prerequisites**:
- Application should expose testable endpoints
- S3 bucket for test results (optional)
- SSM parameters configured for application

### Configuration Validation Configuration

```json
{
  "PostDeployStageEnabled": "true",
  "PostDeployS3StaticHostBucket": "corp-compliance-validation-reports",
  "PostDeployBuildSpec": "examples/buildspec-postdeploy-config-validation.yml",
  "PostDeploySvcRoleIncludeManagedPolicyArns": "arn:aws:iam::123456789012:policy/ComplianceValidation"
}
```

**Prerequisites**:
- Compliance validation managed policies
- S3 bucket for compliance reports
- Permissions boundary policies (for production)

### PostDeploy Disabled Configuration

```json
{
  "PostDeployStageEnabled": "false"
}
```

**Result**: Pipeline has only 3 stages (Source → Build → Deploy), no PostDeploy resources created.

## Environment Variables Available in PostDeploy

All PostDeploy buildspec files have access to the same environment variables as the Build stage:

### AWS Environment
- `AWS_PARTITION`: AWS partition (aws, aws-cn, aws-us-gov)
- `AWS_REGION`: AWS region where pipeline is running
- `AWS_ACCOUNT`: AWS account ID

### Application Identification
- `PREFIX`: Resource prefix for naming
- `PROJECT_ID`: Project identifier
- `STAGE_ID`: Stage identifier (branch alias)

### Pipeline Configuration
- `S3_ARTIFACTS_BUCKET`: Pipeline artifacts bucket
- `DEPLOY_ENVIRONMENT`: Deployment environment (DEV/TEST/PROD)
- `PARAM_STORE_HIERARCHY`: SSM parameter path prefix

### PostDeploy-Specific
- `S3_STATIC_HOST_BUCKET`: Target bucket for PostDeploy artifacts

## Best Practices

### 1. Buildspec Organization
- Keep buildspec files in the repository for version control
- Use descriptive names that indicate the PostDeploy purpose
- Include comprehensive comments and documentation
- Handle errors gracefully with appropriate exit codes

### 2. Environment-Specific Behavior
- Use `DEPLOY_ENVIRONMENT` variable to adjust behavior
- More strict validation in PROD, more lenient in DEV
- Different test suites for different environments
- Environment-specific resource discovery and validation

### 3. Error Handling
- Fail fast on critical errors that indicate deployment problems
- Use warnings for non-critical issues that should be addressed
- Generate comprehensive reports even when tests fail
- Provide clear error messages for troubleshooting

### 4. Resource Discovery
- Use application identifier (`PREFIX-PROJECT_ID-STAGE_ID`) for resource discovery
- Leverage CloudFormation stack outputs for endpoint discovery
- Use resource tags for identifying application-specific resources
- Handle cases where expected resources don't exist

### 5. Artifact Management
- Upload results to S3 for persistence and audit trails
- Use organized folder structures with timestamps
- Generate both human-readable and machine-readable reports
- Include metadata for report context and traceability

## Customization Guide

### Creating Custom PostDeploy Buildspecs

1. **Start with an example**: Copy the closest matching example buildspec
2. **Modify phases**: Adjust install, pre_build, build, and post_build phases
3. **Update dependencies**: Install required tools and libraries
4. **Implement logic**: Add your specific validation or processing logic
5. **Handle artifacts**: Configure appropriate artifact outputs
6. **Test thoroughly**: Validate in development before production use

### Common Customization Patterns

#### Database Migration
```yaml
build:
  commands:
    - echo "Running database migrations"
    - python manage.py migrate --check
    - python manage.py migrate
```

#### Custom Health Checks
```yaml
build:
  commands:
    - echo "Running custom health checks"
    - curl -f $API_ENDPOINT/health || exit 1
    - python custom_health_check.py
```

#### Configuration Export
```yaml
post_build:
  commands:
    - aws ssm get-parameters-by-path --path $PARAM_STORE_HIERARCHY --recursive > config-export.json
    - aws s3 cp config-export.json s3://$S3_STATIC_HOST_BUCKET/configs/
```

## Troubleshooting

### Common Issues

1. **PostDeploy resources not created**
   - Verify `PostDeployStageEnabled` is set to "true"
   - Check CloudFormation conditions are properly configured
   - Ensure pipeline template version supports PostDeploy

2. **Permission errors in PostDeploy stage**
   - Verify PostDeployServiceRole has required permissions
   - Check permissions boundary configuration
   - Ensure S3 bucket policies allow PostDeploy role access

3. **Resource discovery failures**
   - Verify CloudFormation stack naming conventions
   - Check resource tagging for application identification
   - Ensure stack is in complete state before PostDeploy runs

4. **Build failures in PostDeploy**
   - Check buildspec syntax and dependencies
   - Verify environment variables are available
   - Review CloudWatch logs for detailed error messages

### Debugging Tips

1. **Enable verbose logging**: Add `set -x` to buildspec commands for detailed output
2. **Check CloudWatch logs**: PostDeploy logs are in `/aws/codebuild/{PREFIX}-{PROJECT_ID}-{STAGE_ID}-PostDeploy`
3. **Validate permissions**: Use AWS CLI commands to test resource access
4. **Test buildspec locally**: Use CodeBuild local builds for faster iteration

## Migration from Build Stage

If you currently perform post-deployment tasks in the Build stage, consider migrating to PostDeploy:

### Benefits of Migration
- **Logical separation**: Build focuses on packaging, PostDeploy on validation
- **Failure isolation**: PostDeploy failures don't affect deployment success
- **Resource access**: PostDeploy runs after deployment, can access deployed resources
- **Conditional execution**: PostDeploy can be disabled for faster development cycles

### Migration Steps
1. Identify post-deployment tasks in current buildspec
2. Create new PostDeploy buildspec with these tasks
3. Remove post-deployment tasks from Build buildspec
4. Test in development environment
5. Update production pipeline configuration
6. Monitor and validate PostDeploy execution

## Support and Contributions

For questions, issues, or contributions related to PostDeploy examples:

1. Review the pipeline template documentation
2. Check CloudFormation stack events and outputs
3. Examine CloudWatch logs for detailed error information
4. Test changes in development environment first
5. Follow infrastructure-as-code best practices for modifications

Remember that PostDeploy is designed to enhance deployment validation and operational tasks without impacting the core deployment process. Use it to add value through better testing, validation, and operational visibility.