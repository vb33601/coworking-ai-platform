terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
  backend "s3" {
    bucket = "coworking-ai-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "coworking-ai-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = false
  single_nat_gateway = false

  tags = {
    Environment = var.environment
    Project     = "coworking-ai"
  }
}

# EKS
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "coworking-ai-${var.environment}"
  cluster_version = "1.29"

  cluster_endpoint_public_access = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 2
      max_size     = 10

      instance_types = ["m6i.xlarge"]
      capacity_type  = "ON_DEMAND"

      labels = {
        workload = "general"
      }
    }

    ai_workloads = {
      desired_size = 2
      min_size     = 1
      max_size     = 6

      instance_types = ["m6i.2xlarge"]
      capacity_type  = "ON_DEMAND"

      labels = {
        workload = "ai"
      }

      taints = [{
        key    = "ai-workload"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  tags = {
    Environment = var.environment
    Project     = "coworking-ai"
  }
}

# RDS PostgreSQL
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "coworking-ai-${var.environment}"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = "db.r6g.xlarge"

  allocated_storage     = 100
  max_allocated_storage = 500

  db_name  = "coworking_ai"
  username = "postgres"
  port     = 5432

  multi_az               = var.environment == "production"
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  deletion_protection     = var.environment == "production"

  tags = {
    Environment = var.environment
    Project     = "coworking-ai"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "coworking-ai-rds-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "redis" {
  name       = "coworking-ai-redis-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "coworking-ai-${var.environment}"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
}

resource "aws_security_group" "redis" {
  name_prefix = "coworking-ai-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 6379
    to_port   = 6379
    protocol  = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

# S3 for reports and assets
resource "aws_s3_bucket" "assets" {
  bucket = "coworking-ai-assets-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}
