import pulumi
import pulumi_flux as flux
import pulumi_github as github
import pulumi_tls as tls
import pulumi_kubernetes as kubernetes

def bootstrap_flux(name: str, k8s_provider: kubernetes.Provider, github_owner: str, github_repo: str, github_branch: str):
  # 1. Create a Deploy Key for Flux to access the repo
  # We generate this in Pulumi so we can control the private key
  ssh_key = tls.PrivateKey(f"flux-{name}-key", 
      algorithm="ECDSA",
      ecdsa_curve="P256"
  )

  # 2. Add the Deploy Key to GitHub (Write access required for Flux to push image updates/tags)
  deploy_key = github.RepositoryDeployKey(f"flux-{name}-deploy-key",
      repository=github_repo,
      title="flux-cluster-bootstrap",
      key=ssh_key.public_key_openssh,
      read_only=False 
  )

  provider = flux.Provider(f"flux-{name}-provider",
    git=flux.ProviderGitArgs(
      url=f"ssh://git@github.com/{github_owner}/{github_repo}.git",
      branch=github_branch,
      ssh=flux.ProviderGitSshArgs(username="git", private_key=ssh_key.private_key_pem)
    )
  )

  # 3. Bootstrap Flux into the cluster
  # This does exactly what `flux bootstrap github` does
  flux_bootstrap = flux.FluxBootstrapGit(f"flux-{name}-bootstrap",
    path="clusters/platform",           # Folder in repo to sync
    version="v2.3.0",                   # Pin Flux version
    interval="1m0s",
    log_level="info",
    namespace=f"flux-{name}-ns",       # Standard Flux namespace
    components=[                        # Default components
      "source-controller",
      "kustomize-controller",
      "helm-controller",
    ],
    opts=pulumi.ResourceOptions(
      provider=provider,
      parent=k8s_provider,
      depends_on=[deploy_key]
    )
  )

  return flux_bootstrap