import pulumi
import pulumi_kubernetes as kubernetes
import pulumi_kubernetes.helm.v4 as helm

# NOTE: **NOT** in use. This was the original git-ops provider I was going to go with. However for our use-case this is
# overkill and too resource hungry for the simple use-case of a set-it-and-forget-it thing that's just meant to 
# watch Git → render manifests → apply → reconcile
# This file is left here in case this needs to be revisted

def create_argocd(namespace: str, cluster: kubernetes.Provider):

  # Create namespace
  ns = kubernetes.core.v1.Namespace("argocd-ns",
    metadata=kubernetes.meta.v1.ObjectMetaArgs(
      name=namespace
    ),
    opts=pulumi.ResourceOptions(provider=cluster)
  )

  ADMIN_PASSWORD_HASH = "$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi" # admin123

  # Install ArgoCD using Helm v4
  # Refer to https://www.pulumi.com/registry/packages/kubernetes/api-docs/helm/v4/chart/ as LLMs haven't caught up to this just yet
  argocd_chart = helm.Chart("argocd",
    chart="argo-cd",
    version="6.7.5",                                # Pin to stable version
    repository_opts=helm.RepositoryOptsArgs(
      repo="https://argoproj.github.io/argo-helm"
    ),
    namespace=namespace,
    values={
      "global": {
        "domain": "argocd.local",                   # Internal domain; irrelevant without ingress
        "image": {
          "tag": "v2.11.3"                          # Pin Argo CD image version for reproducibility
        },
        "networkPolicy": {
          "create": False                           # No network policies for simplicity
        },
      },
      "server": {
        "enabled": True,                            # Cannot disable in Helm; user ClusterIP to isolate
        "service": {
          "type": "ClusterIP"                       # No need for external access
        },
        "ingress": {
          "enabled": False  # No ingress exposure
        },
        "replicas": 1,
        "resources": {
          "requests": {
            "cpu": "100m",
            "memory": "128Mi"
          },
          "limits": {
            "cpu": "200m",
            "memory": "256Mi"
          }
        },
        "extraArgs": [
          # Optional: Skip TLS verification for internal comms (POC only; insecure in prod)
          "--insecure"
        ],
        "autoscaling": {
          "enabled": False
        }
      },
      # Repo Server: Handles Git cloning/Helm rendering; slightly higher resources for chart ops
      "repoServer": {
        "replicas": 1,
        "resources": {
          "requests": {
            "cpu": "200m",
            "memory": "256Mi"
          },
          "limits": {
            "cpu": "500m",
            "memory": "512Mi"
          }
        },
        "autoscaling": {
          "enabled": False
        },
        "useEphemeralHelmWorkingDir": True         # Use ephemeral storage for Helm charts
      },
      "controller": {
        "replicas": 1,
        "resources": {
          "requests": {
            "cpu": "100m",
            "memory": "128Mi"
          },
          "limits": {
            "cpu": "200m",
            "memory": "256Mi"
          }
        },
        "metrics": {
          "enabled": False                        # Skipping metrics to reduce overhead
        },
        "autoscaling": {
          "enabled": False
        }
      },
      # Redis: Single-pod (non-HA) for caching; minimal
      "redis": {
        "enabled": True,
        "resources": {
          "requests": {
            "cpu": "50m",
            "memory": "64Mi"
          },
          "limits": {
            "cpu": "100m",
            "memory": "128Mi"
          }
        },
        "metrics": {
          "enabled": False
        },
        "exporter": {
          "enabled": False
        }
      },
      "redis-ha": {
        "enabled": False  # Explicitly disable HA for minimal/cost reasons
      },
      # Disable Dex (SSO/OIDC) - not needed for GitOps/CLI
      "dex": {
        "enabled": False
      },
      "notifications": {
        "enabled": False
      },
      # ApplicationSet: Disable if not using generators (basic GitOps doesn't need)
      "applicationSet": {
        "enabled": False
      },
      "configs": {
        "secret": {
          "create": True,
          "argocdServerAdminPassword": ADMIN_PASSWORD_HASH,
        },
        "cm": {
          "create": True,
          "admin.enabled": True,  # Allow local admin user
          "exec.enabled": False,  # Disable exec feature (UI-related)
          "statusbadge.enabled": False,  # Disable badges
          "timeout.reconciliation": "300s"  # Slightly higher for POC stability
        },
        # No pre-configured repos; add via Argo CD App manifests in GitOps repo
        "params": {
          "create": True,
          "server.insecure": True  # Allow insecure for internal access (POC; disable in prod)
        }
      },
      # RBAC: Minimal - no default policies
      "rbac": {
        "create": True,
        "policy.default": "",
        "policy.csv": ""
      }
    },
    skip_crds=False, # Install CRDs (required for Argo CD)
    opts=pulumi.ResourceOptions(
      provider=cluster,
      depends_on=[ns]
    )
  )

  pulumi.export("argocd_namespace", namespace)
  pulumi.export("argocd_admin_password", "admin123")  # Plaintext warning: Use Pulumi config/secrets in prod
  # To access: kubectl port-forward svc/argocd-server -n argocd 8080:443
  # Then argocd login localhost:8080 --username admin --password admin123

  return argocd_chart