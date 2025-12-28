import pulumi
import pulumi_kubernetes as kubernetes
import pulumi_kubernetes.helm.v4 as helm
from typing import Optional

def create_jenkins(
    namespace: str, 
    k8s_provider: kubernetes.Provider, 
    tags: Optional[dict] = None,
    admin_user: str = "admin",
    admin_password: str = None,
):
  """
  Deploy Jenkins as a Kubernetes service using Helm.
  
  Args:
    namespace: Kubernetes namespace for Jenkins
    k8s_provider: Pulumi Kubernetes provider
    tags: AWS resource tags
    admin_user: Jenkins admin username (default: admin)
    admin_password: Jenkins admin password (default: admin123 if not set via config)
  """
  if tags is None:
    tags = {}
  
  # Use provided password or default for demo purposes
  # For production, set via: pulumi config set --secret jenkins_password <password>
  jenkins_password = admin_password or "admin123"

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
        "adminUser": admin_user,
        "adminPassword": jenkins_password,            # Set via pulumi config set --secret jenkins_password
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
  # 1. Find the Jenkins Service object from the Helm chart resources
  # Note: .resources resolves to a list of Kubernetes resources rendered by the chart.
  # Each resource is a Pulumi resource object. We identify the Service by checking:
  # - The Pulumi type contains "Service" (more reliable than checking .kind which might be an Output)
  # - The resource name contains "jenkins"
  def find_jenkins_service(resources):
    if not resources:
      return None
    for r in resources:
      # Check the Pulumi resource type (e.g., "kubernetes:core/v1:Service")
      resource_type = getattr(r, 'pulumi_type', '') or ''
      is_service = 'Service' in resource_type and 'ServiceAccount' not in resource_type
      
      # Check the Pulumi resource name (set during chart rendering)
      resource_name = getattr(r, 'pulumi_resource_name', '') or ''
      is_jenkins = 'jenkins' in resource_name.lower()
      
      if is_service and is_jenkins:
        return r
    return None
  
  jenkins_service = jenkins_chart.resources.apply(find_jenkins_service)

  # 2. Extract the Load Balancer URL from the Service's status
  # The status.loadBalancer.ingress is populated by AWS after the NLB is provisioned
  def get_lb_hostname(service):
    if not service:
      return "Service not found - check resources after deployment"
    
    # service.status is an Output[ServiceStatus], so we need to apply
    return service.status.apply(
      lambda s: (
        (s.load_balancer.ingress[0].hostname or s.load_balancer.ingress[0].ip)
        if s and s.load_balancer and s.load_balancer.ingress
        else "LoadBalancer pending - check AWS console"
      )
    )

  pulumi.export("jenkins_namespace", namespace)
  pulumi.export("jenkins_service_name", "jenkins")
  pulumi.export("jenkins_url", jenkins_service.apply(get_lb_hostname))

  return jenkins_chart
