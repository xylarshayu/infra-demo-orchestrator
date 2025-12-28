# How the deployment works and infra setup

NOTE: IGNORE THIS DOC, NOT PROPERLY YET, IS PLACEHOLDER

## Design Decisions

- Each **environment** houses its own isolated set of services, which can be independently developed by the dev team. They'll have their own CI/CD pipeline, and their own set of environment variables. Accordingly, an *environment* maps to:
  1. Kubernetes namespace
  2. Subdomain
  3. Git branch name
  4. AWS SSM parameter store path
  5. Pulumi stack
  6. Environment configuration values yaml file
- CI/CD is handled by Jenkins, detailed in [this doc](./CICD-Design.md).
- Secrets management is handled by AWS SSM, detailed in [this doc](./Secrets-Design.md).
- This repository handles **all of these**, though its functions for creating an environment and managing secrets are decidedly separate.

## Approach



## Tools

**Infrastructure-as-code**, specifically with Pulumi. Chose it over Terraform due to the recent bad practices of terraform's maintainers after being acquired, eg. sunsetting the CDK.

We'll use Python as it's (relatively) more dev-ops person friendly than, say, Typescript.

Helm helps parameterize the yaml files needed for Kubernetes, different parameters per environment.

As this is an AWS setup, we'll be using EKS (flexible enough for us, maybe unlike Fargate), an EC2 for Jenkins (which will use Kaniko to build images), and ECR to store the images. We'll also use SSM for environment variable storage, and also for the source-of-truth of image version.

## Deployment Setup

**Pulumi**