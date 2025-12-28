import pulumi
import pulumi_flux as flux
import pulumi_github as github
import pulumi_tls as tls
import pulumi_kubernetes as kubernetes
import pulumi_eks as eks
import json

def bootstrap_flux(
    name: str, 
    k8s_provider: kubernetes.Provider, 
    cluster: eks.Cluster,
    github_owner: str, 
    github_repo: str, 
    github_branch: str,
    github_token: pulumi.Output[str] = None,
):
  # Configure GitHub provider with token from Pulumi config
  # Token can be set via: pulumi config set --secret github:token <your-token>
  # Or via GITHUB_TOKEN environment variable
  gh_provider = github.Provider(f"github-{name}-provider",
    owner=github_owner,
    token=github_token,  # Will use GITHUB_TOKEN env var if None
  ) if github_token else None
  # 1. Create a Deploy Key for Flux to access the repo
  # We generate this in Pulumi so we can control the private key
  ssh_key = tls.PrivateKey(f"flux-{name}-key", 
      algorithm="ECDSA",
      ecdsa_curve="P256"
  )

  # 2. Add the Deploy Key to GitHub (Write access required for Flux to push image updates/tags)
  # Requires GITHUB_TOKEN env var or github:token in Pulumi config
  deploy_key_opts = pulumi.ResourceOptions(provider=gh_provider) if gh_provider else None
  deploy_key = github.RepositoryDeployKey(f"flux-{name}-deploy-key",
      repository=github_repo,
      title="flux-cluster-bootstrap",
      key=ssh_key.public_key_openssh,
      read_only=False,
      opts=deploy_key_opts,
  )

  # 3. Extract Kubernetes connection details from the EKS cluster kubeconfig
  # The kubeconfig is a dict/JSON structure, we need to extract the relevant fields
  def extract_k8s_config(kubeconfig):
    """Extract host and CA certificate from kubeconfig for Flux provider"""
    if isinstance(kubeconfig, str):
      kubeconfig = json.loads(kubeconfig)
    
    # Get the first cluster's details
    cluster_info = kubeconfig["clusters"][0]["cluster"]
    host = cluster_info["server"]
    ca_cert = cluster_info.get("certificate-authority-data", "")
    
    return {"host": host, "ca_cert": ca_cert}
  
  k8s_config = cluster.kubeconfig.apply(extract_k8s_config)

  # 4. Create Flux provider with Kubernetes and Git configuration
  # For EKS, we use exec-based authentication via aws-iam-authenticator
  provider = flux.Provider(f"flux-{name}-provider",
    kubernetes=flux.ProviderKubernetesArgs(
      host=k8s_config.apply(lambda c: c["host"]),
      cluster_ca_certificate=k8s_config.apply(lambda c: c["ca_cert"]),
      # Use exec-based authentication for EKS (aws-iam-authenticator)
      exec_=flux.ProviderKubernetesExecArgs(
        api_version="client.authentication.k8s.io/v1beta1",
        command="aws",
        args=["eks", "get-token", "--cluster-name", cluster.eks_cluster.name],
      )
    ),
    git=flux.ProviderGitArgs(
      url=f"ssh://git@github.com/{github_owner}/{github_repo}.git",
      branch=github_branch,
      ssh=flux.ProviderGitSshArgs(username="git", private_key=ssh_key.private_key_pem)
    )
  )

  # 5. Bootstrap Flux into the cluster
  # This does exactly what `flux bootstrap github` does
  flux_bootstrap = flux.FluxBootstrapGit(f"flux-{name}-bootstrap",
    path="clusters/platform",           # Folder in repo to sync
    version="v2.3.0",                   # Pin Flux version
    interval="1m0s",
    log_level="info",
    namespace=f"flux-{name}-ns",        # Flux namespace
    components=[                        # Minimal headless components
      "source-controller",
      "kustomize-controller",
      "helm-controller",
    ],
    opts=pulumi.ResourceOptions(
      provider=provider,
      depends_on=[deploy_key, cluster]  # Removed invalid parent, added cluster dependency
    )
  )

  return flux_bootstrap