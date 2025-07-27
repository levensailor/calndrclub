# Production environment configuration
aws_region = "us-east-1"
environment = "production"
project_name = "calndr"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
database_subnet_cidrs = ["10.0.5.0/24", "10.0.6.0/24"]

# Application secrets (set proper values in environment or override)
secret_key = "production_secret_key_change_me"
aws_access_key_id = "placeholder"
aws_secret_access_key = "placeholder"

# API Keys and External Services
google_places_api_key = ""
sns_platform_application_arn = ""

# Email/SMTP Configuration
smtp_host = ""
smtp_port = 587
smtp_user = ""
smtp_password = ""

# Apple Sign-In Configuration
apple_client_id = ""
apple_team_id = ""
apple_key_id = ""
apple_private_key = ""
apple_redirect_uri = ""

# Google Sign-In Configuration
google_client_id = ""
google_client_secret = ""
google_redirect_uri = "https://calndr.club/auth/google/callback"

# AWS S3 Configuration
aws_s3_bucket_name = ""

# Database configuration - production sized
db_instance_class = "db.t3.small"
db_allocated_storage = 100
db_max_allocated_storage = 500
db_backup_retention_period = 30

# Disable database internet access for production security
enable_database_internet_access = false

# Redis configuration - production sized
redis_node_type = "cache.t3.small"

# ECS configuration - production sized
container_cpu = 512
container_memory = 1024
desired_count = 2
min_capacity = 2
max_capacity = 10

# Auto-scaling
target_cpu_utilization = 70
target_memory_utilization = 80

# Domain configuration for production
domain_name = "calndr.club"
alternative_domain_names = ["www.calndr.club"]

# Monitoring
log_retention_days = 30

# Backup settings - strict for production
enable_deletion_protection = true 