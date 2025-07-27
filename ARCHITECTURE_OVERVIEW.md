# Calndr Backend Architecture Overview

## Architecture Summary

The Calndr backend uses a modern AWS containerized architecture deployed across separate staging and production environments. The system follows best practices for scalability, security, and monitoring.

## High-Level Architecture

### Core Components
- **Application**: FastAPI backend running on ECS Fargate
- **Database**: PostgreSQL on RDS with read replica (production)
- **Cache**: Redis on ElastiCache for performance optimization
- **Load Balancer**: Application Load Balancer with SSL termination
- **Container Registry**: ECR for Docker image storage
- **Monitoring**: CloudWatch for logs, metrics, and alerting

### Network Architecture
- **Multi-AZ Deployment**: Resources distributed across 2 availability zones
- **3-Tier Network**: Public, Private, and Database subnets
- **NAT Gateways**: Provide outbound internet access for private resources
- **Security Groups**: Fine-grained network access control

## Environment Details

### Production Environment
- **VPC CIDR**: 10.0.0.0/16
- **Domain**: api.calndr.club
- **High Availability**: Multi-AZ RDS, Read Replica, Auto Scaling
- **Monitoring**: Enhanced monitoring, email alerts, 7-day log retention
- **Security**: Encryption at rest, Redis authentication, deletion protection

### Staging Environment  
- **VPC CIDR**: 10.1.0.0/16
- **Domain**: staging-api.calndr.club
- **Cost Optimized**: Single AZ RDS, reduced monitoring, shorter log retention
- **Testing**: Safe environment for feature testing and validation

## AWS Services by Category

### Compute & Containers
- **ECS Fargate**: Serverless container platform
- **ECR**: Container image registry with lifecycle policies
- **Application Auto Scaling**: Dynamic scaling based on CPU/memory

### Networking & Content Delivery
- **VPC**: Isolated network environment
- **Application Load Balancer**: HTTPS termination and traffic distribution
- **Route 53**: DNS management and health checks
- **NAT Gateways**: Outbound internet access for private subnets

### Database & Storage
- **RDS PostgreSQL**: Primary database with automated backups
- **ElastiCache Redis**: In-memory caching for performance
- **S3**: Object storage for application assets
- **SSM Parameter Store**: Secure configuration and secrets management

### Security & Identity
- **ACM**: SSL certificate management
- **IAM**: Role-based access control
- **Security Groups**: Network-level firewall rules

### Monitoring & Operations
- **CloudWatch**: Logs, metrics, dashboards, and alarms
- **SNS**: Email alerting for critical issues
- **Performance Insights**: Database performance monitoring

## Network Security Model

### Security Groups
- **ALB Security Group**: Allows HTTP/HTTPS from internet
- **ECS Tasks Security Group**: Allows traffic from ALB only
- **RDS Security Group**: Allows PostgreSQL from ECS and bastion
- **Redis Security Group**: Allows Redis from ECS and bastion
- **Bastion Security Group**: SSH access for maintenance

### Subnet Architecture
```
Public Subnets (Internet Gateway)
├── Application Load Balancer
└── NAT Gateways

Private Subnets (NAT Gateway)
├── ECS Fargate Tasks
└── ElastiCache Redis

Database Subnets (No Internet)
└── RDS PostgreSQL
```

## External Integrations

### Authentication Providers
- **Apple Sign-In**: iOS app authentication
- **Google OAuth**: Social authentication
- **Facebook OAuth**: Social authentication

### External APIs
- **Google Places API**: Location services
- **Apple Push Notifications**: iOS notifications
- **AWS SES SMTP**: Email delivery

## Data Flow

### Request Flow
1. **User Request** → Route 53 DNS resolution
2. **DNS** → Application Load Balancer (SSL termination)
3. **ALB** → Target Group health check
4. **Target Group** → ECS Fargate tasks (FastAPI app)
5. **ECS Task** → RDS PostgreSQL database
6. **ECS Task** → ElastiCache Redis cache
7. **Response** ← Back through ALB to user

### Deployment Flow
1. **Code Push** → GitHub repository
2. **GitHub Actions** → Build Docker image
3. **Docker Image** → Push to ECR
4. **ECS Service** → Pull new image and deploy
5. **Auto Scaling** → Scale tasks based on metrics

## Monitoring & Alerting

### CloudWatch Metrics
- **ECS**: CPU utilization, memory utilization, task count
- **RDS**: CPU, connections, memory, read/write latency
- **Redis**: CPU, memory usage, cache hits/misses
- **ALB**: Request count, response time, error rates

### Critical Alarms
- **High CPU/Memory**: Auto scaling triggers
- **Database Issues**: Connection limits, slow queries
- **Application Errors**: 5xx error rates
- **Infrastructure**: Health check failures

### Logging Strategy
- **Application Logs**: Structured JSON logs in CloudWatch
- **Request Logs**: Separate log stream excluding health checks
- **Database Logs**: Query logging and performance insights
- **Infrastructure Logs**: ECS execution and system logs

## High Availability & Disaster Recovery

### Production HA Features
- **Multi-AZ RDS**: Automatic failover to standby
- **Read Replica**: Read traffic distribution
- **ECS Auto Scaling**: Automatic task replacement
- **Multiple AZs**: Load balancer spans 2 availability zones

### Backup Strategy
- **RDS Automated Backups**: 7-day retention with point-in-time recovery
- **Redis Snapshots**: Daily snapshots for data protection
- **Container Images**: Lifecycle policies retain recent versions
- **Configuration**: SSM Parameter Store versioning

## Cost Optimization

### Staging Optimizations
- **Single AZ**: Reduced NAT Gateway and RDS costs
- **Smaller Instance Types**: Right-sized for testing workloads
- **Reduced Monitoring**: Basic monitoring without enhanced features
- **No Read Replica**: Cost savings for non-critical environment

### General Optimizations
- **Fargate Spot**: Mixed capacity for non-critical workloads
- **ECR Lifecycle**: Automatic cleanup of old images
- **CloudWatch Log Retention**: Configurable retention periods
- **Auto Scaling**: Scale down during low usage periods

## Security Best Practices

### Network Security
- **Private Subnets**: Application and database isolated from internet
- **Security Groups**: Principle of least privilege
- **NACLs**: Additional network layer protection
- **VPC Flow Logs**: Network traffic monitoring

### Application Security
- **Secrets Management**: SSM Parameter Store for sensitive data
- **Encryption**: At rest and in transit
- **IAM Roles**: Service-to-service authentication
- **Container Scanning**: ECR vulnerability scanning

### Compliance & Governance
- **Resource Tagging**: Environment, project, and cost tracking
- **Access Logging**: CloudTrail for API calls
- **Deletion Protection**: Critical resources protected
- **Backup Verification**: Regular restore testing

## Infrastructure as Code

### Terraform Management
- **State Backend**: S3 with DynamoDB locking
- **Environment Separation**: Separate state files
- **Variable Management**: Environment-specific tfvars
- **Module Structure**: Reusable infrastructure components

### Deployment Automation
- **GitHub Actions**: CI/CD pipeline
- **Terraform Plan**: Infrastructure change preview
- **Automated Testing**: Infrastructure validation
- **Rollback Capability**: Version-controlled infrastructure 