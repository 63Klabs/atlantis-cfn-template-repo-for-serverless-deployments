# Atlantis template repository for serverless deployments using AWS SAM and CloudFormation

Scripts and structure for managing templates and publishing to S3

## Deploy to your own S3

These templates are available from `s3://63klabs` for use in your own projects, which is fine for getting started, learning, and experimenting, but you will most likely want to host your own templates, including those that you create yourself.

Download this repository and utilize the commands in the buildspec.yml file to manage your own deployments to your own organization's S3 bucket.

If using AWS CodePipeline, just create a new pipeline that monitors changes to a branch in your repository.
