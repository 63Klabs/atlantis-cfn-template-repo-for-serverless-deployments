# Atlantis Template Repository for Serverless Deployments using AWS SAM and CloudFormation

Scripts and structure for managing templates and publishing to your organization's infrastructure module and template S3 bucket.

The intended users of this repository are AWS account admins, architects, and platform engineers. Those performing developer and software engineer roles will need read access to the S3 bucket in order to include the templates and modules in their deployments.

To deploy these templates, use [Atlantis CloudFormation Configuration Repository for Serverless Deployments](https://github.com/63klabs/atlantis-cfn-configuration-repo-for-serverless-deployments) available on GitHub.

## Deploy to your own S3 Template Bucket

These templates are available from `s3://63klabs` for use in your own projects, which is fine for getting started, learning, and experimenting, but you will eventually want to host your own copies of these templates, including those that you create yourself. You will also host them on an S3 bucket only accessible within your organization where only certain individuals have access.

Download this repository and utilize the commands in the buildspec.yml file to manage your own deployments to your own organization's S3 template bucket.

If using AWS CodePipeline, just create a new pipeline that monitors changes to a branch in your repository and copies changes to an S3 bucket.

> Hint: You can use the [template-pipeline-two-stage.yml](./templates/v2/pipeline/template-pipeline-two-stage.yml) to deploy your AWS CodePipeline. All you need is an S3 bucket to use as the `HostBucket`.

## Scripts

Use the scripts in the scripts directory to manage your templates in S3. Use the examples in [buildspec.yml](./buildspec.yml) and [scripts documentation](./scripts/README.md).

A zip file of the scripts can be copied from `s3://63klabs/atlantis/utilities/template_scripts.zip` (or your own bucket) programmatically for use in other pipeline scripts.

## Tutorial

TODO

## Changelog

TODO

## Author

Chad Kluck, Software Engineer, AWS Certified, [Website](https://chadkluck.me)
