#!/bin/bash

# Build and validate the Jekyll documentation site

set -e

echo "Testing OpenCue documentation build..."

# Navigate to docs directory
cd "$(dirname "$0")"

# Color output functions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE} $1${NC}"
}

print_success() {
    echo -e "${GREEN} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW} $1${NC}"
}

print_error() {
    echo -e "${RED} $1${NC}"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v bundle &> /dev/null; then
    print_error "Bundler is not installed. Please install Ruby and Bundler first."
    exit 1
fi

if [ ! -f "Gemfile" ]; then
    print_error "Gemfile not found. Make sure you're in the docs directory."
    exit 1
fi

print_success "Prerequisites check passed"

# Install dependencies
print_status "Installing dependencies..."
if bundle install --quiet; then
    print_success "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Clean previous build
if [ -d "_site" ]; then
    print_status "Cleaning previous build..."
    rm -rf _site
fi

# Build the site
print_status "Building documentation..."
if bundle exec jekyll build --verbose; then
    print_success "Jekyll build completed"
else
    print_error "Jekyll build failed"
    exit 1
fi

# Validate build output
print_status "Validating build output..."

if [ ! -d "_site" ]; then
    print_error "Build directory '_site' not found"
    exit 1
fi

# Count generated files
html_files=$(find _site -type f -name "*.html" | wc -l | tr -d ' ')
css_files=$(find _site -type f -name "*.css" | wc -l | tr -d ' ')
js_files=$(find _site -type f -name "*.js" | wc -l | tr -d ' ')
image_files=$(find _site -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.svg" -o -name "*.ico" \) | wc -l | tr -d ' ')
total_files=$(find _site -type f | wc -l | tr -d ' ')

print_success "Generated $html_files HTML files"
print_success "Generated $css_files CSS files"
print_success "Generated $js_files JavaScript files"
print_success "Generated $image_files image files"
print_success "Total files generated: $total_files"

# Check for critical files
critical_files=(
    "_site/index.html"
    "_site/assets/css/just-the-docs-default.css"
    "_site/assets/js/just-the-docs.js"
    "_site/assets/images/opencue_logo_with_text.png"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "Critical file exists: $(basename "$file")"
    else
        print_error "Missing critical file: $file"
        exit 1
    fi
done

# Check for theme toggle functionality
if grep -q "theme-toggle" _site/index.html; then
    print_success "Theme toggle functionality found"
else
    print_warning "Theme toggle functionality not found in index.html"
fi

# Check for proper image paths - now checking for relative_url filter usage
if grep -q "assets/images/" _site/**/*.html 2>/dev/null; then
    print_success "Image paths found in build output"
else
    print_warning "No image paths found in build output"
fi

# Build size information
build_size=$(du -sh _site | cut -f1)
print_success "Build size: $build_size"

# Success summary
echo ""
print_success "Documentation build completed successfully!"
echo -e "Build output: ${BLUE}$(pwd)/_site${NC}"

# Testing options
echo ""
print_status "Testing options:"
echo "- Serve locally:     bundle exec jekyll serve"
# Determine the local URL based on baseurl setting
if grep -q 'baseurl: ""' _config.yml; then
    echo "- Local URL:         http://localhost:4000/"
else
    baseurl=$(grep 'baseurl:' _config.yml | sed 's/.*baseurl: "\(.*\)"/\1/')
    echo "- Local URL:         http://localhost:4000${baseurl}/"
fi
echo "- Validate HTML:     bundle exec htmlproofer _site --disable-external"
echo "- Test dark mode:    Open site and click sun/moon icon in top-right"

# Check if port 4000 is available
if lsof -Pi :4000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Port 4000 is already in use. Jekyll serve may fail."
    print_status "To free port 4000: pkill -f 'jekyll serve'"
fi

print_success "Build test completed successfully!"
