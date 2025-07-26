# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-cache-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-cache-subnet-group"
  }
}

# ElastiCache Replication Group (Redis)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id         = "${var.project_name}-${var.environment}-redis"
  description                  = "Redis cluster for ${var.project_name} ${var.environment}"
  
  node_type                    = var.redis_node_type
  port                         = 6379
  parameter_group_name         = var.redis_parameter_group_name
  
  num_cache_clusters           = var.redis_num_cache_nodes
  
  engine_version               = var.redis_engine_version
  subnet_group_name            = aws_elasticache_subnet_group.main.name
  security_group_ids           = [aws_security_group.redis.id]

  # Backup and maintenance
  automatic_failover_enabled   = var.redis_num_cache_nodes > 1
  multi_az_enabled            = var.environment == "production" && var.redis_num_cache_nodes > 1
  
  # Backup configuration
  snapshot_retention_limit     = var.environment == "production" ? 7 : 1
  snapshot_window             = "03:00-05:00"
  maintenance_window          = "sun:05:00-sun:07:00"
  
  # Enable backups for production
  auto_minor_version_upgrade   = true
  
  # Security
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = false # FastAPI client doesn't support TLS to Redis out of box
  auth_token                   = var.environment == "production" ? random_password.redis_auth.result : null

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Redis auth token for production
resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

# Store Redis auth token in SSM
resource "aws_ssm_parameter" "redis_auth" {
  count = var.environment == "production" ? 1 : 0
  
  name  = "/${var.project_name}/${var.environment}/redis/auth_token"
  type  = "SecureString"
  value = random_password.redis_auth.result

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-auth"
  }
}

# Store Redis auth token in SSM for staging (no auth needed but parameter expected)
resource "aws_ssm_parameter" "redis_auth_staging" {
  count = var.environment != "production" ? 1 : 0
  
  name  = "/${var.project_name}/${var.environment}/redis/auth_token"
  type  = "SecureString"
  value = ""  # Empty for staging as Redis auth is not enabled

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-auth"
  }
}

# CloudWatch Log Group for Redis
resource "aws_cloudwatch_log_group" "redis" {
  name              = "/elasticache/${var.project_name}-${var.environment}-redis"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-logs"
  }
}

# CloudWatch Alarms for Redis
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-memory"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FreeableMemory"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "10000000"  # 10MB in bytes
  alarm_description   = "This metric monitors Redis memory usage"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-memory-alarm"
  }
} 