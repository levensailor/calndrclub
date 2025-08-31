# Calndr Backend - Containerized Infrastructure

A scalable, containerized FastAPI backend for the Calndr family calendar application, deployed on AWS with full CI/CD automation.

> **Important**: This repository contains ONLY the backend code for the Calndr application. The frontend code is maintained in the main [calndr](https://github.com/levensailor/calndr) repository. Changes to the backend should be made in the main repository and will be automatically synced to this repository.

## 🚀 Architecture Overview

- **Application**: FastAPI with Python 3.11
- **Database**: PostgreSQL 15 (AWS RDS with Multi-AZ for production)
- **Cache**: Redis 7 (AWS ElastiCache)
- **Container Orchestration**: AWS ECS Fargate
- **Load Balancer**: Application Load Balancer with SSL termination
- **CI/CD**: GitHub Actions with automated testing and deployment
- **Infrastructure**: Terraform for Infrastructure as Code
- **Monitoring**: CloudWatch with custom dashboards and alerts

## 📋 Prerequisites

- **AWS CLI** configured with appropriate permissions
- **Docker** for local development and testing
- **Terraform** >= 1.0 for infrastructure management
- **Git** for version control
- **GitHub** repository with Actions enabled

## 🔄 Repository Sync Process

This repository is automatically synchronized with the backend code from the main [calndr](https://github.com/levensailor/calndr) repository. The sync process works as follows:

1. Changes to backend code are made in the main `calndr` repository
2. After each commit to the main repository, a post-commit hook triggers the sync script
3. The sync script copies only the backend code to this repository
4. Changes are automatically committed and pushed to this repository

**Important**: Do not make direct changes to this repository. All changes should be made in the main `calndr` repository.

## 🏗️ Infrastructure Setup

### 1. Initial Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd calndr-backend-refactor

# Make deployment script executable
chmod +x deploy-containerized.sh

# Check prerequisites
./deploy-containerized.sh help
```

### 2. Configure Environment Variables

Create a `.env` file in the project root (not committed to git):

```env
# Database Configuration
DB_USER=calndr_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=calndr

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Application Configuration
SECRET_KEY=your_secret_key_here
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your_s3_bucket

# External API Keys (optional)
GOOGLE_PLACES_API_KEY=your_google_places_api_key
APPLE_CLIENT_ID=your_apple_client_id
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### 3. Initialize Infrastructure

```bash
# Initialize Terraform for staging environment
./deploy-containerized.sh init-infrastructure -e staging

# Initialize Terraform for production environment
./deploy-containerized.sh init-infrastructure -e production
```

### 4. Configure GitHub Secrets

Set up the following secrets in your GitHub repository:

- `AWS_ROLE_ARN`: ARN of the GitHub Actions IAM role (from Terraform output)
- `DOCKER_BUILDKIT`: `1` (for optimized Docker builds)

## 🐳 Local Development

### Docker Compose Setup

```bash
# Start all services locally
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Local Testing

```bash
# Build and test Docker image locally
./deploy-containerized.sh build-local

# Run tests (add your test files)
cd backend
python -m pytest tests/ -v
```

## 🚀 Deployment

### Automatic Deployment (Recommended)

Deployments are triggered automatically via GitHub Actions:

- **Staging**: Push to `develop` branch
- **Production**: Push to `main` branch

### Manual Deployment

```bash
# Deploy to staging
./deploy-containerized.sh deploy-staging

# Deploy to production
./deploy-containerized.sh deploy-production
```

## 📊 Monitoring and Operations

### View Application Status

```bash
# Check deployment status
./deploy-containerized.sh status -e production

# View application logs
./deploy-containerized.sh logs -e production
```

### CloudWatch Dashboard

Access your monitoring dashboard:
- Staging: `https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=calndr-staging-dashboard`
- Production: `https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=calndr-production-dashboard`

### Alerts and Monitoring

- **CPU/Memory Utilization**: Alerts when > 85%
- **Response Time**: Alerts when > 1 second
- **Error Rate**: Alerts when > 10 errors per 5 minutes
- **Database Connections**: Alerts when > 20 connections
- **Redis Memory**: Alerts when < 10MB free

## 🔧 Configuration

### Environment-Specific Settings

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| Container CPU | 256 | 512 | 1024 |
| Container Memory | 512MB | 1GB | 2GB |
| RDS Instance | db.t3.micro | db.t3.small | db.t3.medium |
| Multi-AZ RDS | No | No | Yes |
| Redis Nodes | 1 | 1 | 2 |
| ECS Desired Count | 1 | 2 | 3 |
| Auto Scaling Max | 3 | 5 | 10 |

### Scaling Configuration

Auto-scaling is configured based on:
- **CPU Utilization**: Target 70%
- **Memory Utilization**: Target 80%
- **Custom Metrics**: Application-specific metrics

## 🛡️ Security Features

- **Container Security**: Non-root user, minimal attack surface
- **Network Security**: Private subnets for applications and databases
- **Data Encryption**: Encryption at rest and in transit
- **Secret Management**: AWS SSM Parameter Store for sensitive data
- **Image Scanning**: Trivy vulnerability scanning in CI/CD
- **SSL/TLS**: HTTPS enforced with automatic certificate management

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

1. **Test and Build**
   - Python dependency installation
   - Unit and integration tests
   - Docker image build and push to ECR

2. **Security Scan**
   - Trivy vulnerability scanning
   - Results uploaded to GitHub Security tab

3. **Deploy**
   - Environment-specific deployment
   - Health checks and rollback on failure
   - Cleanup of old images

### Deployment Strategy

- **Blue/Green Deployment**: Zero-downtime deployments
- **Health Checks**: Application health verification
- **Rollback**: Automatic rollback on deployment failures
- **Circuit Breaker**: Deployment protection mechanisms

## 📁 Project Structure

```
calndr-backend-refactor/
├── backend/                    # FastAPI application
│   ├── api/                   # API endpoints
│   ├── core/                  # Core configuration
│   ├── db/                    # Database models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   └── main.py               # Application entry point
├── terraform/                 # Infrastructure as Code
│   ├── main.tf               # Main Terraform configuration
│   ├── variables.tf          # Variable definitions
│   ├── outputs.tf            # Output definitions
│   ├── ecs.tf                # ECS configuration
│   ├── rds.tf                # Database configuration
│   ├── redis.tf              # Cache configuration
│   ├── load_balancer.tf      # Load balancer configuration
│   ├── security_groups.tf    # Security groups
│   ├── iam.tf                # IAM roles and policies
│   ├── ecr.tf                # Container registry
│   └── monitoring.tf         # CloudWatch configuration
├── .github/workflows/         # CI/CD pipelines
├── nginx/                     # Nginx configuration
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local development setup
├── deploy-containerized.sh    # Deployment script
└── README.md                 # This file
```

## 🚨 Troubleshooting

### Common Issues

1. **Container Won't Start**
   ```bash
   # Check ECS service events
   aws ecs describe-services --cluster calndr-production-cluster --services calndr-production-service
   
   # Check CloudWatch logs
   ./deploy-containerized.sh logs -e production
   ```

2. **Database Connection Issues**
   ```bash
   # Verify security groups allow connections
   # Check SSM parameters for database credentials
   aws ssm get-parameter --name "/calndr/production/db/password" --with-decryption
   ```

3. **High Response Times**
   ```bash
   # Check CloudWatch metrics
   # Verify auto-scaling configuration
   # Review database performance insights
   ```

### Recovery Procedures

1. **Rollback Deployment**
   ```bash
   # Use AWS CLI to update service to previous task definition
   aws ecs update-service --cluster <cluster> --service <service> --task-definition <previous-task-def>
   ```

2. **Database Recovery**
   ```bash
   # Restore from automated backup (RDS)
   aws rds restore-db-instance-from-db-snapshot --db-instance-identifier <new-instance> --db-snapshot-identifier <snapshot-id>
   ```

## 📞 Support

- **Issues**: Create GitHub issues for bugs and feature requests
- **Documentation**: Check the `/docs` endpoint when the API is running
- **Monitoring**: Use CloudWatch dashboards for real-time monitoring
- **Logs**: Application logs are available in CloudWatch Logs

## 🔄 Migration from Single EC2

If you're migrating from the single EC2 deployment:

1. **Backup Current Data**
   ```bash
   # Backup database
   pg_dump -h current-db-host -U username dbname > backup.sql
   ```

2. **Deploy New Infrastructure**
   ```bash
   ./deploy-containerized.sh init-infrastructure -e production
   ```

3. **Restore Data**
   ```bash
   # Restore to new RDS instance
   psql -h new-rds-endpoint -U username dbname < backup.sql
   ```

4. **Update DNS**
   - Point your domain to the new Application Load Balancer
   - Verify SSL certificate is working

5. **Verify and Cleanup**
   - Test all application functionality
   - Monitor for 24-48 hours
   - Decommission old EC2 instance

## 📈 Performance Optimization

- **Database**: Connection pooling, read replicas for production
- **Cache**: Redis for session storage and API response caching
- **CDN**: Consider CloudFront for static assets
- **Monitoring**: Custom metrics for business logic
- **Scaling**: Predictive scaling based on usage patterns

---

**Author**: Calndr Development Team  
**Last Updated**: $(date +'%Y-%m-%d')  
**Version**: 2.0.0 (Containerized)

For more information, visit the [Calndr website](https://calndr.club) or check the API documentation at `/docs` when the application is running. 



