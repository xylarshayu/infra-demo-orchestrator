import pulumi
import pulumi_aws as aws
import pulumi_eks as eks
import pulumi_awsx as awsx
from typing import Optional

def create_k8s_cluster(vpc: awsx.ec2.Vpc, tags: Optional[dict] = None) -> eks.Cluster:
  if tags is None:
    tags = {}

  # 1. Create an ECR Registry for our apps
  registry = aws.ecr.Repository("app-registry",
    force_delete=True, # Cleanup when re-run
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
      scan_on_push=True
    ),
    tags=tags
  )

  # 2. Create an EKS Cluster
  # Note: At minimum a t3.medium for the node group, t2.micro wont do for EKS stuff + Argo + Apps
  cluster= eks.Cluster("platform-cluster",
    version="1.34",                             # Pinned Kubernetes version
    storage_classes={
      "gp3": eks.StorageClassArgs(
        type="gp3",                             # Default storage class
        default=True,
        encrypted=True,
        reclaim_policy="Delete"
      )
    },
    vpc_id=vpc.vpc_id,                          # Use the VPC we created
    public_subnet_ids=vpc.public_subnet_ids,    # For load balancers (internet facing)
    private_subnet_ids=vpc.private_subnet_ids,  # For worker nodes (private)
    # Node Group:
    instance_type="t3.medium",                  # 2 vCPU, 4GB RAM. Minimum for EKS + Argo + Apps
    desired_capacity=2,
    min_size=1,
    max_size=3,
    # IRSA (IAM Roles for Service Accounts):
    create_oidc_provider=True,                   # Lets pods assume IAM Roles
    tags=tags
  )

  # 3. Export critical details
  pulumi.export("kubeconfig", cluster.kubeconfig)
  pulumi.export("cluster_name", cluster.eks_cluster.name)
  pulumi.export("ecr_registry_url", registry.repository_url)
  pulumi.export("cluster_oidc_url", cluster.core.oidc_provider.url)

  return cluster
