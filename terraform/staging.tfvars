# Staging environment configuration
aws_region = "us-east-1"
environment = "staging"
project_name = "calndr"

# VPC Configuration
vpc_cidr = "10.1.0.0/16"
public_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnet_cidrs = ["10.1.3.0/24", "10.1.4.0/24"]
database_subnet_cidrs = ["10.1.5.0/24", "10.1.6.0/24"]

# Application secrets (set proper values in environment or override)
secret_key = "staging_secret_key_change_me"
aws_access_key_id = "placeholder"
aws_secret_access_key = "placeholder"

# Database configuration - smaller for staging
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
db_max_allocated_storage = 50
db_backup_retention_period = 3

# Redis configuration - smaller for staging
redis_node_type = "cache.t3.micro"

# ECS configuration - smaller for staging
container_cpu = 256
container_memory = 512
desired_count = 1
min_capacity = 1
max_capacity = 2

# Auto-scaling
target_cpu_utilization = 70
target_memory_utilization = 80

# Domain configuration for staging (no custom domain for now)
domain_name = ""
alternative_domain_names = []

# Monitoring
log_retention_days = 7

# Backup settings - less strict for staging
enable_deletion_protection = false 