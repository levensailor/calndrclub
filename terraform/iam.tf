# ECS Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project_name}-${var.environment}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-execution-role"
  }
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-task-role"
  }
}

# ECS Execution Role Policy Attachment
resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for ECS execution role to access SSM parameters
resource "aws_iam_policy" "ecs_ssm_policy" {
  name        = "${var.project_name}-${var.environment}-ecs-ssm-policy"
  description = "Policy for ECS to access SSM parameters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter",
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/${var.environment}/*",
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.project_name}/${var.environment}/*"
        ]
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-ssm-policy"
  }
}

# Attach SSM policy to ECS execution role
resource "aws_iam_role_policy_attachment" "ecs_execution_ssm_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = aws_iam_policy.ecs_ssm_policy.arn
}

# Custom policy for ECS task role (application permissions)
resource "aws_iam_policy" "ecs_task_policy" {
  name        = "${var.project_name}-${var.environment}-ecs-task-policy"
  description = "Policy for ECS tasks to access AWS services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.backup_bucket_name}",
          "arn:aws:s3:::${var.backup_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sns:CreatePlatformEndpoint",
          "sns:DeleteEndpoint",
          "sns:GetEndpointAttributes",
          "sns:SetEndpointAttributes"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/ecs/${var.project_name}-${var.environment}:*"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-task-policy"
  }
}

# Attach task policy to ECS task role
resource "aws_iam_role_policy_attachment" "ecs_task_role_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}

# RDS Enhanced Monitoring Role
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-${var.environment}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-monitoring-role"
  }
}

# Attach RDS Enhanced Monitoring policy
resource "aws_iam_role_policy_attachment" "rds_monitoring_policy" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# GitHub Actions Role (for CI/CD)
resource "aws_iam_role" "github_actions" {
  name = "${var.project_name}-${var.environment}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:*/*:*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-github-actions-role"
  }
}

# GitHub Actions Policy
resource "aws_iam_policy" "github_actions_policy" {
  name        = "${var.project_name}-${var.environment}-github-actions-policy"
  description = "Policy for GitHub Actions to deploy to ECS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_execution_role.arn,
          aws_iam_role.ecs_task_role.arn
        ]
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-github-actions-policy"
  }
}

# Attach GitHub Actions policy
resource "aws_iam_role_policy_attachment" "github_actions_policy" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_policy.arn
}

# Store application secrets in SSM Parameter Store
resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.project_name}/${var.environment}/app/secret_key"
  type  = "SecureString"
  value = var.secret_key

  tags = {
    Name = "${var.project_name}-${var.environment}-secret-key"
  }
}

resource "aws_ssm_parameter" "aws_access_key" {
  name  = "/${var.project_name}/${var.environment}/aws/access_key_id"
  type  = "SecureString"
  value = var.aws_access_key_id

  tags = {
    Name = "${var.project_name}-${var.environment}-aws-access-key"
  }
}

resource "aws_ssm_parameter" "aws_secret_key" {
  name  = "/${var.project_name}/${var.environment}/aws/secret_access_key"
  type  = "SecureString"
  value = var.aws_secret_access_key

  tags = {
    Name = "${var.project_name}-${var.environment}-aws-secret-key"
  }
}

# Google Places API Key
resource "aws_ssm_parameter" "google_places_api_key" {
  name  = "/${var.project_name}/${var.environment}/api/google_places_api_key"
  type  = "SecureString"
  value = var.google_places_api_key

  tags = {
    Name = "${var.project_name}-${var.environment}-google-places-api-key"
  }
}

# SNS Platform Application ARN
resource "aws_ssm_parameter" "sns_platform_application_arn" {
  name  = "/${var.project_name}/${var.environment}/aws/sns_platform_application_arn"
  type  = "SecureString"
  value = var.sns_platform_application_arn

  tags = {
    Name = "${var.project_name}-${var.environment}-sns-platform-arn"
  }
}

# SMTP Configuration
resource "aws_ssm_parameter" "smtp_user" {
  name  = "/${var.project_name}/${var.environment}/smtp/user"
  type  = "SecureString"
  value = var.smtp_user

  tags = {
    Name = "${var.project_name}-${var.environment}-smtp-user"
  }
}

resource "aws_ssm_parameter" "smtp_password" {
  name  = "/${var.project_name}/${var.environment}/smtp/password"
  type  = "SecureString"
  value = var.smtp_password

  tags = {
    Name = "${var.project_name}-${var.environment}-smtp-password"
  }
}

# Apple Sign-In Configuration
resource "aws_ssm_parameter" "apple_private_key" {
  name  = "/${var.project_name}/${var.environment}/apple/private_key"
  type  = "SecureString"
  value = var.apple_private_key

  tags = {
    Name = "${var.project_name}-${var.environment}-apple-private-key"
  }
}

# Google Sign-In Configuration
resource "aws_ssm_parameter" "google_client_secret" {
  name  = "/${var.project_name}/${var.environment}/google/client_secret"
  type  = "SecureString"
  value = var.google_client_secret

  tags = {
    Name = "${var.project_name}-${var.environment}-google-client-secret"
  }
} 