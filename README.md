# Atlantis Template Repository for Serverless Deployments using AWS SAM and CloudFormation

- Create a central S3 location to obtain CloudFormation templates for deployments.
- Provides scripts and structure for managing and publishing your organization's CloudFormation templates for SAM deployments.
- Can be used to `include` from S3 location in other templates and with [Atlantis CloudFormation configuration for SAM](https://github.com/63Klabs/atlantis-cfn-configuration-repo-for-serverless-deployments/settings/variables/actions) to facilitate deployments. 

The intended users of this repository are AWS account admins, architects, and platform engineers. Those performing developer and software engineer roles, and CloudFormation executions utilizing the templates, will need read access to the S3 bucket in order to include the templates and modules during deployments.

> If you do not wish to maintain your own templates and just wish to utilize them FOR BEGINNING, EXPERIMENTAL, EDUCATIONAL, and TRAINING PURPOSES, you DO NOT need to deploy your own S3 bucket of templates. Just use `S3://63klabs` which is publicly available. It will get you started quicker and does not require advanced knowledge of everything covered in the deployment documentation. Just go build!

You can reference the original source repository of these templates on GitHub: [Atlantis Template Repository for Serverless Deployments using AWS SAM and CloudFormation](https://github.com/63Klabs/atlantis-cfn-template-repo-for-serverless-deployments)

## Deploy to your own S3 Template Bucket

These templates are available from `s3://63klabs` for use in your own projects, which is fine for getting started, learning, and experimenting, but you will eventually want to host your own copies of these templates, including those that you create yourself. You will also host them on an S3 bucket only accessible within your organization where only certain individuals have access.

Download this repository and utilize the commands in the buildspec.yml file to manage your own deployments to your own organization's S3 template bucket.

See the [scripts README](./scripts/README.md) for more information on manual and automated deployments. (Hint: [template-pipeline-build-only](./templates/v2/pipeline/template-pipeline-build-only.yml) is a template you can use for your very own pipeline or you can deploy using the [GitHub actions workflow](./.github/workflows/deploy.yml)!).

## CloudFormation Template Validation

This repository includes automated CloudFormation template validation using cfn-lint to ensure template quality and catch syntax errors before deployment.

### Features

- **Automatic Template Discovery**: Recursively scans the `templates/v2` directory for all CloudFormation template files
- **Comprehensive Validation**: Uses cfn-lint to validate templates against AWS best practices and syntax rules
- **Local Development Integration**: Integrates with pytest for local testing alongside existing test suites
- **CI/CD Pipeline Integration**: Automatically validates templates during build process
- **Detailed Error Reporting**: Provides specific error details including file paths and violation descriptions

### Local Development Setup

1. **Set up the virtual environment**:
   ```bash
   python3 scripts/setup_venv.py
   ```

2. **Activate the virtual environment**:
   ```bash
   # Linux/macOS
   source .venv/bin/activate
   
   # Windows
   .venv\Scripts\activate
   ```

3. **Run CloudFormation template validation**:
   ```bash
   # Run all tests including CFN validation
   python -m pytest tests/
   
   # Run only CFN template validation
   python -m pytest tests/test_cfn_templates.py
   
   # Run CFN validation standalone
   python scripts/cfn_lint_runner.py
   ```

### CI/CD Integration

CloudFormation template validation is automatically integrated into the build pipeline via `buildspec.yml`. The validation:

- Runs during the build phase after dependency installation
- Fails the build if any templates have validation errors
- Provides detailed error reports in build logs
- Uses isolated virtual environment for dependency management

### Template Validation Rules

The validation process checks for:

- CloudFormation syntax errors
- AWS resource property validation
- Best practice compliance
- Security and performance recommendations
- Template structure and formatting

### Troubleshooting

**Virtual Environment Issues**:
- Ensure Python 3.7+ is installed
- Run `python3 scripts/setup_venv.py` to recreate the virtual environment
- Check that cfn-lint is properly installed: `.venv/bin/cfn-lint --version`

**Template Validation Errors**:
- Review error messages for specific file paths and line numbers
- Consult [cfn-lint documentation](https://github.com/aws-cloudformation/cfn-lint) for rule details
- Use `cfn-lint --help` for additional validation options

## Tutorial

TODO

## Changelog

[Change Log](./CHANGELOG.md)

## Author

Chad Kluck
DevOps & Developer Experience Engineer
AWS Certified
[Website](https://chadkluck.me)
