# Architecture Diagrams - Usage Guide

This directory contains the Calndr backend architecture in multiple formats for use with different diagramming tools.

## Available Formats

### 📊 Draw.io / Diagrams.net Format
**File**: `calndr-architecture-drawio.xml`
- **Compatible with**: Draw.io, Diagrams.net
- **How to use**: 
  1. Go to [app.diagrams.net](https://app.diagrams.net)
  2. Click "Open Existing Diagram" 
  3. Upload the XML file
  4. The complete diagram will load with proper colors and layout

### 📈 Lucidchart Format  
**File**: `calndr-architecture-lucidchart.csv`
- **Compatible with**: Lucidchart
- **How to use**:
  1. Log into Lucidchart
  2. Create new document → Import Data
  3. Upload the CSV file
  4. Lucidchart will auto-arrange the components
  5. Customize layout and styling as needed

### 🖼️ Graphviz Format (PDF/SVG/PNG Export)
**File**: `calndr-architecture.dot`
- **Compatible with**: Graphviz, any tool that supports DOT format
- **How to generate images**:
  ```bash
  # Install Graphviz first
  # macOS: brew install graphviz
  # Ubuntu: sudo apt-get install graphviz
  # Windows: Download from graphviz.org
  
  # Generate PDF
  dot -Tpdf calndr-architecture.dot -o calndr-architecture.pdf
  
  # Generate SVG  
  dot -Tsvg calndr-architecture.dot -o calndr-architecture.svg
  
  # Generate PNG
  dot -Tpng calndr-architecture.dot -o calndr-architecture.png
  
  # Generate high-resolution PNG
  dot -Tpng -Gdpi=300 calndr-architecture.dot -o calndr-architecture-hires.png
  ```

### 📝 Text Format (Manual Import)
**File**: `calndr-architecture-simple.txt`
- **Compatible with**: Any diagramming tool (manual creation)
- **How to use**: 
  - Reference this file to manually create diagrams in Visio, Graffle, or other tools
  - Contains complete component lists, connections, and specifications
  - Includes IP ranges, ports, and security group details

## Component Details

### 🏗️ Infrastructure Components
- **Production VPC**: 10.0.0.0/16
- **Staging VPC**: 10.1.0.0/16
- **ECS Fargate**: Containerized FastAPI backend
- **RDS PostgreSQL**: Primary database with read replica (prod only)
- **ElastiCache Redis**: Caching layer
- **Application Load Balancer**: HTTPS termination and routing

### 🔒 Security & Networking
- **3-tier architecture**: Public, Private, Database subnets
- **NAT Gateways**: Outbound internet access for private resources
- **Security Groups**: Fine-grained network access control
- **SSL/TLS**: ACM certificates for HTTPS

### 📊 Monitoring & Operations
- **CloudWatch**: Centralized logging and metrics
- **SNS**: Email alerting for critical issues
- **Auto Scaling**: Dynamic scaling based on CPU/memory
- **SSM Parameter Store**: Secure secrets management

## Editing and Customization

### Draw.io/Diagrams.net
- Open the XML file and edit directly in the web interface
- Export to PDF, PNG, SVG, or other formats
- Collaborate in real-time with team members

### Graphviz DOT
- Edit the `.dot` file with any text editor
- Supports extensive customization options
- Excellent for automated diagram generation

### Adding New Components
1. **CSV Format**: Add new rows with component details
2. **DOT Format**: Add new nodes and edges following the existing pattern
3. **Draw.io**: Use the built-in shape libraries and connectors
4. **Text Format**: Update the relevant sections with new components

## Integration with Documentation

### Terraform Integration
The diagrams reflect the actual infrastructure defined in the `terraform/` directory:
- Network topology matches VPC/subnet configuration
- Security groups align with actual AWS resources
- Environment separation mirrors tfvars files

### Code Documentation
Refer to these files for additional context:
- `ARCHITECTURE_OVERVIEW.md`: Detailed technical documentation
- `terraform/`: Infrastructure as Code definitions
- `backend/LOGGING_GUIDE.md`: Application logging architecture

## Export Options

### For Presentations
- **PDF**: High-quality vector format for documents
- **PNG**: Raster format for slides and web
- **SVG**: Scalable vector format for web use

### For Documentation
- **PNG/SVG**: Embed in markdown documentation
- **PDF**: Include in technical specifications
- **Draw.io**: Interactive diagrams for team collaboration

## Maintenance

When updating the architecture:
1. Update the Terraform configurations first
2. Modify the diagrams to reflect infrastructure changes
3. Update the text documentation accordingly
4. Regenerate any exported images

## Tools Installation

### Graphviz (for DOT files)
```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz

# Windows
# Download from: https://graphviz.org/download/
```

### Online Tools (No Installation Required)
- **Draw.io**: [app.diagrams.net](https://app.diagrams.net)
- **Lucidchart**: [lucidchart.com](https://lucidchart.com)
- **Graphviz Online**: [edotor.net](https://edotor.net)

## Troubleshooting

### Common Issues
1. **CSV Import**: Ensure proper encoding (UTF-8) and delimiter (comma)
2. **DOT Rendering**: Check for syntax errors with `dot -Tsvg -v file.dot`
3. **Draw.io Import**: Verify XML is well-formed and not corrupted
4. **Large Diagrams**: Use `-Gdpi=150` for smaller file sizes in Graphviz

### Getting Help
- Graphviz documentation: [graphviz.org/doc](https://graphviz.org/doc)
- Draw.io help: [desk.draw.io](https://desk.draw.io)
- Lucidchart support: [help.lucidchart.com](https://help.lucidchart.com) 