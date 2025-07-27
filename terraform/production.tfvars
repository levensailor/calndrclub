# Production environment configuration
aws_region = "us-east-1"
environment = "production"
project_name = "calndr"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
database_subnet_cidrs = ["10.0.5.0/24", "10.0.6.0/24"]

# Application secrets (stored in SSM Parameter Store - see README for setup)
secret_key = ""  # Stored in SSM: /calndr/production/secret_key
aws_access_key_id = ""  # Stored in SSM: /calndr/production/aws_access_key_id
aws_secret_access_key = ""  # Stored in SSM: /calndr/production/aws_secret_access_key

# API Keys and External Services (stored in SSM Parameter Store)
google_places_api_key = ""  # Stored in SSM: /calndr/production/google_places_api_key
sns_platform_application_arn = ""  # Stored in SSM: /calndr/production/sns_platform_application_arn

# Email/SMTP Configuration
smtp_host = "email-smtp.us-east-1.amazonaws.com"
smtp_port = 25
smtp_user = ""  # Stored in SSM: /calndr/production/smtp_user
smtp_password = ""  # Stored in SSM: /calndr/production/smtp_password

# Apple Sign-In Configuration
apple_client_id = "club.calndr"
apple_team_id = "HU4EE3MB4T"
apple_key_id = "9Q9D25269Q"
apple_private_key = ""  # Stored in SSM: /calndr/production/apple_private_key
apple_redirect_uri = "https://calndr.club/api/v1/auth/apple/callback"

# Google Sign-In Configuration
# IMPORTANT: Replace with your NEW Web Application Client ID (not the iOS one)
google_client_id = "427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com"
google_client_secret = ""
google_redirect_uri = "https://calndr.club/auth/google/callback"

# AWS S3 Configuration
aws_s3_bucket_name = "calndr-profile"

# Database configuration - production sized
db_instance_class = "db.t3.small"
db_allocated_storage = 100
db_max_allocated_storage = 500
db_backup_retention_period = 30
db_name = "postgres"
db_user = "postgres"
db_password = ""  # Stored in SSM: /calndr/production/db_password

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