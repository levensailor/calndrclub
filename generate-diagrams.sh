#!/bin/bash

# Generate Architecture Diagrams from DOT file
# Requires Graphviz to be installed

DOT_FILE="calndr-architecture.dot"
OUTPUT_DIR="diagrams"

# Check if Graphviz is installed
if ! command -v dot &> /dev/null; then
    echo "❌ Graphviz is not installed. Please install it first:"
    echo "   macOS: brew install graphviz"
    echo "   Ubuntu: sudo apt-get install graphviz"
    echo "   Windows: Download from https://graphviz.org/download/"
    exit 1
fi

# Check if DOT file exists
if [ ! -f "$DOT_FILE" ]; then
    echo "❌ DOT file '$DOT_FILE' not found!"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "🎨 Generating architecture diagrams..."

# Generate PDF (high quality for documents)
echo "📄 Generating PDF..."
dot -Tpdf "$DOT_FILE" -o "$OUTPUT_DIR/calndr-architecture.pdf"

# Generate SVG (scalable for web)
echo "🖼️ Generating SVG..."
dot -Tsvg "$DOT_FILE" -o "$OUTPUT_DIR/calndr-architecture.svg"

# Generate PNG (standard resolution)
echo "🖼️ Generating PNG (standard)..."
dot -Tpng -Gdpi=150 "$DOT_FILE" -o "$OUTPUT_DIR/calndr-architecture.png"

# Generate high-resolution PNG (for presentations)
echo "🖼️ Generating PNG (high-res)..."
dot -Tpng -Gdpi=300 "$DOT_FILE" -o "$OUTPUT_DIR/calndr-architecture-hires.png"

# Generate PostScript (for print)
echo "🖨️ Generating PostScript..."
dot -Tps "$DOT_FILE" -o "$OUTPUT_DIR/calndr-architecture.ps"

echo ""
echo "✅ All diagrams generated successfully!"
echo "📁 Output directory: $OUTPUT_DIR/"
echo ""
echo "Generated files:"
ls -la "$OUTPUT_DIR/"

echo ""
echo "📋 Quick usage:"
echo "   PDF: Best for documents and printing"
echo "   SVG: Best for web and scalable graphics"
echo "   PNG: Best for presentations and embedding"
echo "   PNG (high-res): Best for large displays and detailed views" 