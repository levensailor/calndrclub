#!/bin/bash
set -e

echo "=== Fixing Database Subnet Routing Issues ==="
echo "This script will add missing route tables and associations for database subnets"

# Check if we're in the terraform directory
if [ ! -f "main.tf" ]; then
    echo "Changing to terraform directory..."
    cd terraform
fi

# Check current directory
echo "Current directory: $(pwd)"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

# Plan the changes for the specified environment
ENVIRONMENT=${1:-staging}
echo "Planning infrastructure changes for environment: $ENVIRONMENT"

terraform plan -var-file="${ENVIRONMENT}.tfvars" -target=aws_route_table.database -target=aws_route_table_association.database

echo ""
echo "=== Review the plan above ==="
echo "This will create:"
echo "- Database route tables for each database subnet"
echo "- Route table associations to connect database subnets to their route tables"
echo "- For staging: Database subnets will have internet access through NAT gateways"
echo "- For production: Database subnets will be isolated (no internet access)"
echo ""
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Applying database routing fixes..."
    terraform apply -var-file="${ENVIRONMENT}.tfvars" -target=aws_route_table.database -target=aws_route_table_association.database
    
    echo ""
    echo "=== Database Routing Fix Complete ==="
    echo "Database subnets now have proper route tables configured."
    echo ""
    echo "Next steps:"
    echo "1. Restart your ECS service to test database connectivity"
    echo "2. Check application logs for successful database connection"
    echo "3. If issues persist, verify security group rules allow traffic"
    echo ""
else
    echo "Operation cancelled."
    exit 1
fi 