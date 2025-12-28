import pulumi
import pulumi_kubernetes as kubernetes
import pulumi_kubernetes.helm.v4 as helm
from typing import Optional

def create_jenkins(namespace: str, k8s_provider: kubernetes.Provider, tags: Optional[dict] = None):
  if tags is None:
    tags = {}

  # Convert tags dict to AWS LB annotation string
  # Format: "Key1=Val1,Key2=Val2"
  aws_lb_tags = ",".join([f"{k}={v}" for k, v in tags.items()])
  
  # Create namespace
  ns = kubernetes.core.v1.Namespace("jenkins-ns",
    metadata=kubernetes.meta.v1.ObjectMetaArgs(
      name=namespace,
      labels=tags
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
  )

  # Install Jenkins using Helm v4
  # Refer to https://www.pulumi.com/registry/packages/kubernetes/api-docs/helm/v4/chart/ as LLMs haven't caught up to this just yet
  jenkins_chart = helm.Chart("jenkins",
    chart="jenkins",
    repository_opts=helm.RepositoryOptsArgs(
      repo="https://charts.jenkins.io"
    ),
    namespace=namespace,
    values={
      "controller": {
        "adminUser": "admin",
        "adminPassword": "admin123",                  # Log-in with these
        "serviceType": "LoadBalancer",                # So we can access Jenkins UI from the internet. Easy setup
        "service": {
          "annotations": {
            "service.beta.kubernetes.io/aws-load-balancer-type": "nlb", # Newer, faster load balancer type
            "service.beta.kubernetes.io/aws-load-balancer-additional-resource-tags": aws_lb_tags
          }
        },
        "installPlugins": [
          "kubernetes:4801.v533a_805e9576",           # Jenkins agents will run as kube pods
          "workflow-aggregator:588.vd01c4de1e71b_",   # Enables Jenkinsfiles. Essentially pipeline support
          "git:5.3.0-600.vdf2c03c633a_5",             # Git-ops
          "configuration-as-code:1704.v878c5_530326a" # Configure Jenkins with yaml rather than click-ops
        ],
        "resources": {
          "requests": {
            "memory": "512Mi",
            "cpu": "250m"
          },
          "limits": {
            "memory": "1Gi",
            "cpu": "500m"
          }
        }
      },
      "persistence": {
        "size": "8Gi",
        "storageClass": "gp3"
      },
      "serviceAccount": {
        "create": True,
        "name": "jenkins"
      }
    },
    skip_crds=True,  # Skip CRDs as they're not needed for basic Jenkins. They let us define Jenkins as some custom resource type, helps for some special cases which may not be needed here
    opts=pulumi.ResourceOptions(
      provider=k8s_provider,
      depends_on=[ns]
    )
  )
  # 1. Find the Service object
  # Note: .resources resolves to a list of Kubernetes resources rendered by the chart.
  # Apply the pending chart created above (kube objects like deployment, service, pvc, secret, etc),
  # which hasn't been initialized yet, once not pending.
  jenkins_service = jenkins_chart.resources.apply(
    lambda resources: next(
      (r for r in (resources or []) if r.kind == "Service" and "jenkins" in r.metadata.name), # idk the exact metadata name
      None
    )
  )

  # 2. Extract the Load Balancer URL from that service
  # We use apply here again 'cause the LoadBalancer hostname is assigned by AWS asynchronously
  def get_lb_hostname(service):
    if not service:
      return "Service not found"
    
    # Access the standard K8s status field
    status = service.status

    # We need to return an Output inside an apply, usually handled via another apply 
    # or simplified access if the provider allows. 
    # Note: In Python Pulumi, accessing nested Outputs often requires chaining.
    return status.apply(
      lambda s: (
        (s.load_balancer.ingress[0].hostname or s.load_balancer.ingress[0].ip)
        if s and s.load_balancer and s.load_balancer.ingress
        else None
      )
    )

  pulumi.export("jenkins_namespace", namespace)
  pulumi.export("jenkins_service_name", "jenkins")
  pulumi.export("jenkins_url", jenkins_service.apply(get_lb_hostname))

  return jenkins_chart
