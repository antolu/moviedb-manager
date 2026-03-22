#!/bin/bash

# Development environment management script for moviedb-manager

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[DEV]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
}

# Start development environment
start_dev() {
    print_status "Starting development environment..."
    print_status "This will mount source code for live reload"

    # Build development images if they don't exist
    DOCKER_BUILDKIT=1 docker compose -f docker-compose.dev.yml build

    # Start containers
    docker compose -f docker-compose.dev.yml up -d

    print_status "Development environment started!"
    print_status "URL: http://localhost:6001"
    print_status "Backend Direct: http://localhost:6003"
    print_status ""
    print_status "To view logs: ./dev.sh logs"
}

# Stop development environment
stop_dev() {
    print_status "Stopping development environment..."
    docker compose -f docker-compose.dev.yml down
}

# Restart development environment
restart_dev() {
    stop_dev
    start_dev
}

# Rebuild dev images
rebuild_dev() {
    print_status "Rebuilding development images..."
    docker compose -f docker-compose.dev.yml build --no-cache
}

# Show logs
show_logs() {
    docker compose -f docker-compose.dev.yml logs -f "$@"
}

# Run tests
run_tests() {
    print_status "Running tests in isolated environment (building images first)..."
    docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --force-recreate
}

# Start production environment
start_prod() {
    print_status "Starting production environment..."
    docker compose up -d
}

# Stop production environment
stop_prod() {
    print_status "Stopping production environment..."
    docker compose down
}

# Help
show_help() {
    cat <<EOF
Usage: $0 [COMMAND]

Commands:
  dev, start    Start development environment with hot reloading
  stop          Stop development environment
  restart       Restart development environment
  rebuild       Rebuild development images
  logs          Follow logs
  test          Run tests in an isolated environment
  prod          Start production environment
  prod-stop     Stop production environment
  help          Show this help message
EOF
}

# Main
check_dependencies

case "${1:-help}" in
    dev|start)
        start_dev
        ;;
    stop)
        stop_dev
        ;;
    restart)
        restart_dev
        ;;
    rebuild)
        rebuild_dev
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    test)
        run_tests
        ;;
    prod)
        start_prod
        ;;
    prod-stop)
        stop_prod
        ;;
    help|*)
        show_help
        ;;
esac
