"""Platform lifecycle layer of infrastructure project"""

import pulumi
import pulumi_kubernetes as kubernetes
from components.vpc import create_vpc
from components.eks import create_k8s_cluster
from components.jenkins import create_jenkins
from components.flux import bootstrap_flux

config = pulumi.Config()
gh_owner = config.require("github_owner")
gh_repo = config.require("github_repo")
gh_branch = config.require("github_branch")

common_tags = {
  "Project": "infra-demo",
  "ManagedBy": "Pulumi",
}

vpc = create_vpc(tags=common_tags)
cluster = create_k8s_cluster(vpc, tags=common_tags)
k8s_provider = kubernetes.Provider("k8s-provider",
  kubeconfig=cluster.kubeconfig,
  opts=pulumi.ResourceOptions(depends_on=[cluster])
)
jenkins = create_jenkins("jenkins", k8s_provider, tags=common_tags)
flux = bootstrap_flux("main", k8s_provider, gh_owner, gh_repo, gh_branch)

pulumi.export("vpc_id", vpc.vpc_id)
pulumi.export("kubeconfig", cluster.kubeconfig)
pulumi.export("cluster_name", cluster.eks_cluster.name)
pulumi.export("cluster_oidc_url", cluster.core.oidc_provider.url)