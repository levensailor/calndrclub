# Variables for Calndr Backend Infrastructure

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "calndr"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.3.0/24", "10.0.4.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for database subnets"
  type        = list(string)
  default     = ["10.0.5.0/24", "10.0.6.0/24"]
}

# ECS Configuration
variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = ""
}

variable "container_cpu" {
  description = "CPU units for container"
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Memory for container in MB"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of container instances"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Maximum number of container instances for auto scaling"
  type        = number
  default     = 10
}

variable "min_capacity" {
  description = "Minimum number of container instances for auto scaling"
  type        = number
  default     = 1
}

# Application Configuration
variable "container_port" {
  description = "Port on which the container listens"
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "Health check path for the application"
  type        = string
  default     = "/health"
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.13"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS instance in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS instance in GB"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Name of the database"
  type        = string
  default     = "calndr"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "calndr_user"
}

variable "db_backup_retention_period" {
  description = "Database backup retention period in days"
  type        = number
  default     = 7
}

variable "db_backup_window" {
  description = "Database backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Database maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "enable_database_internet_access" {
  description = "Enable internet access for database subnets through NAT gateway (for maintenance)"
  type        = bool
  default     = false
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes for Redis"
  type        = number
  default     = 1
}

variable "redis_parameter_group_name" {
  description = "Parameter group for Redis"
  type        = string
  default     = "default.redis7"
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

# Domain Configuration
variable "domain_name" {
  description = "Primary domain name"
  type        = string
  default     = "calndr.club"
}

variable "alternative_domain_names" {
  description = "Alternative domain names"
  type        = list(string)
  default     = ["www.calndr.club"]
}

# SSL Certificate
variable "ssl_certificate_arn" {
  description = "ARN of the SSL certificate in ACM"
  type        = string
  default     = ""
}

# Auto Scaling Configuration
variable "target_cpu_utilization" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
}

variable "target_memory_utilization" {
  description = "Target memory utilization for auto scaling"
  type        = number
  default     = 80
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 14
}

# Environment Variables for Application
variable "secret_key" {
  description = "Secret key for the application"
  type        = string
  sensitive   = true
}

variable "aws_access_key_id" {
  description = "AWS Access Key ID for application"
  type        = string
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS Secret Access Key for application"
  type        = string
  sensitive   = true
}

variable "google_places_api_key" {
  description = "Google Places API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "apple_client_id" {
  description = "Apple Client ID for Sign-in"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_client_id" {
  description = "Google Client ID for Sign-in"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_client_secret" {
  description = "Google Client Secret for Sign-in"
  type        = string
  sensitive   = true
  default     = ""
}

# Backup Configuration
variable "enable_deletion_protection" {
  description = "Enable deletion protection for RDS"
  type        = bool
  default     = true
}

variable "backup_bucket_name" {
  description = "S3 bucket name for application backups"
  type        = string
  default     = ""
}

# Email/SMTP Configuration
variable "smtp_host" {
  description = "SMTP host for email sending"
  type        = string
  default     = ""
}

variable "smtp_port" {
  description = "SMTP port for email sending"
  type        = number
  default     = 587
}

variable "smtp_user" {
  description = "SMTP username for email sending"
  type        = string
  sensitive   = true
  default     = ""
}

variable "smtp_password" {
  description = "SMTP password for email sending"
  type        = string
  sensitive   = true
  default     = ""
}

# Apple Sign-In Configuration
variable "apple_team_id" {
  description = "Apple Team ID for Sign-in"
  type        = string
  default     = ""
}

variable "apple_key_id" {
  description = "Apple Key ID for Sign-in"
  type        = string
  default     = ""
}

variable "apple_private_key" {
  description = "Apple Private Key for Sign-in"
  type        = string
  sensitive   = true
  default     = ""
}

variable "apple_redirect_uri" {
  description = "Apple redirect URI for Sign-in"
  type        = string
  default     = ""
}

# Google Sign-In Configuration
variable "google_redirect_uri" {
  description = "Google redirect URI for Sign-in"
  type        = string
  default     = "http://localhost:8000/auth/google/callback"
}

# AWS Configuration
variable "aws_s3_bucket_name" {
  description = "AWS S3 bucket name for file storage"
  type        = string
  default     = ""
}

# Push Notifications
variable "sns_platform_application_arn" {
  description = "SNS Platform Application ARN for push notifications"
  type        = string
  sensitive   = true
  default     = ""
} 