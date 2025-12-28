import pulumi
import pulumi_awsx as awsx
from typing import Optional

def create_vpc(tags: Optional[dict] = None):
  if tags is None:
    tags = {}

  # Create a VPC with explicit subnets for EKS
  vpc = awsx.ec2.Vpc("platform-vpc",
          enable_dns_hostnames=True,  # Required for EKS node registration
          cidr_block="10.0.0.0/16",   # Standard large private IP range
          number_of_availability_zones=1, # In actual production scenarios, don't use 1 'cause single point of failure. Use 2+
          subnet_specs=[
            awsx.ec2.SubnetSpecArgs(
              type=awsx.ec2.SubnetType.PUBLIC, # Has IGW, hosts NAT gateway
              cidr_mask=24,                    # Creates a /24 subnet (256 IP addresses)
              name="public",
              tags={
                "kubernetes.io/role/elb": "1", # For internet-facing LBs
                **tags,
              }
            ),
            awsx.ec2.SubnetSpecArgs(
              type=awsx.ec2.SubnetType.PRIVATE,         # No IGW, uses NAT for internet
              cidr_mask=24,                    # Creates a /24 subnet (256 IP addresses)
              name="private",
              tags={
                "kubernetes.io/role/internal-elb": "1", # For internal LBs
                **tags,
              }
            )
          ],
          # NAT Gateway - Critical for private subnets to access internet
          nat_gateways=awsx.ec2.NatGatewayConfigurationArgs(
            strategy=awsx.ec2.NatGatewayStrategy.SINGLE # In actual production scenarios, don't use SINGLE 'cause single point of failure. One per AZ
          ),
          tags={
            "Name": "wrkflowautom-vpc",
            "kubernetes.io/cluster/platform-cluster": "shared", # EKS needs this tag to discover and manage the VPC
            **tags,
          }
  )

  pulumi.export("vpc_id", vpc.vpc_id)
  pulumi.export("public_subnet_ids", vpc.public_subnet_ids)
  pulumi.export("private_subnet_ids", vpc.private_subnet_ids)

  return vpc