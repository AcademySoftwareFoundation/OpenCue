#!/bin/bash
#
# OpenCue Full Stack Deployment Script
#
# This script builds and deploys the complete OpenCue stack including:
#   - db: PostgreSQL database for storing OpenCue data
#   - flyway: Database migration tool for schema management
#   - cuebot: The OpenCue server that manages jobs, frames, and hosts
#   - rqd: The render queue daemon that runs on render hosts
#   - rest-gateway: HTTP/REST API gateway for web access
#   - cueweb: Web UI for monitoring and managing OpenCue
#
# Usage:
#   ./sandbox/deploy_opencue_full.sh [command]
#
# Commands:
#   up      - Start all services (default)
#   down    - Stop all services
#   build   - Build images only
#   logs    - View logs
#   status  - Check service status
#   restart - Restart services
#   clean   - Stop and remove all containers, volumes, and images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to the OpenCue root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCUE_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$OPENCUE_ROOT"

# Docker compose file path
COMPOSE_FILE="sandbox/docker-compose.full.yml"

# Generate JWT secret if not set
if [ -z "$JWT_SECRET" ]; then
    export JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || echo "opencue-dev-jwt-secret-$(date +%s)")
    echo -e "${YELLOW}Generated JWT_SECRET (save this for client use):${NC}"
    echo -e "${BLUE}export JWT_SECRET='$JWT_SECRET'${NC}"
    echo ""
fi

# Create required directories
mkdir -p /tmp/rqd/logs /tmp/rqd/shots

print_header() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

build_images() {
    print_header "Building Docker Images"

    print_status "Building Cuebot image..."
    docker build -t opencue/cuebot -f cuebot/Dockerfile . || {
        print_error "Failed to build Cuebot image"
        exit 1
    }

    print_status "Building REST Gateway image..."
    docker build -t opencue/rest-gateway:latest -f rest_gateway/Dockerfile . || {
        print_error "Failed to build REST Gateway image"
        exit 1
    }

    print_status "Building CueWeb image..."
    docker build -t opencue/cueweb:latest ./cueweb || {
        print_error "Failed to build CueWeb image"
        exit 1
    }

    print_success "All images built successfully"
}

cleanup_orphaned_containers() {
    # Remove any orphaned containers that might conflict with docker compose
    local containers=("opencue-db" "opencue-flyway" "opencue-cuebot" "opencue-rqd" "opencue-rest-gateway" "opencue-cueweb")
    for container in "${containers[@]}"; do
        if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
            print_status "Removing orphaned container: $container"
            docker rm -f "$container" &>/dev/null || true
        fi
    done
}

start_services() {
    print_header "Starting OpenCue Full Stack"
    print_status "Deploying: db, flyway, cuebot, rqd, rest-gateway, cueweb"

    # Check if images exist, build if not
    if ! docker image inspect opencue/rest-gateway:latest &>/dev/null || \
       ! docker image inspect opencue/cueweb:latest &>/dev/null; then
        print_warning "Images not found, building..."
        build_images
    fi

    # Clean up any orphaned containers from previous runs
    cleanup_orphaned_containers

    print_status "Starting services..."
    docker compose -f "$COMPOSE_FILE" up -d

    print_status "Waiting for services to be healthy..."
    sleep 10

    # Check service status
    check_status

    print_header "Deployment Complete!"
    echo ""
    echo -e "${GREEN}All services are running:${NC}"
    echo -e "  ${BLUE}PostgreSQL:${NC}      localhost:5432"
    echo -e "  ${BLUE}Cuebot gRPC:${NC}     localhost:8443"
    echo -e "  ${BLUE}RQD:${NC}             localhost:8444"
    echo -e "  ${BLUE}REST Gateway:${NC}    http://localhost:8448"
    echo -e "  ${BLUE}CueWeb UI:${NC}       http://localhost:3000"
    echo ""
    echo -e "${YELLOW}To generate a JWT token for API access:${NC}"
    echo -e "${BLUE}export JWT_SECRET='$JWT_SECRET'${NC}"
    echo ""
    echo "python3 -c \""
    echo "import jwt, datetime"
    echo "payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}"
    echo "print(jwt.encode(payload, '$JWT_SECRET', algorithm='HS256'))"
    echo "\""
}

stop_services() {
    print_header "Stopping OpenCue Services"
    docker compose -f "$COMPOSE_FILE" down
    # Also clean up any orphaned containers
    cleanup_orphaned_containers
    print_success "All services stopped"
}

check_status() {
    print_header "Service Status"
    docker compose -f "$COMPOSE_FILE" ps

    echo ""
    print_status "Checking service health..."

    # Check PostgreSQL
    if docker exec opencue-db pg_isready -U cuebot -d cuebot &>/dev/null; then
        print_success "PostgreSQL is healthy"
    else
        print_warning "PostgreSQL not responding yet"
    fi

    # Check REST Gateway
    if curl -sf http://localhost:8448/ &>/dev/null || [ $? -eq 22 ]; then
        print_success "REST Gateway is responding (401 expected without auth)"
    else
        print_warning "REST Gateway not responding yet"
    fi

    # Check CueWeb
    if curl -sf http://localhost:3000 &>/dev/null; then
        print_success "CueWeb is responding"
    else
        print_warning "CueWeb not responding yet"
    fi
}

view_logs() {
    print_header "Service Logs"
    docker compose -f "$COMPOSE_FILE" logs -f "$@"
}

restart_services() {
    print_header "Restarting OpenCue Services"
    docker compose -f "$COMPOSE_FILE" restart
    print_success "All services restarted"
}

clean_all() {
    print_header "Cleaning Up OpenCue Deployment"
    print_warning "This will remove all containers, volumes, and images!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f "$COMPOSE_FILE" down --volumes --rmi all
        # Also clean up any orphaned containers
        cleanup_orphaned_containers
        print_success "Cleanup complete"
    else
        print_status "Cleanup cancelled"
    fi
}

show_help() {
    echo "OpenCue Full Stack Deployment Script"
    echo ""
    echo "Deploys the complete OpenCue stack:"
    echo "  - db: PostgreSQL database"
    echo "  - flyway: Database migrations"
    echo "  - cuebot: OpenCue server"
    echo "  - rqd: Render queue daemon"
    echo "  - rest-gateway: REST API"
    echo "  - cueweb: Web UI"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  up       Start all services (default)"
    echo "  down     Stop all services"
    echo "  build    Build images only"
    echo "  logs     View logs (add service name for specific logs)"
    echo "  status   Check service status"
    echo "  restart  Restart services"
    echo "  clean    Stop and remove all containers, volumes, and images"
    echo "  help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Start all services"
    echo "  $0 up           # Start all services"
    echo "  $0 down         # Stop all services"
    echo "  $0 logs cueweb  # View CueWeb logs"
    echo "  $0 logs cuebot  # View Cuebot logs"
    echo "  $0 logs rqd     # View RQD logs"
    echo "  $0 build        # Build images only"
}

# Main command handling
case "${1:-up}" in
    up|start)
        start_services
        ;;
    down|stop)
        stop_services
        ;;
    build)
        build_images
        ;;
    logs)
        shift
        view_logs "$@"
        ;;
    status|ps)
        check_status
        ;;
    restart)
        restart_services
        ;;
    clean)
        clean_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
