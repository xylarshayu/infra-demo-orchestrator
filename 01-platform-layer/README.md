# Platform Layer - Infrastructure Demo

The platform layer of the infrastructure demo project. This layer creates the foundational AWS infrastructure including VPC, EKS cluster, Jenkins CI, and Flux GitOps.

## Overview

This Pulumi program provisions:

- **VPC** with public and private subnets, NAT Gateway
- **EKS Cluster** with managed node groups (t3.medium instances)
- **ECR Repository** for container images
- **Jenkins** deployed as a Kubernetes service with LoadBalancer access
- **Flux** bootstrapped for GitOps from a GitHub repository

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured with credentials
- Pulumi CLI installed and logged in
- Python 3.10+ with `uv` package manager
- GitHub account with a repository for GitOps
- GitHub Personal Access Token with `repo` scope

## Configuration

### Required Configuration

Set the following configuration values:

```bash
# AWS Region
pulumi config set aws:region ap-south-1

# GitHub configuration for Flux GitOps
pulumi config set github_owner <your-github-username>
pulumi config set github_repo <your-gitops-repo-name>
pulumi config set github_branch main

# GitHub token (required for creating deploy keys)
# Option 1: Set as Pulumi secret
pulumi config set --secret github:token <your-github-token>

# Option 2: Set as environment variable
export GITHUB_TOKEN=<your-github-token>
```

### Optional Configuration

```bash
# Jenkins admin password (defaults to admin123 if not set)
pulumi config set --secret jenkins_password <your-password>
```

### GitHub Token Permissions

The GitHub token needs the following permissions:
- `repo` - Full control of private repositories (for deploy key creation)

## Deployment

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Preview changes:
   ```bash
   pulumi preview
   ```

3. Deploy the stack:
   ```bash
   pulumi up
   ```

4. Get outputs:
   ```bash
   pulumi stack output kubeconfig --show-secrets > kubeconfig.yaml
   export KUBECONFIG=./kubeconfig.yaml
   kubectl get nodes
   ```

## Tear Down

To destroy all resources and avoid ongoing costs:

```bash
pulumi destroy
```

**Note:** After destroy, verify in AWS Console that all resources are removed:
- EC2 > Load Balancers
- VPC > NAT Gateways
- EKS > Clusters
- ECR > Repositories

## Cost Estimate

When running (per hour):
- EKS Control Plane: ~$0.10/hr
- 2x t3.medium EC2: ~$0.083/hr
- NAT Gateway: ~$0.045/hr
- Network Load Balancer: ~$0.022/hr

**Estimated: ~$0.25-0.30 per hour**

## Outputs

| Output | Description |
|--------|-------------|
| `vpc_id` | VPC ID |
| `kubeconfig` | Kubeconfig for kubectl access |
| `cluster_name` | EKS cluster name |
| `cluster_oidc_url` | OIDC provider URL for IRSA |
| `ecr_registry_url` | ECR repository URL |
| `jenkins_url` | Jenkins UI URL (LoadBalancer) |
| `jenkins_namespace` | Kubernetes namespace for Jenkins |

## Jenkins Access

After deployment, access Jenkins at the `jenkins_url` output:
- Username: `admin`
- Password: `admin123` (or custom if set via `pulumi config set --secret jenkins_password`)

## Project Structure

```
01-platform-layer/
├── __main__.py           # Main Pulumi program
├── components/
│   ├── vpc.py            # VPC and networking
│   ├── eks.py            # EKS cluster and ECR
│   ├── jenkins.py        # Jenkins Helm deployment
│   └── flux.py           # Flux GitOps bootstrap
├── Pulumi.yaml           # Project configuration
├── Pulumi.main.yaml      # Stack configuration
└── pyproject.toml        # Python dependencies
```
