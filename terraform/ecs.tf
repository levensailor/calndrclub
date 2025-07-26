# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}-cluster"

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs_exec.name
      }
    }
  }

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-cluster"
  }
}

# ECS Capacity Provider (for Fargate)
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-${var.environment}-logs"
  }
}

resource "aws_cloudwatch_log_group" "ecs_exec" {
  name              = "/ecs/${var.project_name}-${var.environment}-exec"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-${var.environment}-exec-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-app"
      image = "${aws_ecr_repository.app.repository_url}:${var.environment}-latest"

      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "APP_ENV"
          value = var.environment
        },
        {
          name  = "DB_HOST"
          value = split(":", aws_db_instance.main.endpoint)[0]
        },
        {
          name  = "DB_PORT"
          value = "5432"
        },
        {
          name  = "DB_NAME"
          value = aws_db_instance.main.db_name
        },
        {
          name  = "REDIS_HOST"
          value = aws_elasticache_replication_group.main.primary_endpoint_address
        },
        {
          name  = "REDIS_PORT"
          value = "6379"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "REDIS_DB"
          value = "0"
        },
        {
          name  = "REDIS_MAX_CONNECTIONS"
          value = "20"
        },
        {
          name  = "REDIS_SOCKET_TIMEOUT"
          value = "5"
        },
        {
          name  = "PROJECT_NAME"
          value = "Calndr API"
        },
        {
          name  = "VERSION"
          value = "1.0.0"
        },
        {
          name  = "DESCRIPTION"
          value = "Family Calendar Management API"
        },
        {
          name  = "API_V1_STR"
          value = "/api/v1"
        },
        {
          name  = "ALGORITHM"
          value = "HS256"
        },
        {
          name  = "ACCESS_TOKEN_EXPIRE_MINUTES"
          value = "43200"
        },
        # Cache TTL settings
        {
          name  = "CACHE_TTL_WEATHER_FORECAST"
          value = "3600"
        },
        {
          name  = "CACHE_TTL_WEATHER_HISTORIC"
          value = "259200"
        },
        {
          name  = "CACHE_TTL_EVENTS"
          value = "900"
        },
        {
          name  = "CACHE_TTL_CUSTODY"
          value = "7200"
        },
        {
          name  = "CACHE_TTL_USER_PROFILE"
          value = "1800"
        },
        {
          name  = "CACHE_TTL_FAMILY_DATA"
          value = "1800"
        },
        # SMTP Configuration (non-sensitive values)
        {
          name  = "SMTP_HOST"
          value = var.smtp_host
        },
        {
          name  = "SMTP_PORT"
          value = tostring(var.smtp_port)
        },
        # Apple Sign-In (non-sensitive values)
        {
          name  = "APPLE_CLIENT_ID"
          value = var.apple_client_id
        },
        {
          name  = "APPLE_TEAM_ID"
          value = var.apple_team_id
        },
        {
          name  = "APPLE_KEY_ID"
          value = var.apple_key_id
        },
        {
          name  = "APPLE_REDIRECT_URI"
          value = var.apple_redirect_uri
        },
        # Google Sign-In (non-sensitive values)
        {
          name  = "GOOGLE_CLIENT_ID"
          value = var.google_client_id
        },
        {
          name  = "GOOGLE_REDIRECT_URI"
          value = var.google_redirect_uri
        },
        # AWS S3 Configuration
        {
          name  = "AWS_S3_BUCKET_NAME"
          value = var.aws_s3_bucket_name
        }
      ]

      secrets = [
        {
          name      = "SECRET_KEY"
          valueFrom = aws_ssm_parameter.secret_key.arn
        },
        {
          name      = "DB_USER"
          valueFrom = aws_ssm_parameter.db_user.arn
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = aws_ssm_parameter.db_password.arn
        },
        {
          name      = "AWS_ACCESS_KEY_ID"
          valueFrom = aws_ssm_parameter.aws_access_key.arn
        },
        {
          name      = "AWS_SECRET_ACCESS_KEY"
          valueFrom = aws_ssm_parameter.aws_secret_key.arn
        },
        {
          name      = "REDIS_PASSWORD"
          valueFrom = var.environment == "production" ? aws_ssm_parameter.redis_auth[0].arn : aws_ssm_parameter.redis_auth_staging[0].arn
        },
        {
          name      = "GOOGLE_PLACES_API_KEY"
          valueFrom = aws_ssm_parameter.google_places_api_key.arn
        },
        {
          name      = "SNS_PLATFORM_APPLICATION_ARN"
          valueFrom = aws_ssm_parameter.sns_platform_application_arn.arn
        },
        {
          name      = "SMTP_USER"
          valueFrom = aws_ssm_parameter.smtp_user.arn
        },
        {
          name      = "SMTP_PASSWORD"
          valueFrom = aws_ssm_parameter.smtp_password.arn
        },
        {
          name      = "APPLE_PRIVATE_KEY"
          valueFrom = aws_ssm_parameter.apple_private_key.arn
        },
        {
          name      = "GOOGLE_CLIENT_SECRET"
          valueFrom = aws_ssm_parameter.google_client_secret.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command = [
          "CMD-SHELL",
          "curl -f http://localhost:${var.container_port}${var.health_check_path} || exit 1"
        ]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-${var.environment}-task-def"
  }
}

# ECS Service
resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-${var.environment}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "${var.project_name}-app"
    container_port   = var.container_port
  }

  # Note: deployment_configuration will be added after initial deployment works

  depends_on = [
    aws_lb_listener.app,
    aws_iam_role_policy_attachment.ecs_execution_role_policy,
    aws_iam_role_policy_attachment.ecs_task_role_policy
  ]

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-service"
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "ecs_policy_cpu" {
  name               = "${var.project_name}-${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = var.target_cpu_utilization
  }
}

# Auto Scaling Policy - Memory
resource "aws_appautoscaling_policy" "ecs_policy_memory" {
  name               = "${var.project_name}-${var.environment}-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = var.target_memory_utilization
  }
} 