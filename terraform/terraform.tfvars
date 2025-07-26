# Basic configuration for ECR deployment
aws_region = "us-east-1"
environment = "production"
project_name = "calndr"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
database_subnet_cidrs = ["10.0.5.0/24", "10.0.6.0/24"]

# Application secrets (temporary values)
secret_key = "temp_secret_key_for_ecr_creation"
aws_access_key_id = "placeholder"
aws_secret_access_key = "placeholder"

# Database configuration
db_instance_class = "db.t3.micro"
db_allocated_storage = 20

# Redis configuration
redis_node_type = "cache.t3.micro"

# ECS configuration
ecs_cpu = 256
ecs_memory = 512
ecs_desired_count = 1
ecs_min_capacity = 1
ecs_max_capacity = 3

# Auto-scaling
cpu_target_value = 70
memory_target_value = 80
