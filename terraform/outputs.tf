# Outputs for the Calndr Backend Infrastructure

output "vpc_id" {
  description = "The VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "The public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "The private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "The database subnet IDs"
  value       = aws_subnet.database[*].id
}

output "load_balancer_dns" {
  description = "The DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "The zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "database_endpoint" {
  description = "The RDS database endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "database_port" {
  description = "The RDS database port"
  value       = aws_db_instance.main.port
}

output "redis_endpoint" {
  description = "The Redis primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "The Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "ecr_repository_url" {
  description = "The ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "The ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "The ECS service name"
  value       = aws_ecs_service.app.name
}

output "cloudwatch_dashboard_url" {
  description = "The CloudWatch dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "domain_name" {
  description = "The primary domain name"
  value       = var.domain_name
}

output "application_url" {
  description = "The application URL"
  value       = "https://${var.domain_name}"
}

output "github_actions_role_arn" {
  description = "The ARN of the GitHub Actions IAM role"
  value       = aws_iam_role.github_actions.arn
}

# Sensitive outputs for CI/CD setup
output "ssm_parameters" {
  description = "SSM parameter names for secrets"
  value = {
    secret_key      = aws_ssm_parameter.secret_key.name
    db_user         = aws_ssm_parameter.db_user.name
    db_password     = aws_ssm_parameter.db_password.name
    aws_access_key  = aws_ssm_parameter.aws_access_key.name
    aws_secret_key  = aws_ssm_parameter.aws_secret_key.name
    redis_auth      = var.environment == "production" ? aws_ssm_parameter.redis_auth[0].name : null
  }
  sensitive = true
} 