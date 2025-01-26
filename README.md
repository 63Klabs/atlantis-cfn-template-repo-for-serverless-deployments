# Atlantis template repository for serverless deployments using AWS SAM and CloudFormation

Scripts and structure for managing templates and publishing to S3

## Deploy to your own S3 Template Bucket

These templates are available from `s3://63klabs` for use in your own projects, which is fine for getting started, learning, and experimenting, but you will most likely want to host your own templates, including those that you create yourself. You will also most likely host them on an S3 bucket that is is only accessible within your organization where only certain individuals have access.

Download this repository and utilize the commands in the buildspec.yml file to manage your own deployments to your own organization's S3 template bucket.

If using AWS CodePipeline, just create a new pipeline that monitors changes to a branch in your repository and copies changes to an S3 bucket.

> Hint: You can use the [template-pipeline-two-stage.yml](./templates/v2/pipeline/template-pipeline-two-stage.yml) to deploy your AWS CodePipeline.

## Scripts

The `scripts` directory contains scripts to use during CodeBuild or from the command line locally.

These scripts are available from `s3://63klabs/atlantis/utilities/template_scripts.zip` and can be downloaded upon request for use in build scripts. The buildspec file includes a zip and upload command for you to use to host your own version.

```bash
# Install:
pip install -r requirements.txt

# -- OR --
pip install boto3

# -- OR --
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/Mac
pip install -r requirements.txt
```

### s3_inventory.py

This will inventory the objects in the bucket, including each version of the object, and generate files in both csv and json.

If you run this script from the command line, you can specify a profile to use with the `--profile` option. The profile used must have valid credentials and permissions to:

- s3:ListBucket
- s3:GetBucketVersioning
- s3:ListBucketVersions

```bash
# Make Executable:
chmod +x s3_inventory.py

# Basic usage
./scripts/s3_inventory.py my-bucket-name

# For a specific bucket path
./scripts/s3_inventory.py my-bucket-name path/to/inventory

# With specific AWS profile
./scripts/s3_inventory.py my-bucket-name --profile myprofile

# With custom output directory
./scripts/s3_inventory.py my-bucket-name --output-dir /path/to/output 
# output path is relative to the current working directory the command was issued from, not relative to the script.
# For example executing ./scripts/s3_inventory.py with --output-dir output will output to ./output
# cd into scripts and executing ./s3_inventory.py with --output-dir output will output to output in the scripts directory
```
