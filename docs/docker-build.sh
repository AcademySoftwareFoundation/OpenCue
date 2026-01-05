#!/bin/bash

# Helper script for building OpenCue documentation with Docker
# This script provides convenient commands for common Docker-based documentation tasks

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check for Docker Compose (v2 or v1)
    if command -v docker compose &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        print_warning "Docker Compose not found. Using direct Docker commands instead."
        DOCKER_COMPOSE=""
    fi
}

# Show usage
show_usage() {
    cat << EOF
OpenCue Documentation Docker Build Script

Usage: $0 [command]

Commands:
  build       Build documentation once
  serve       Start development server with live reload
  clean       Clean build artifacts and Docker resources
  rebuild     Clean and rebuild everything
  shell       Open a shell in the documentation container
  logs        Show container logs
  stop        Stop running containers
  help        Show this help message

Examples:
  $0 build          # Build documentation
  $0 serve          # Start dev server at http://localhost:4000
  $0 clean          # Clean up build artifacts
  $0 rebuild        # Full rebuild from scratch

For more information, see DOCKER.md
EOF
}

# Build documentation
build_docs() {
    print_status "Building OpenCue documentation..."
    
    if [ -n "$DOCKER_COMPOSE" ]; then
        $DOCKER_COMPOSE --profile build up --abort-on-container-exit
    else
        # Fallback to direct Docker commands
        IMAGE_NAME="opencue-docs"
        print_status "Building Docker image..."
        docker build -t $IMAGE_NAME .
        print_status "Running build..."
        docker run --rm -v "$(pwd):/docs" $IMAGE_NAME bundle exec jekyll build --verbose
    fi
    
    if [ -d "_site" ]; then
        size=$(du -sh _site | cut -f1)
        print_success "Documentation built successfully! (Size: $size)"
        print_status "Output directory: $(pwd)/_site"
    else
        print_error "Build failed - _site directory not found"
        exit 1
    fi
}

# Serve documentation
serve_docs() {
    print_status "Starting documentation server..."
    print_status "Server will be available at: http://localhost:4000"
    print_status "Press Ctrl+C to stop"
    echo ""
    
    if [ -n "$DOCKER_COMPOSE" ]; then
        $DOCKER_COMPOSE --profile serve up
    else
        # Fallback to direct Docker commands
        IMAGE_NAME="opencue-docs"
        print_status "Building Docker image..."
        docker build -t $IMAGE_NAME .
        print_status "Starting server..."
        docker run --rm -it -v "$(pwd):/docs" -p 4000:4000 \
            $IMAGE_NAME bundle exec jekyll serve --host 0.0.0.0 --livereload --force_polling
    fi
}

# Clean artifacts
clean_docs() {
    print_status "Cleaning build artifacts..."
    
    # Stop containers
    if [ -n "$DOCKER_COMPOSE" ]; then
        $DOCKER_COMPOSE down 2>/dev/null || true
    else
        docker stop opencue-docs-build 2>/dev/null || true
        docker rm opencue-docs-build 2>/dev/null || true
    fi
    
    # Remove build artifacts
    if [ -d "_site" ]; then
        rm -rf _site
        print_success "Removed _site directory"
    fi
    
    if [ -d ".jekyll-cache" ]; then
        rm -rf .jekyll-cache
        print_success "Removed .jekyll-cache directory"
    fi
    
    # Remove Docker image and volumes
    docker rmi opencue-docs 2>/dev/null || true
    if docker volume ls | grep -q "docs_docs-bundle"; then
        docker volume rm docs_docs-bundle 2>/dev/null || true
        print_success "Removed Docker volumes"
    fi
    
    print_success "Cleanup complete"
}

# Rebuild everything
rebuild_docs() {
    print_status "Rebuilding documentation from scratch..."
    clean_docs
    
    print_status "Rebuilding Docker image..."
    docker compose build --no-cache
    
    build_docs
}

# Open shell
open_shell() {
    print_status "Opening shell in documentation container..."
    
    if [ -n "$DOCKER_COMPOSE" ]; then
        $DOCKER_COMPOSE run --rm docs-build sh
    else
        IMAGE_NAME="opencue-docs"
        docker build -t $IMAGE_NAME . > /dev/null 2>&1
        docker run --rm -it -v "$(pwd):/docs" $IMAGE_NAME sh
    fi
}

# Show logs
show_logs() {
    print_status "Showing container logs..."
    docker compose logs -f
}

# Stop containers
stop_containers() {
    print_status "Stopping containers..."
    
    if [ -n "$DOCKER_COMPOSE" ]; then
        $DOCKER_COMPOSE down
    else
        docker stop opencue-docs-build 2>/dev/null || true
        docker rm opencue-docs-build 2>/dev/null || true
    fi
    
    print_success "Containers stopped"
}

# Main script
main() {
    cd "$(dirname "$0")"
    
    check_docker
    
    case "${1:-help}" in
        build)
            build_docs
            ;;
        serve)
            serve_docs
            ;;
        clean)
            clean_docs
            ;;
        rebuild)
            rebuild_docs
            ;;
        shell)
            open_shell
            ;;
        logs)
            show_logs
            ;;
        stop)
            stop_containers
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
