# Staging environment configuration
aws_region = "us-east-1"
environment = "staging"
project_name = "calndr"

# VPC Configuration
vpc_cidr = "10.1.0.0/16"
public_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnet_cidrs = ["10.1.3.0/24", "10.1.4.0/24"]
database_subnet_cidrs = ["10.1.5.0/24", "10.1.6.0/24"]

# Application secrets (stored in SSM Parameter Store - see README for setup)
secret_key = ""  # Stored in SSM: /calndr/staging/secret_key
aws_access_key_id = ""  # Stored in SSM: /calndr/staging/aws_access_key_id
aws_secret_access_key = ""  # Stored in SSM: /calndr/staging/aws_secret_access_key

# API Keys and External Services (stored in SSM Parameter Store)
google_places_api_key = ""  # Stored in SSM: /calndr/staging/google_places_api_key
sns_platform_application_arn = ""  # Stored in SSM: /calndr/staging/sns_platform_application_arn

# Email/SMTP Configuration
smtp_host = "email-smtp.us-east-1.amazonaws.com"
smtp_port = 25
smtp_user = ""  # Stored in SSM: /calndr/staging/smtp_user
smtp_password = ""  # Stored in SSM: /calndr/staging/smtp_password

# Apple Sign-In Configuration
apple_client_id = "club.calndr"
apple_team_id = "HU4EE3MB4T"
apple_key_id = "9Q9D25269Q"
apple_private_key = ""  # Stored in SSM: /calndr/staging/apple_private_key
apple_redirect_uri = "https://staging.calndr.club/api/v1/auth/apple/callback"

# Google Sign-In Configuration
# IMPORTANT: Replace with your NEW Web Application Client ID (not the iOS one)  
google_client_id = "427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com"
google_client_secret = ""
google_redirect_uri = "https://staging.calndr.club/auth/google/callback"

# AWS S3 Configuration
aws_s3_bucket_name = "calndr-profile"

# Database configuration - smaller for staging
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
db_max_allocated_storage = 50
db_backup_retention_period = 3
db_name = "postgres"
db_user = "postgres"
db_password = ""  # Stored in SSM: /calndr/staging/db_password

# Enable database internet access for staging maintenance
enable_database_internet_access = true

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

# Domain configuration for staging
domain_name = "staging.calndr.club"
alternative_domain_names = []

# Monitoring
log_retention_days = 7

# Backup settings - less strict for staging
enable_deletion_protection = false 