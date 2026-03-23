# Makefile for building OpenCue documentation with Docker
# Provides simple commands for Docker-based documentation builds

.PHONY: help build serve clean rebuild shell

# Docker image name
IMAGE_NAME = opencue-docs
CONTAINER_NAME = opencue-docs-build

help:
	@echo "OpenCue Documentation Docker Build"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build    - Build documentation once"
	@echo "  serve    - Start development server with live reload"
	@echo "  clean    - Clean build artifacts and Docker resources"
	@echo "  rebuild  - Clean and rebuild everything"
	@echo "  shell    - Open a shell in the documentation container"
	@echo ""
	@echo "Examples:"
	@echo "  make build   # Build documentation"
	@echo "  make serve   # Start dev server at http://localhost:4000"
	@echo "  make clean   # Clean up"

# Build the Docker image
docker-image:
	@echo "Building Docker image..."
	docker build -t $(IMAGE_NAME) .

# Build documentation
build: docker-image
	@echo "Building OpenCue documentation..."
	docker run --rm \
		-v "$(PWD):/docs" \
		$(IMAGE_NAME) \
		bundle exec jekyll build --verbose
	@if [ -d "_site" ]; then \
		echo "✓ Documentation built successfully!"; \
		echo "  Output directory: $(PWD)/_site"; \
	else \
		echo "✗ Build failed - _site directory not found"; \
		exit 1; \
	fi

# Serve documentation with live reload
serve: docker-image
	@echo "Starting documentation server..."
	@echo "Server will be available at: http://localhost:4000"
	@echo "Press Ctrl+C to stop"
	docker run --rm -it \
		-v "$(PWD):/docs" \
		-p 4000:4000 \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME) \
		bundle exec jekyll serve --host 0.0.0.0 --livereload --force_polling

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf _site .jekyll-cache
	@docker rmi $(IMAGE_NAME) 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Rebuild from scratch
rebuild: clean build

# Open shell in container
shell: docker-image
	@echo "Opening shell in documentation container..."
	docker run --rm -it \
		-v "$(PWD):/docs" \
		$(IMAGE_NAME) \
		sh
